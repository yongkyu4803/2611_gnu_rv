"""
engine_api — 실제 AI API(Anthropic Claude)를 호출하는 분석 엔진

- 문장은 다시 나누지 않는다. 문장 ID와 원문을 묶음(chunk)으로 보내고, 문장별 JSON을 받는다.
- 초안 주석 CSV는 프롬프트에 넣지 않는다(독립 분석).
- 응답은 원본 그대로 raw/에 보관한다. 형식이 틀리면 재시도하고, 끝내 실패한 문장은 '실패'로 기록한다.
  실패를 로컬 결과나 빈 값으로 몰래 채우지 않는다.
- 묶음 응답이 형식·스키마·ID·위치 검사를 모두 통과한 뒤에만 완료 캐시(chunk_###.ok.json)를 만든다.
- 같은 run_id로 다시 실행하면(재개) 처음 실행의 입력·설정(manifest.json)과 같은지 먼저 확인하고,
  다르면 멈춘다. 같으면 완료 캐시를 다시 검증한 뒤 끝난 묶음만 건너뛴다.
- 재개할 run_id의 작업 기록(manifest.json)이 없으면 멈춘다(잘못 적은 ID로 새 유료 실행이 시작되지 않게).
- 응답이 max_tokens에 걸려 잘리면 같은 요청을 되풀이하지 않고 묶음을 반으로 나눠 다시 보낸다.
- API 키는 함수 인자로만 받고 어디에도 저장하지 않는다.
"""
import json, os, re, time, hashlib
import rvtool as rv

PROMPT_VERSION = "api-prompt-1.0.0"
ENGINE_VERSION = "engine_api-1.2.0"

class ResumeMismatch(RuntimeError):
    """재개하려는 실행과 입력·설정이 다를 때."""
class CacheInvalid(RuntimeError):
    """완료 캐시 파일이 검증을 통과하지 못할 때."""
SYSTEM = """You annotate sentences from chemistry research articles for a reporting-verb reading tool.
Return ONLY a JSON object, no prose and no code fences: {"results":[...]} with exactly one object per input sentence, using the same sentence_id.

Each result object has these keys:
- sentence_id (string, copied exactly)
- has_citation (boolean): true if the sentence contains a bracketed numeric citation like [12], [3,4], [7–9] or [23]−[25].
- citation_numbers (array of integers): every cited number, ranges expanded, duplicates removed, ascending. [] if no citation.
- reporting_verb (string): verbs that report PRIOR research cited in this sentence (another source's finding, claim, procedure, or statement), joined by ", ". Empty string if none or if has_citation is false.
  Include auxiliaries, negation and adverbs inside the verb phrase (e.g. "have been reported", "did not cite", "have already demonstrated"); exclude adverbs before the first auxiliary ("also reported" -> "reported").
  Coordinated verbs that are each a separable reporting act count separately ("recovered and reused" -> "recovered, reused"); fixed phrases count once ("points out", "makes the case").
  Do not count the current authors' own procedures or results, references to figures/tables ("Figure 2 shows"), or nouns/adjectives.
- citation_form (string): "integral" if the cited author's name appears in the sentence (e.g. "Chen et al. [32] reported"), "non_integral" if only the number appears, "" if there is no citation OR the sentence mixes both kinds (then say so in note).
- note (string): short reason for uncertain or mixed cases, otherwise "".
- hits (array): every verb in the sentence that reports or describes research activity, results, interpretation, or points to figures/tables. For each hit:
  text (exact substring of the sentence, same verb-phrase span rule as above), occurrence (1 for the first occurrence of that exact text in the sentence, 2 for the second, ...),
  role: one of "prior" (reports prior cited research), "result" (presents the current study's results), "interpret" (interprets or argues), "method" (the current study's procedures), "ref" (points to a figure, table or another section), "uncertain" (cannot tell whether prior or current research),
  attr: one of "선행연구", "현재 연구", "현재 연구(본문 지시)", "불명",
  agent: who or what is the subject/agent, one of "선행연구", "필자", "자료·측정", "연구 대상(물질·시료)", "그림·표", "앞 내용 지시", "수동(행위자 생략)", "기타", "불명".
If has_citation is false, reporting_verb and citation_form must be "" and citation_numbers must be [].
"""
ALLOWED_RESULT_KEYS = {"sentence_id","has_citation","citation_numbers","reporting_verb","citation_form","note","hits"}
AGENTS = {"선행연구","필자","자료·측정","연구 대상(물질·시료)","그림·표","앞 내용 지시","수동(행위자 생략)","기타","불명"}

class AnthropicCaller:
    """실제 호출. model은 Anthropic 문서의 모델 ID를 쓴다."""
    def __init__(self, api_key, model, max_tokens=4000, timeout=120):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key, timeout=timeout)
        self.sdk = getattr(anthropic, "__version__", "")
        self.model, self.max_tokens = model, max_tokens
    def __call__(self, system, user):
        # temperature 등 샘플링 인자는 넣지 않는다(제공자 기본값).
        r = self.client.messages.create(model=self.model, max_tokens=self.max_tokens,
                                        system=system, messages=[{"role": "user", "content": user}])
        return "".join(b.text for b in r.content if getattr(b, "type", "") == "text"), dict(id=r.id, stop_reason=r.stop_reason,
                usage=dict(input_tokens=r.usage.input_tokens, output_tokens=r.usage.output_tokens))
    def settings(self):
        return dict(provider="anthropic", model=self.model, max_tokens=self.max_tokens, sampling="제공자 기본값", sdk=self.sdk)

def chunks(ids, size):
    return [ids[i:i+size] for i in range(0, len(ids), size)]

def estimate(doc, ids, chunk_size):
    m = doc.by_id(); chars = sum(len(m[i].text) for i in ids)
    n = len(chunks(ids, chunk_size))
    return dict(sentences=len(ids), chunks=n, sentence_chars=chars,
                rough_input_tokens=int((chars + n * len(SYSTEM)) / 4), note="대략적인 추정이며 실제 요금은 제공자 요금표로 확인하세요")

def _strip(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    return t

def parse_chunk(text, doc, ids):
    """응답을 해석하고 검사한다. 문제가 있으면 ValueError(설명)."""
    obj = json.loads(_strip(text))
    if not isinstance(obj, dict) or not isinstance(obj.get("results"), list): raise ValueError("results 배열이 없습니다")
    res = obj["results"]; got = [r.get("sentence_id") for r in res]
    if sorted(got) != sorted(ids) or len(got) != len(set(got)): raise ValueError(f"문장 ID 대응 불일치: 받은 {got[:6]}… / 보낸 {ids[:6]}…")
    m = doc.by_id(); core, whole, invalid, checks = [], [], [], []
    for r in res:
        extra = set(r) - ALLOWED_RESULT_KEYS
        if extra: raise ValueError(f"허용되지 않은 키 {extra} ({r.get('sentence_id')})")
        sid = r["sentence_id"]; s = m[sid].text
        c = {k: r.get(k) for k in ("sentence_id","has_citation","citation_numbers","reporting_verb","citation_form","note")}
        c = dict(document_id=doc.document_id, **c)
        core.append(c)
        code_nums = rv.citation_numbers(s)
        if c["citation_numbers"] != code_nums or bool(c["has_citation"]) != bool(code_nums):
            checks.append(dict(sentence_id=sid, model_numbers=c["citation_numbers"], code_numbers=code_nums, note="모델 응답과 코드 판정이 다름(응답은 그대로 보존)"))
        for h in r.get("hits") or []:
            t, k = h.get("text", ""), int(h.get("occurrence", 1) or 1)
            pos, start = -1, -1
            for _ in range(k):
                pos = s.find(t, pos + 1)
                if pos < 0: break
                start = pos
            role, attr, agent = h.get("role"), h.get("attr"), h.get("agent", "")
            if not t or pos < 0: invalid.append(dict(sentence_id=sid, hit=h, reason="원문에서 표현을 찾지 못함")); continue
            if role not in rv.ROLES or attr not in rv.ATTRS: invalid.append(dict(sentence_id=sid, hit=h, reason="허용되지 않은 role/attr")); continue
            hh = dict(document_id=doc.document_id, sentence_id=sid, text=t, start=start, end=start+len(t), role=role, attr=attr, source="api",
                      agent=agent if agent in AGENTS else "기타")
            whole.append(hh)
    return core, whole, invalid, checks

def make_manifest(doc, caller, ids, chunk_size):
    st = caller.settings() if hasattr(caller, "settings") else {}
    return dict(document_id=doc.document_id, document_version=doc.document_version,
                input_sha256=dict(txt=doc.hashes["txt"], tsv=doc.hashes["tsv"]),
                sentence_ids=list(ids), chunk_size=chunk_size,
                provider=st.get("provider"), model=st.get("model"), max_tokens=st.get("max_tokens"),
                prompt_version=PROMPT_VERSION, system_prompt_sha256=hashlib.sha256(SYSTEM.encode()).hexdigest(),
                engine_version=ENGINE_VERSION)

def check_manifest(old, new):
    return [f"{k}: 처음 {old.get(k)!r} / 지금 {new.get(k)!r}" for k in sorted(set(old) | set(new)) if old.get(k) != new.get(k)]

def validate_chunk(core, whole, doc, part):
    return rv.validate_core(core, doc, part) + rv.validate_whole(whole, doc) + \
        [f"요청하지 않은 ID 결과: {sorted({c['sentence_id'] for c in core} - set(part))}"] * bool({c["sentence_id"] for c in core} - set(part))

def _call_part(doc, caller, work, part, label, max_retries, sleep, usage, log, name):
    """문장 묶음 하나를 보내고 검사한다. 성공하면 ((core, whole, invalid, checks), 원본 파일 목록), 끝내 실패하면 None.
    응답이 max_tokens에 걸려 잘리면 같은 요청을 되풀이하지 않고 반으로 나눠 각각 보낸다(나눈 조각 중 하나라도 실패하면 묶음 전체가 실패)."""
    m = doc.by_id()
    user = json.dumps(dict(document_id=doc.document_id, sentences=[dict(sentence_id=i, text=m[i].text) for i in part]), ensure_ascii=False)
    for attempt in range(1, max_retries + 1):
        raw_path = os.path.join(work, f"{label}_try{attempt}.raw.json")
        if os.path.exists(raw_path): raw_path = raw_path.replace(".raw.json", f"_{rv.uuid.uuid4().hex[:4]}.raw.json")
        try:
            text, meta = caller(SYSTEM, user)
        except Exception as e:
            rv.write_json_once(raw_path, dict(error=f"{type(e).__name__}: {e}", at=rv.now_iso()))
            log(f"{name}: 호출 오류(시도 {attempt}/{max_retries}) {type(e).__name__}"); time.sleep(sleep * attempt); continue
        rv.write_json_once(raw_path, dict(response_text=text, meta=meta, at=rv.now_iso()))
        usage.append((meta or {}).get("usage", {}))
        if (meta or {}).get("stop_reason") == "max_tokens":
            rv.write_json_once(raw_path.replace(".raw.json", ".truncated.json"), dict(sentence_ids=part, note="max_tokens에 걸려 응답이 잘림"))
            if len(part) == 1:
                log(f"{name}: 한 문장의 응답도 max_tokens를 넘었습니다. MAX_TOKENS를 늘려 주세요"); return None
            half = (len(part) + 1) // 2
            log(f"{name}: 응답이 max_tokens에 걸려 잘림 → {len(part)}문장을 {half}+{len(part) - half}로 나눠 다시 보냄")
            a = _call_part(doc, caller, work, part[:half], label + "a", max_retries, sleep, usage, log, name)
            b = _call_part(doc, caller, work, part[half:], label + "b", max_retries, sleep, usage, log, name) if a else None
            if not (a and b): return None
            return tuple(x + y for x, y in zip(a[0], b[0])), a[1] + b[1]
        try:
            c, w, inv, ch = parse_chunk(text, doc, part)
        except Exception as e:
            rv.write_json_once(raw_path.replace(".raw.json", ".parse_error.json"), dict(error=str(e)[:500]))
            log(f"{name}: 응답 형식 오류(시도 {attempt}/{max_retries}) {str(e)[:120]}"); time.sleep(sleep); continue
        probs = validate_chunk(c, w, doc, part)
        if probs:   # 스키마·ID·위치 검사 실패: 완료 캐시를 만들지 않고 다시 부른다
            rv.write_json_once(raw_path.replace(".raw.json", ".schema_error.json"), dict(problems=probs[:50]))
            log(f"{name}: 스키마·ID·위치 검사 실패(시도 {attempt}/{max_retries}) {probs[0][:120]}"); time.sleep(sleep); continue
        return (c, w, inv, ch), [dict(file=os.path.basename(raw_path), sha256=rv.sha256_file(raw_path), sentence_ids=part)]
    return None

def is_saved(run_root, doc, run_id):
    """그 실행이 이미 정식 저장(run.json)까지 끝났는가."""
    return bool(run_id) and os.path.exists(os.path.join(rv.run_dir(run_root, doc, run_id), "run.json"))

def analyze(doc, caller, run_root, run_id=None, sentence_ids=None, chunk_size=20, max_retries=3, sleep=2.0, log=print):
    """chunk마다 호출·검사·중간 저장. (core, whole, record_fields, extras)를 돌려준다. 저장(save_run)은 노트북에서 한다."""
    ids = sentence_ids or [s.id for s in doc.sentences]
    m = doc.by_id()
    unknown = [i for i in ids if i not in m]
    if unknown: raise rv.InputError(f"입력에 없는 문장 ID: {unknown}")
    resuming = run_id is not None
    run_id = run_id or rv.new_run_id("api")
    work = os.path.join(rv.run_dir(run_root, doc, run_id), "work")
    if os.path.exists(os.path.join(rv.run_dir(run_root, doc, run_id), "run.json")):
        raise ResumeMismatch(f"이미 저장이 끝난 실행입니다(재개 불가): {run_id}")
    manifest = make_manifest(doc, caller, ids, chunk_size)
    mpath = os.path.join(work, "manifest.json")
    if os.path.exists(mpath):
        diffs = check_manifest(json.load(open(mpath, encoding="utf-8")), manifest)
        if diffs: raise ResumeMismatch("처음 실행과 입력·설정이 달라 재개하지 않습니다:\n  " + "\n  ".join(diffs))
        log(f"재개: 입력·설정이 처음 실행과 같습니다({run_id})")
    else:
        if resuming:   # 잘못 적은 ID로 새 유료 실행이 시작되지 않게 멈춘다
            raise ResumeMismatch(f"재개할 실행을 찾지 못했습니다(manifest.json 없음): {run_id}\n"
                                 f"  실행 ID를 확인하세요. 새로 실행하려면 RESUME에서 이 논문을 빼세요. 찾은 위치: {work}")
        os.makedirs(work, exist_ok=True); rv.write_json_once(mpath, manifest)
        log(f"새 실행 ID: {run_id} (끊기면 이 ID로 재개)")
    plan = chunks(ids, chunk_size)
    sys_sha = hashlib.sha256(SYSTEM.encode()).hexdigest()
    core, whole, invalid, checks, failed, usage = [], [], [], [], [], []
    for k, part in enumerate(plan):
        done = os.path.join(work, f"chunk_{k:03d}.ok.json")
        if os.path.exists(done):
            d = json.load(open(done, encoding="utf-8"))
            probs = validate_chunk(d.get("core", []), d.get("whole", []), doc, part)
            if d.get("sentence_ids") != part: probs.append("캐시의 문장 ID 목록이 이 묶음과 다름")
            if probs: raise CacheInvalid(f"완료 캐시가 검증을 통과하지 못했습니다({done}): {probs[:3]}")
            log(f"묶음 {k+1}/{len(plan)}: 이전 실행에서 끝남(캐시 재검증 통과), 건너뜀")
            core += d["core"]; whole += d["whole"]; invalid += d["invalid"]; checks += d["checks"]; continue
        res = _call_part(doc, caller, work, part, f"chunk_{k:03d}", max_retries, sleep, usage, log, f"묶음 {k+1}")
        if res is None:
            failed += part; log(f"묶음 {k+1}: 끝내 실패 → {len(part)}문장을 '실패'로 기록(대체하지 않음)"); continue
        (c, w, inv, ch), raws = res
        rv.write_json_once(done, dict(sentence_ids=part, core=c, whole=w, invalid=inv, checks=ch, raw_files=raws))
        core += c; whole += w; invalid += inv; checks += ch
        log(f"묶음 {k+1}/{len(plan)}: 완료({len(part)}문장)")
    fields = dict(run_id=run_id, model=getattr(caller, "model", None), settings=caller.settings() if hasattr(caller, "settings") else {},
                  prompt_version=PROMPT_VERSION, system_prompt_sha256=sys_sha, chunk_size=chunk_size, max_retries=max_retries,
                  use_annotations=False, api_called=True,
                  engine_version=ENGINE_VERSION,
                  processing=dict(requested=len(ids), requested_ids=list(ids), succeeded=len(ids) - len(failed), failed=len(failed), failed_ids=failed),
                  usage_total=dict(input_tokens=sum(u.get("input_tokens", 0) for u in usage), output_tokens=sum(u.get("output_tokens", 0) for u in usage)))
    return core, whole, fields, dict(invalid_hits=invalid, citation_checks=checks)
