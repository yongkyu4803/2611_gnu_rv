"""오프라인 시험: 입력 검사·인용 정규화·저장(덮어쓰기 금지)·검증·로컬 엔진·API 엔진(가짜 호출).
실제 API 호출 시험은 여기에 없다(키가 필요). 결과는 tests/test_log.json에 남는다."""
import sys, os, json, shutil, tempfile, csv
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, ROOT)
import rvtool as rv, engine_local as L, engine_api as API
log, T = [], tempfile.mkdtemp()
def check(name, cond, detail=""):
    log.append(dict(test=name, passed=bool(cond), detail=str(detail)[:300])); print(("통과" if cond else "실패"), name, detail if not cond else "")
def doc(d): return rv.load_document(f"{ROOT}/inputs/{d}_input.txt", f"{ROOT}/inputs/{d}_structure.tsv", d, f"{ROOT}/annotations/{d}_draft_v1.3.csv", document_version="preproc-v1.2-xml-20261015")
A, B = doc("paper_a"), doc("paper_b")
check("입력: A 249문장·64문단", len(A.sentences) == 249 and len({s.paragraph_id for s in A.sentences}) == 64)
check("입력: B 215문장·48문단", len(B.sentences) == 215 and len({s.paragraph_id for s in B.sentences}) == 48)
# 입력 오류 감지
bad = os.path.join(T, "dup.txt"); lines = open(f"{ROOT}/inputs/paper_a_input.txt", encoding="utf-8").read().splitlines()
body = [l for l in lines if not l.startswith("#")]; open(bad, "w", encoding="utf-8").write("\n".join(body + [body[0]]))
try: rv.read_txt(bad); check("입력: 중복 ID 거부", False)
except rv.InputError as e: check("입력: 중복 ID 거부", True, e)
bad2 = os.path.join(T, "tab.txt"); open(bad2, "w", encoding="utf-8").write("1-001\tA\tB\n")
try: rv.read_txt(bad2); check("입력: 문장 안 탭 경고·중단", False)
except rv.InputError as e: check("입력: 문장 안 탭 경고·중단", True, e)
# 인용 정규화
check("인용: [23–25]", rv.citation_numbers("x [23–25].") == [23, 24, 25])
check("인용: [23]−[25]", rv.citation_numbers("x [23]−[25] y") == [23, 24, 25])
check("인용: [23,24,24]", rv.citation_numbers("x [23,24,24]") == [23, 24])
check("인용: 코드 판정이 초안 CSV 번호와 전부 일치(A·B)", all([int(x) for x in D.annotations[s.id]["citation_numbers"].split(";") if x] == rv.citation_numbers(s.text) for D in (A, B) for s in D.sentences))
# 로컬 엔진
for D in (A, B):
    core, whole, excl, f = L.analyze(D)
    check(f"로컬: {D.document_id} core 스키마·ID 검사", rv.validate_core(core, D) == [], rv.validate_core(core, D)[:3])
    check(f"로컬: {D.document_id} whole 스키마·위치 검사", rv.validate_whole(whole, D) == [], rv.validate_whole(whole, D)[:3])
    check(f"로컬: {D.document_id} 독립 모드는 주석 재사용 표현 없음", all(h["source"] == "local_rules" for h in whole))
core_r, whole_r, _, f_r = L.analyze(A, use_annotations=True)
check("로컬: 주석 재사용 모드는 source=annotation_reuse로 구분", any(h["source"] == "annotation_reuse" for h in whole_r) and f_r["use_annotations"])
core, whole, excl, f = L.analyze(A, sentence_ids=[i for d, i in rv.SMOKE])
check("스모크(로컬): 3.2.3-007 reported 탐지", next(c for c in core if c["sentence_id"] == "3.2.3-007")["reporting_verb"] == "reported")
check("스모크(로컬): 3.3.1-012 번호 [40,41]", next(c for c in core if c["sentence_id"] == "3.3.1-012")["citation_numbers"] == [40, 41])
# 저장·덮어쓰기 금지·재호출
rid = rv.new_run_id("local"); rec = rv.base_record(A, "local", rid, ["core_v1.3", "whole_paper_hits_0.1"], **f)
d = rv.save_run(T, A, rid, rec, core, whole)
try: rv.save_run(T, A, rid, rec, core, whole); check("저장: 같은 run_id 덮어쓰기 거부", False)
except FileExistsError: check("저장: 같은 run_id 덮어쓰기 거부", True)
r = rv.load_run(T, "paper_a", rid); check("재호출: 해시 확인 후 같은 내용", r["core"] == core and r["whole"] == whole)
open(os.path.join(d, "core.json"), "a").write(" ")
try: rv.load_run(T, "paper_a", rid); check("재호출: 저장 후 변경 감지", False)
except ValueError: check("재호출: 저장 후 변경 감지", True)
# API 엔진: 가짜 호출(실제 API 아님)
def fake_ok(ids, D):
    m = D.by_id(); out = []
    for i in ids:
        s = m[i].text; nums = rv.citation_numbers(s); a = D.annotations[i]
        out.append(dict(sentence_id=i, has_citation=bool(nums), citation_numbers=nums, reporting_verb=a.get("reporting_verb", "") if nums else "",
                        citation_form=a.get("citation_form", "") if nums else "", note="", hits=[dict(text=v, occurrence=1, role="prior", attr="선행연구", agent="선행연구") for v in a.get("reporting_verb", "").split(", ") if v]))
    return json.dumps(dict(results=out), ensure_ascii=False)
class Fake:
    model = "FAKE-no-network"
    def __init__(self, D, plan): self.D, self.plan, self.calls = D, plan, 0
    def settings(self): return dict(provider="fake", model=self.model)
    def __call__(self, system, user):
        self.calls += 1; ids = [x["sentence_id"] for x in json.loads(user)["sentences"]]
        step = self.plan.pop(0) if self.plan else "ok"
        if step == "raise": raise TimeoutError("가짜 시간 초과")
        if step == "garbage": return "죄송합니다, JSON이 아닙니다", dict(usage={})
        return "```json\n" + fake_ok(ids, self.D) + "\n```", dict(usage=dict(input_tokens=1, output_tokens=1))
ids = [i for d, i in rv.SMOKE]
c, w, fl, ex = API.analyze(A, Fake(A, ["garbage", "ok"]), T, sentence_ids=ids, chunk_size=20, sleep=0, log=lambda *a: None)
check("API(가짜): 형식 오류 뒤 재시도로 성공", fl["processing"]["failed"] == 0 and rv.validate_core(c, A, ids) == [])
check("API(가짜): 원본 응답 보관", len([p for p in os.listdir(os.path.join(T, "paper_a", fl["run_id"], "work")) if p.endswith(".raw.json")]) == 2)
c2, w2, fl2, ex2 = API.analyze(A, Fake(A, ["raise", "raise", "raise"]), T, sentence_ids=ids, sleep=0, log=lambda *a: None)
check("API(가짜): 3회 실패 시 '실패' 기록, 대체 결과 없음", fl2["processing"]["failed"] == 2 and c2 == [] and w2 == [])
f3 = Fake(A, ["ok"]); part = [s.id for s in A.sentences[:45]]
c3, w3, fl3, _ = API.analyze(A, f3, T, sentence_ids=part, chunk_size=20, sleep=0, log=lambda *a: None)
f4 = Fake(A, []); c4, w4, fl4, _ = API.analyze(A, f4, T, run_id=fl3["run_id"], sentence_ids=part, chunk_size=20, sleep=0, log=lambda *a: None)
check("API(가짜): 같은 run_id 재개 시 끝난 묶음은 다시 부르지 않음", f4.calls == 0 and c4 == c3)
check("API(가짜): whole 위치 검사", rv.validate_whole(w3, A) == [])
# 화면
core_b, whole_b, _, fb = L.analyze(B)
rb = rv.new_run_id("local"); rv.save_run(T, B, rb, rv.base_record(B, "local", rb, ["core_v1.3", "whole_paper_hits_0.1"], **fb), core_b, whole_b)
ra = rv.new_run_id("local"); core_a, whole_a, _, fa = L.analyze(A); rv.save_run(T, A, ra, rv.base_record(A, "local", ra, ["core_v1.3", "whole_paper_hits_0.1"], **fa), core_a, whole_a)
out = rv.build_viewer([rv.load_run(T, "paper_a", ra), rv.load_run(T, "paper_b", rb)], [A, B], os.path.join(T, "viewer.html"))
check("화면: HTML 생성", os.path.getsize(out) > 100000)
try: rv.build_viewer([rv.load_run(T, "paper_a", ra), rv.load_run(T, "paper_b", rb)], [A, B], out); check("화면: 덮어쓰기 거부", False)
except FileExistsError: check("화면: 덮어쓰기 거부", True)
shutil.copy(out, os.path.join(HERE, "viewer_test_output.html"))

# ======================= 회귀 시험(2026-10-19 수정분) =======================
import copy
def ok_file(root, D, rid, k=0): return os.path.join(root, D.document_id, rid, "work", f"chunk_{k:03d}.ok.json")
class Scripted(Fake):
    """plan 항목: 'ok' | 'raise' | 'garbage' | 'badschema'(형식은 JSON이지만 스키마 위반) | 'badpos'(원문에 없는 표현)"""
    def __call__(self, system, user):
        step = self.plan[0] if self.plan else "ok"
        if step in ("badschema", "badpos"):
            self.plan.pop(0); self.calls += 1
            ids = [x["sentence_id"] for x in json.loads(user)["sentences"]]
            obj = json.loads(fake_ok(ids, self.D))
            if step == "badschema": obj["results"][0]["citation_form"] = "integralX"
            else: obj["results"][0]["hits"] = [dict(text="NOT_IN_SENTENCE", occurrence=1, role="prior", attr="선행연구", agent="선행연구")]
            return json.dumps(obj, ensure_ascii=False), dict(usage={})
        return super().__call__(system, user)
# R1 스키마 검증 전에는 완료 캐시를 만들지 않음
R = tempfile.mkdtemp()
c, w, fl, _ = API.analyze(A, Scripted(A, ["badschema", "ok"]), R, sentence_ids=ids, sleep=0, log=lambda *a: None)
work = os.path.join(R, "paper_a", fl["run_id"], "work")
check("회귀 R1-a: 스키마 위반 응답 뒤 재시도 성공, 위반 기록 남김", fl["processing"]["failed"] == 0 and any(p.endswith(".schema_error.json") for p in os.listdir(work)))
c, w, fl, _ = API.analyze(A, Scripted(A, ["badschema"] * 3), R, sentence_ids=ids, sleep=0, log=lambda *a: None)
check("회귀 R1-b: 3회 모두 스키마 위반이면 완료 캐시 없음·실패 기록", not os.path.exists(ok_file(R, A, fl["run_id"])) and fl["processing"]["failed"] == 2 and c == [])
c, w, fl, ex = API.analyze(A, Scripted(A, ["badpos"]), R, sentence_ids=ids, sleep=0, log=lambda *a: None)
check("회귀 R1-c: 원문에 없는 표현은 캐시·결과에 들어가지 않고 별도 목록", fl["processing"]["failed"] == 0 and all(h["text"] != "NOT_IN_SENTENCE" for h in w) and len(ex["invalid_hits"]) == 1)
# R2 손상된 완료 캐시는 재개 때 다시 검증해서 멈춤
c, w, fl, _ = API.analyze(A, Scripted(A, []), R, sentence_ids=ids, sleep=0, log=lambda *a: None)
of = ok_file(R, A, fl["run_id"]); d = json.load(open(of, encoding="utf-8")); d["core"][0]["citation_form"] = "integralX"
os.chmod(of, 0o644); json.dump(d, open(of, "w", encoding="utf-8"), ensure_ascii=False)
try: API.analyze(A, Scripted(A, []), R, run_id=fl["run_id"], sentence_ids=ids, sleep=0, log=lambda *a: None); check("회귀 R2: 손상 캐시 재개 거부", False)
except API.CacheInvalid: check("회귀 R2: 손상 캐시 재개 거부", True)
# R3 재개 시 입력·설정 동일성 검사
base = Scripted(A, ["ok"]); c, w, fl, _ = API.analyze(A, base, R, sentence_ids=part, chunk_size=20, sleep=0, log=lambda *a: None)
RID = fl["run_id"]
def resume_with(D=A, caller=None, ids_=part, cs=20):
    try:
        API.analyze(D, caller or Scripted(A, []), R, run_id=RID, sentence_ids=ids_, chunk_size=cs, sleep=0, log=lambda *a: None); return "재개됨"
    except API.ResumeMismatch as e: return "거부"
other = Scripted(A, []); other.model = "OTHER-MODEL"
check("회귀 R3-a: 모델이 다르면 재개 거부", resume_with(caller=other) == "거부")
check("회귀 R3-b: 묶음 크기가 다르면 재개 거부", resume_with(cs=10) == "거부")
check("회귀 R3-c: 문장 목록이 다르면 재개 거부", resume_with(ids_=part[:-1]) == "거부")
mod = os.path.join(T, "paper_a_input_mod.txt"); open(mod, "w", encoding="utf-8").write(open(f"{ROOT}/inputs/paper_a_input.txt", encoding="utf-8").read().replace("# 저자:", "# 저자(수정):"))
A_mod = rv.load_document(mod, f"{ROOT}/inputs/paper_a_structure.tsv", "paper_a", document_version="preproc-v1.2-xml-20261015")
check("회귀 R3-d: 입력 파일 해시가 다르면 재개 거부", resume_with(D=A_mod) == "거부")
A_v = rv.load_document(f"{ROOT}/inputs/paper_a_input.txt", f"{ROOT}/inputs/paper_a_structure.tsv", "paper_a", document_version="other-version")
check("회귀 R3-e: document_version이 다르면 재개 거부", resume_with(D=A_v) == "거부")
same = Scripted(A, []); check("회귀 R3-f: 모두 같으면 재개, 호출 0회", resume_with(caller=same) == "재개됨" and same.calls == 0)
rv.save_run(R, A, RID, rv.base_record(A, "api", RID, ["core_v1.3"], **{k: v for k, v in fl.items() if k != "run_id"}), c, w)
check("회귀 R3-g: 저장이 끝난 실행은 재개 거부", resume_with(caller=Scripted(A, [])) == "거부")
# R4 소량 시험의 정식 저장·다시 읽기·부분 화면
c, w, fl, ex = API.analyze(A, Scripted(A, []), R, sentence_ids=ids, sleep=0, log=lambda *a: None)
rec = rv.base_record(A, "api", fl["run_id"], ["core_v1.3", "whole_paper_hits_0.1"], run_kind="smoke", **{k: v for k, v in fl.items() if k != "run_id"})
rv.save_run(R, A, fl["run_id"], rec, c, w, extra=ex); rr = rv.load_run(R, "paper_a", fl["run_id"])
check("회귀 R4-a: 소량 시험 정식 저장·다시 읽기(해시 확인)", rr["record"]["run_kind"] == "smoke" and rr["record"]["processing"]["requested_ids"] == ids and rv.validate_core(rr["core"], A, ids) == [])
pv = rv.build_viewer([rr], [A], os.path.join(R, "smoke_view.html")); html = open(pv, encoding="utf-8").read()
dat = json.loads(html.split("const DATA=", 1)[1].split(";\nconst SRC", 1)[0].replace("<\\/", "</"))
check("회귀 R4-b: 부분 화면(논문 하나, 2문장만 분석·나머지 미분석 표시)", len(dat) == 1 and dat[0]["run"]["partial"] and dat[0]["run"]["analyzed"] == 2
      and sum(1 for x in dat[0]["s"] if not x["u"]) == 2 and sum(1 for x in dat[0]["s"] if x["u"]) == 247)
shutil.copy(pv, os.path.join(HERE, "viewer_smoke_partial_test_output.html"))
# R5 불일치 후보에 보고동사 문자열 차이 포함
core_d = []
for s_ in A.sentences:
    a_ = A.annotations[s_.id]; nums = rv.citation_numbers(s_.text)
    core_d.append(dict(document_id="paper_a", sentence_id=s_.id, has_citation=bool(nums), citation_numbers=nums,
                       reporting_verb=a_["reporting_verb"] if nums else "", citation_form=a_["citation_form"] if nums else "", note=""))
tgt = next(x for x in core_d if x["sentence_id"] == "3.3.1-012"); tgt["reporting_verb"] = "also reported"   # 유무는 같고 문자열만 다름
ag = rv.agreement_with_annotations(core_d, A)
row = [r for r in ag["disagreement_candidates"] if r["sentence_id"] == "3.3.1-012"]
check("회귀 R5: 보고동사 문자열만 다른 문장도 불일치 후보에 포함", len(row) == 1 and row[0]["differences"] == ["보고동사 문자열"] and len(ag["disagreement_candidates"]) == 1)
# R8 (0.4.2) 코랩 실습에서 발견: paper_a 3.2.3-007 "Chen et al.[32] reported"의 주어가 '불명'으로 나옴
c8, h8, _ = L.analyze_sentence("paper_a", A.by_id()["3.2.3-007"], "en_core_web_sm")
check("회귀 R8-a: 3.2.3-007 reported → 선행연구 보고, 주어 선행연구(Chen et al.[32])",
      len(h8) == 1 and h8[0]["role"] == "prior" and h8[0]["agent"] == "선행연구" and h8[0].get("agent_text", "").startswith("Chen et al."), h8)
c8b, h8b, _ = L.analyze_sentence("paper_a", A.by_id()["3.2.3-008"], "en_core_web_sm")
check("회귀 R8-b: 3.2.3-008 'The results … by Chen et al.[32] were compared'는 문법 주어(results)를 유지",
      any(h["text"] == "were compared" and h["agent"] == "자료·측정" for h in h8b), h8b)
_, h8c, _ = L.analyze_sentence("x", rv.Sentence("9-001", 1, "Lee and Kim [7] have shown that the yield depends on temperature.", "RD", "9", "x", "P001", 1, 9), "en_core_web_sm")
check("회귀 R8-c: 'Lee and Kim [7] have shown'도 선행연구", h8c and h8c[0]["agent"] == "선행연구", h8c)

# R9 전처리 기록 대조
check("회귀 R9-a: 두 논문 모두 전처리 기록과 일치", all(r["status"] == "일치" for D in (A, B) for r in rv.check_preprocessing_record(D)))
A9 = rv.load_document(f"{ROOT}/inputs/paper_a_input.txt", f"{ROOT}/inputs/paper_a_structure.tsv", "paper_a", document_version="v"); A9.meta["총 문장 수"] = "250"
check("회귀 R9-b: 기록과 다르면 '불일치'", [r["status"] for r in rv.check_preprocessing_record(A9)][0] == "불일치")
A9.meta.pop("총 문장 수"); check("회귀 R9-c: 기록이 없으면 '기록 없음'", [r["status"] for r in rv.check_preprocessing_record(A9)][0] == "기록 없음")

# R7 저장 전 검증(save_validated_run): 문제가 있으면 아무것도 저장하지 않음
core_v, whole_v, excl_v, f_v = L.analyze(A)
bad_whole = [dict(h) for h in whole_v]; bad_whole[0]["end"] += 1
rid_v = rv.new_run_id("research-practice")
try:
    rv.save_validated_run(R, A, rid_v, rv.base_record(A, "local", rid_v, ["core_v1.3"], **f_v), core_v, bad_whole); check("회귀 R7-a: 위치가 틀린 결과는 저장 거부", False)
except rv.ValidationFailed:
    check("회귀 R7-a: 위치가 틀린 결과는 저장 거부", not os.path.exists(os.path.join(R, "paper_a", rid_v)))
d_ok = rv.save_validated_run(R, A, rid_v, rv.base_record(A, "local", rid_v, ["core_v1.3"], **f_v), core_v, whole_v, extra=dict(excluded=excl_v))
check("회귀 R7-b: 검증 통과 시 저장·검증 기록·제외 후보 파일", os.path.exists(os.path.join(d_ok, "excluded.json")) and json.load(open(os.path.join(d_ok, "run.json")))["validation"]["core"] == "통과")

# R6 (0.4.1) 학생 실습 문장에서 드러난 규칙 보완
def one(t):
    c_, h_, _ = L.analyze_sentence("x", rv.Sentence("9-001", 1, t, "RD", "9", "x", "P001", 1, 5), "en_core_web_sm"); return h_
h = one("Smith et al. [5] demonstrated that the yield increased at higher temperatures.")
check("회귀 R6-a: 'Smith et al. [5] demonstrated' 주어를 선행연구로", h and h[0]["role"] == "prior" and h[0]["agent"] == "선행연구", h)
h = one("The details are found in Table 3.")
check("회귀 R6-b: 'are found in Table 3'은 그림·표 지시", h and h[0]["role"] == "ref", h)
h = one("We found that the extraction yield was highest at 60 °C.")
check("회귀 R6-c: 'We found'는 자기 결과(바뀌지 않음)", h and h[0]["role"] == "result" and h[0]["agent"] == "필자", h)


# ======================= 회귀 시험(2026-11-02 수정분) =======================
# R10 재개: 저장이 끝난 실행 확인, 잘못 적은 실행 ID로 새 실행을 시작하지 않음
R10 = tempfile.mkdtemp()
c, w, fl, _ = API.analyze(A, Scripted(A, []), R10, sentence_ids=ids, sleep=0, log=lambda *a: None)
check("회귀 R10-a: 저장 전에는 is_saved=False", not API.is_saved(R10, A, fl["run_id"]) and not API.is_saved(R10, A, None))
rv.save_run(R10, A, fl["run_id"], rv.base_record(A, "api", fl["run_id"], ["core_v1.3"], **{k: v for k, v in fl.items() if k != "run_id"}), c, w)
check("회귀 R10-b: 저장 후에는 is_saved=True(노트북이 다시 부르지 않고 건너뜀)", API.is_saved(R10, A, fl["run_id"]))
typo = Scripted(A, [])
try: API.analyze(A, typo, R10, run_id="20990101-000000-api-typo00", sentence_ids=ids, sleep=0, log=lambda *a: None); check("회귀 R10-c: 없는 실행 ID로 재개하면 멈춤", False)
except API.ResumeMismatch: check("회귀 R10-c: 없는 실행 ID로 재개하면 멈춤(호출 0회, 폴더 없음)", typo.calls == 0 and not os.path.exists(os.path.join(R10, "paper_a", "20990101-000000-api-typo00")))
# R11 max_tokens에 걸려 잘린 응답: 같은 요청을 되풀이하지 않고 반으로 나눠 다시 보냄
class Truncating(Fake):
    """limit 문장보다 많이 보내면 응답이 잘린 것처럼 돌려준다."""
    def __init__(self, D, limit): super().__init__(D, []); self.limit, self.sizes = limit, []
    def __call__(self, system, user):
        n = len(json.loads(user)["sentences"]); self.sizes.append(n)
        if n > self.limit: self.calls += 1; return '{"results":[{"sentence_id":', dict(usage=dict(input_tokens=1, output_tokens=4000), stop_reason="max_tokens")
        text, meta = super().__call__(system, user); return text, dict(meta, stop_reason="end_turn")
tr = Truncating(A, 6); part20 = [s.id for s in A.sentences[:20]]
c, w, fl, _ = API.analyze(A, tr, R10, sentence_ids=part20, chunk_size=20, sleep=0, log=lambda *a: None)
okc = json.load(open(ok_file(R10, A, fl["run_id"]), encoding="utf-8"))
check("회귀 R11-a: 잘린 응답은 나눠 보내 모두 성공(20→10→5)", fl["processing"]["failed"] == 0 and rv.validate_core(c, A, part20) == [] and tr.sizes == [20, 10, 5, 5, 10, 5, 5], tr.sizes)
check("회귀 R11-b: 완료 캐시에 나눈 조각의 원본 파일이 모두 기록됨", sorted(i for r in okc["raw_files"] for i in r["sentence_ids"]) == sorted(part20) and len(okc["raw_files"]) == 4)
check("회귀 R11-c: 잘림 기록 파일을 남김", len([p for p in os.listdir(os.path.join(R10, "paper_a", fl["run_id"], "work")) if p.endswith(".truncated.json")]) == 3)
tr1 = Truncating(A, 0)
c, w, fl, _ = API.analyze(A, tr1, R10, sentence_ids=ids[:1], sleep=0, log=lambda *a: None)
check("회귀 R11-d: 한 문장도 잘리면 되풀이하지 않고 '실패'(호출 1회)", fl["processing"]["failed"] == 1 and tr1.calls == 1 and c == [])
# R12 (0.4.3) 인용 방식: by/of/from 뒤 소문자 낱말은 저자명이 아님, "et al.,[19]"의 쉼표 허용
check("회귀 R12-a: 'peaks from cellulose [56]'은 비통합", L.citation_form("leaving only the sharper peaks from cellulose [56].")[0] == "non_integral")
check("회귀 R12-b: 'adapted from reference [25]'는 비통합", L.citation_form("conditions were adapted from reference [25]: 3 g")[0] == "non_integral")
check("회귀 R12-c: 'According to Martins et al.,[19]'는 통합", L.citation_form("According to Martins et al.,[19] DESs are")[0] == "integral")
check("회귀 R12-d: 'Chen et al. [32] reported'는 그대로 통합", L.citation_form("Chen et al. [32] reported that")[0] == "integral")
check("회귀 R12-e: 'method of Folch [12]'처럼 대문자 이름은 그대로 통합", L.citation_form("using the method of Folch [12].")[0] == "integral")


json.dump(dict(passed=sum(x["passed"] for x in log), total=len(log), tests=log, note="API 시험은 가짜 호출이며 실제 네트워크 호출이 아님"),
          open(os.path.join(HERE, "test_log.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\n{sum(x['passed'] for x in log)}/{len(log)} 통과")
