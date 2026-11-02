import nbformat as nbf
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell

ARRANGE = r'''# 파일 준비: rv_colab.zip 하나를 올리거나, 파일을 하나씩 올려도 됩니다.
# ZIP은 rv_colab.zip 하나만 새 임시 폴더에 풀고, 필수 파일이 모두 있을 때만 현재 폴더에 덮어써 옮깁니다
# (이전에 올린 파일이 새 판본과 섞이지 않게). ZIP과 개별 파일을 섞어 올리면 ZIP 내용이 우선합니다.
import os, zipfile, shutil, tempfile, hashlib
NEED = ["rvtool.py", "engine_local.py", "engine_api.py", "viewer_template.html",
        "schemas/core_v1.3.json", "schemas/whole_paper_hits_v0.1.json",
        "inputs/paper_a_input.txt", "inputs/paper_a_structure.tsv", "inputs/paper_b_input.txt", "inputs/paper_b_structure.tsv"]
OPTIONAL = ["annotations/paper_a_draft_v1.3.csv", "annotations/paper_b_draft_v1.3.csv"]
ZIP_NAME = "rv_colab.zip"
def install_zip(zpath):
    tmp = tempfile.mkdtemp(prefix="rv_zip_")
    with zipfile.ZipFile(zpath) as f: f.extractall(tmp)
    base = os.path.join(tmp, "rv_colab") if os.path.isdir(os.path.join(tmp, "rv_colab")) else tmp
    lacking = [rel for rel in NEED if not os.path.exists(os.path.join(base, rel))]
    if lacking:   # 새 ZIP 자체에 필수 파일이 다 있어야 복사한다(이전 파일이 빈자리를 채우지 않게)
        raise FileNotFoundError(f"올린 ZIP에 필수 파일이 없습니다: {lacking}. 아무것도 복사하지 않았습니다. 최신 {ZIP_NAME}을 올려 주세요.")
    for rel in NEED + OPTIONAL:
        src = os.path.join(base, rel)
        if os.path.exists(src):
            os.makedirs(os.path.dirname(rel) or ".", exist_ok=True); shutil.copy2(src, rel)
    print(f"자료 ZIP: {zpath} (SHA-256 {hashlib.sha256(open(zpath, 'rb').read()).hexdigest()[:16]}…)")
def place_loose_files():
    # 하나씩 올린 자료 파일은 이름을 보고 제자리로 옮긴다(같은 이름이 있으면 새 파일로 바꾼다)
    for rel in NEED + OPTIONAL:
        name = os.path.basename(rel)
        if name != rel and os.path.exists(name):
            os.makedirs(os.path.dirname(rel), exist_ok=True); shutil.move(name, rel)
if os.path.exists(ZIP_NAME): install_zip(ZIP_NAME)
place_loose_files()
missing = [p for p in NEED if not os.path.exists(p)]
if missing:
    try:
        from google.colab import files
        print("다음 파일이 없습니다. 올려 주세요(rv_colab.zip 하나 또는 개별 파일):", missing)
        up = list(files.upload())
        zips = [n for n in up if n.endswith(".zip")]
        if len(zips) > 1: raise FileNotFoundError(f"ZIP 파일은 하나만 올려 주세요(올린 ZIP: {zips})")
        if zips: install_zip(zips[0])
        place_loose_files()
    except ImportError:
        pass
missing = [p for p in NEED if not os.path.exists(p)]
print("필수 파일:", "모두 있음" if not missing else f"없음 → {missing}")
print("선택 파일(초안 주석 CSV):", [p for p in OPTIONAL if os.path.exists(p)])
if missing: raise FileNotFoundError(f"필수 파일이 없습니다: {missing}. 올린 뒤 이 칸을 다시 실행하세요.")
'''

LOAD = r'''import sys, json, importlib
sys.path.insert(0, ".")
import rvtool as rv; importlib.reload(rv)
if not hasattr(rv, "save_validated_run"):
    raise RuntimeError(f"공통 모듈 판본이 이 노트북보다 오래되었습니다({rv.TOOL_VERSION}). 이 노트북과 같은 때 받은 rv_colab.zip을 올려 주세요.")
print("공통 모듈:", rv.TOOL_VERSION)
RUN_ROOT = "rv_runs"            # 실행 결과 저장 폴더(실행마다 새 하위 폴더, 덮어쓰지 않음)
DOC_VERSION = "preproc-v1.2-xml-20261015"   # 입력 판본 이름(입력 파일 머리부에 없어서 여기서 정함)
def load(d):
    ann = f"annotations/{d}_draft_v1.3.csv"
    return rv.load_document(f"inputs/{d}_input.txt", f"inputs/{d}_structure.tsv", d,
                            ann if os.path.exists(ann) else None, document_version=DOC_VERSION)
A, B = load("paper_a"), load("paper_b")
for D in (A, B): print(json.dumps(rv.describe(D), ensure_ascii=False, indent=1))
'''

def local_nb():
    nb = nbf.v4.new_notebook()
    nb.cells = [
        md("""# 보고동사로 다시 읽기 ① 외부 API 없이 분석하기

맥주 찌꺼기를 다룬 화학 논문 두 편(논문 A: ACS Omega 2025, 논문 B: Molecules 2024)을 **논문 전체**에서 다시 읽습니다. 색칠 → 흐름 그래프 → 클릭 → 원래 문맥으로 돌아가기가 중심입니다.

- 분석 엔진: spaCy 구문분석 + 규칙(`engine_local.py`). **외부 AI API를 부르지 않습니다.** 다만 첫 칸에서 spaCy와 영어 모델을 인터넷으로 내려받습니다.
- 결과 두 층: `core`(입력데이터 명세서 v1.3의 문장별 결과, 스키마 수정 없음)와 `whole`(논문 전체 표현별 결과, 별도 스키마 whole_paper_hits v0.1).
- 결과는 **후보**입니다. 사람이 확인하지 않았고, 초안 주석과 비교한 값은 정확도가 아니라 일치도입니다.
- PDF 추출·DOI 수집은 다루지 않습니다(입력은 이미 전처리된 TXT·TSV). SLA 감성분석과는 다른 분석입니다."""),
        md("## 1. 설치"),
        code("!pip -q install spacy jsonschema\n!python -m spacy download en_core_web_sm -q"),
        md("## 2. 파일 준비\n`rv_colab.zip`을 올리면 자동으로 풀립니다. ZIP을 쓸 수 없으면 파일을 하나씩 올려도 됩니다(필수 10개, 선택 2개)."),
        code(ARRANGE),
        md("## 3. 입력 검사\n문장을 다시 나누거나 ID를 바꾸지 않습니다. 중복·누락·순서 불일치·빈 문장·문장 안 탭은 오류로 멈춥니다."),
        code(LOAD),
        md("## 4. 소량 시험(정식 저장·다시 읽기·부분 화면까지)\n명세서의 연결 시험 문장 두 개(논문 A의 3.2.3-007, 3.3.1-012)만 분석하고, 전체 실행과 똑같이 저장 → 다시 읽기 → 검증 → 부분 화면까지 확인합니다. 기대값은 Claude 판정 초안이며 사람이 확인한 정답이 아닙니다."),
        code(r'''import engine_local as L, time; importlib.reload(L)
ids = [i for d, i in rv.SMOKE]
core, whole, excl, f = L.analyze(A, sentence_ids=ids)
rid = rv.new_run_id("local-smoke")
rec = rv.base_record(A, "local", rid, ["core_v1.3", "whole_paper_hits_0.1"], run_kind="smoke", **f)
SMOKE_DIR = rv.save_validated_run(RUN_ROOT, A, rid, rec, core, whole, extra=dict(excluded=excl), expected_ids=ids)   # 검증 실패 시 저장하지 않음
r = rv.load_run(RUN_ROOT, "paper_a", rid)              # 다시 읽기(해시 확인)
for c in r["core"]: print(c)
print("표현 후보:", [(h["sentence_id"], h["text"], h["role"]) for h in r["whole"]])
print("다시 읽은 결과 검사 — core:", rv.validate_core(r["core"], A, ids) or "통과", "/ whole:", rv.validate_whole(r["whole"], A) or "통과")
SMOKE_VIEW = rv.build_viewer([r], [A], f"viewer_local_smoke_{time.strftime('%Y%m%d-%H%M%S')}.html")
print("저장:", SMOKE_DIR, "| 부분 화면:", SMOKE_VIEW, "(분석한 2문장만 색칠, 나머지는 '미분석' 표시)")
try:
    from google.colab import files
    from IPython.display import HTML, display
    display(HTML(open(SMOKE_VIEW, encoding="utf-8").read()))
except ImportError:
    pass'''),
        md("## 5. 전체 분석과 저장\n기본은 **독립 분석**(초안 주석 CSV를 쓰지 않음)입니다. `USE_ANNOTATIONS=True`는 초안 주석을 그대로 가져와 표시하는 별도 모드이며, 그 결과를 같은 CSV와 비교하면 안 됩니다."),
        code(r'''USE_ANNOTATIONS = False
SCOPE = ["core_v1.3", "whole_paper_hits_0.1"]
RUNS = {}
for D in (A, B):
    core, whole, excl, f = L.analyze(D, use_annotations=USE_ANNOTATIONS)
    rid = rv.new_run_id("local")
    rec = rv.base_record(D, "local", rid, SCOPE, **f)
    d = rv.save_validated_run(RUN_ROOT, D, rid, rec, core, whole, extra=dict(excluded=excl))   # 검증 실패 시 저장하지 않음
    RUNS[D.document_id] = rid
    print(D.document_id, "저장:", d, "| 표현", len(whole), "| 제외", len(excl), "| 저장 전 검증: 통과")'''),
        md("## 6. 검증과 다시 읽기\n저장한 파일을 다시 열어 해시가 그대로인지 확인한 뒤 스키마·ID·위치(`sentence[start:end]==text`)를 다시 검사합니다."),
        code(r'''for D in (A, B):
    r = rv.load_run(RUN_ROOT, D.document_id, RUNS[D.document_id])
    print(D.document_id, r["record"]["run_id"], "| core:", rv.validate_core(r["core"], D) or "통과", "| whole:", rv.validate_whole(r["whole"], D) or "통과")
print(json.dumps(rv.list_runs(RUN_ROOT), ensure_ascii=False, indent=1)[:1500])'''),
        md("## 7. 초안 주석과의 일치도(선택)\n초안 주석 CSV가 있을 때만 계산합니다. **Claude 판정 초안과의 일치도이며 정확도가 아닙니다.** 불일치 문장은 어느 쪽이 맞는지 정하지 않은 후보 목록입니다."),
        code(r'''for D in (A, B):
    r = rv.load_run(RUN_ROOT, D.document_id, RUNS[D.document_id])
    if r["record"]["use_annotations"]:
        print(D.document_id, "주석 재사용 모드라 일치도를 계산하지 않습니다"); continue
    ag = rv.agreement_with_annotations(r["core"], D, "독립 분석(로컬 규칙)")
    if ag: print(D.document_id, ag["label"], ag["counts"], "불일치 후보", len(ag["disagreement_candidates"]))'''),
        md("## 8. 절별 집계\n집계 단위는 표현(hit), 분모는 절별 단어 수입니다. 초록은 기본으로 뺍니다. 결과·논의(RD)를 결과와 논의로 나누지 않습니다."),
        code(r'''try:
    import pandas as pd
except ImportError:
    pd = None
for D in (A, B):
    r = rv.load_run(RUN_ROOT, D.document_id, RUNS[D.document_id])
    agg = rv.aggregate(D, r["whole"], exclude_abstract=True, failed_ids=r["record"]["processing"]["failed_ids"])
    print(D.document_id, "| 분석 실패 문장:", agg["failed_sentences"])
    if pd is not None: display(pd.DataFrame(agg["rows"]).pivot(index="role", columns="section_type", values="per_1000_words"))'''),
        md("## 9. 화면 연결: 보고동사로 다시 읽기\n저장된 결과로 화면을 만듭니다. 그래프의 점을 누르면 그 구간 문장 → 앞뒤 문맥·문단 → 전체 본문 위치로 갑니다."),
        code(r'''import time
out = f"viewer_local_{time.strftime('%Y%m%d-%H%M%S')}.html"
rv.build_viewer([rv.load_run(RUN_ROOT, "paper_a", RUNS["paper_a"]), rv.load_run(RUN_ROOT, "paper_b", RUNS["paper_b"])], [A, B], out)
print("화면 파일:", out)
try:
    from google.colab import files
    from IPython.display import HTML, display
    display(HTML(open(out, encoding="utf-8").read()))
    files.download(out)
except ImportError:
    pass'''),
        md("## 10. 결과 내려받기\n`rv_runs` 폴더 전체를 ZIP으로 묶습니다. 이 노트북에서 실행하지 않은 것: 실제 API 분석(② 노트북), 사람 기준의 정확도 평가."),
        code(r'''import shutil
z = shutil.make_archive(f"rv_runs_{time.strftime('%Y%m%d-%H%M%S')}", "zip", RUN_ROOT)
print("내려받을 파일:", z)
try:
    from google.colab import files; files.download(z)
except ImportError:
    pass'''),
    ]
    nb.metadata["kernelspec"] = dict(name="python3", display_name="Python 3", language="python")
    return nb

def api_nb():
    nb = nbf.v4.new_notebook()
    nb.cells = [
        md("""# 보고동사로 다시 읽기 ② 실제 AI API로 분석하기

① 노트북과 같은 입력·검사·저장·화면을 쓰고, 분석 엔진만 **Anthropic Claude API**(`engine_api.py`)로 바꿉니다.

- **전송 안내:** 문장 원문(두 논문 모두 CC BY 4.0 공개 논문)이 Anthropic API로 전송됩니다. 초안 주석 CSV는 보내지 않습니다.
- **비용:** 호출할 때마다 요금이 듭니다. 기본값은 시험 문장 2개만 보내는 소량 실행이고, 전체 실행은 `FULL_RUN=True`로 따로 켜야 합니다.
- **키:** 코랩 왼쪽의 🔑(보안 비밀)에 `ANTHROPIC_API_KEY`로 넣거나, 실행 중 입력창에 붙여 넣습니다. 키는 노트북·로그·결과 파일에 저장되지 않습니다.
- **실패 처리:** 응답 형식이 틀리면 정해진 횟수까지 다시 부르고, 끝내 실패한 문장은 '실패'로 기록합니다. 로컬 결과로 몰래 채우지 않습니다. 응답 원본은 모두 보관합니다.
- 결과는 **후보**이며, 초안 주석과의 비교는 정확도가 아니라 일치도입니다."""),
        md("## 1. 설치"),
        code("!pip -q install anthropic jsonschema spacy\n# spaCy는 화면용 입력 검사에는 필요 없지만, ① 노트북 결과와 함께 쓸 때를 위해 설치합니다."),
        md("## 2. 파일 준비"),
        code(ARRANGE),
        md("## 3. 입력 검사"),
        code(LOAD),
        md("## 4. API 설정\n모델 ID는 Anthropic 문서의 모델 목록(https://docs.claude.com/en/docs/about-claude/models)에서 확인해 넣으세요."),
        code(r'''import getpass, engine_api as API; importlib.reload(API)
MODEL = "claude-sonnet-5-5"     # 문서에서 확인한 모델 ID로 바꿀 수 있습니다
MAX_TOKENS = 4000
CHUNK_SIZE, MAX_RETRIES = 20, 3
def get_key():
    try:
        from google.colab import userdata
        k = userdata.get("ANTHROPIC_API_KEY")
        if k: return k
    except Exception:
        pass
    return getpass.getpass("ANTHROPIC_API_KEY: ")
caller = API.AnthropicCaller(get_key(), MODEL, MAX_TOKENS)
print("설정:", caller.settings())   # 키는 출력하지 않습니다'''),
        md("## 5. 소량 시험(기본)\n시험 문장 2개만 보냅니다. **`CONFIRM_SEND`는 기본값이 `False`라서, 직접 `True`로 바꾸기 전에는 아무것도 전송되지 않습니다.** 성공하면 전체 실행과 똑같이 정식 저장 → 다시 읽기 → 검증 → 부분 화면까지 확인합니다. 이 결과의 성공은 연결이 작동한다는 뜻이지 분석 정확도의 검증이 아닙니다."),
        code(r'''import time
CONFIRM_SEND = False   # 문장 원문을 API로 보내는 데 동의하면 직접 True로 바꾸세요(기본값 False)
ids = [i for d, i in rv.SMOKE]
print("예상:", API.estimate(A, ids, CHUNK_SIZE))
if not CONFIRM_SEND:
    raise SystemExit("전송하지 않았습니다. CONFIRM_SEND = True로 바꾼 뒤 이 칸을 다시 실행하세요.")
core, whole, f, ex = API.analyze(A, caller, RUN_ROOT, sentence_ids=ids, chunk_size=CHUNK_SIZE, max_retries=MAX_RETRIES)
ok_ids = [i for i in ids if i not in set(f["processing"]["failed_ids"])]
rec = rv.base_record(A, "api", f["run_id"], ["core_v1.3", "whole_paper_hits_0.1"], run_kind="smoke", **{k: v for k, v in f.items() if k != "run_id"})
SMOKE_RUN = f["run_id"]
SMOKE_DIR = rv.save_validated_run(RUN_ROOT, A, SMOKE_RUN, rec, core, whole, extra=ex, expected_ids=ok_ids)   # 정식 저장(검증 실패 시 저장하지 않음)
r = rv.load_run(RUN_ROOT, "paper_a", SMOKE_RUN)                                    # 다시 읽기(해시 확인)
for c in r["core"]: print(c)
print("표현:", [(h["sentence_id"], h["text"], h["role"]) for h in r["whole"]])
print("처리:", r["record"]["processing"], "| 사용량:", r["record"]["usage_total"])
print("다시 읽은 결과 검사 — core:", rv.validate_core(r["core"], A, ok_ids) or "통과", "| whole:", rv.validate_whole(r["whole"], A) or "통과",
      "| 위치를 찾지 못한 표현:", len(ex["invalid_hits"]))
SMOKE_VIEW = rv.build_viewer([r], [A], f"viewer_api_smoke_{time.strftime('%Y%m%d-%H%M%S')}.html")
print("저장:", SMOKE_DIR, "| 부분 화면:", SMOKE_VIEW)
try:
    from google.colab import files
    from IPython.display import HTML, display
    display(HTML(open(SMOKE_VIEW, encoding="utf-8").read()))
except ImportError:
    pass'''),
        md("## 6. 전체 실행(선택)\n`FULL_RUN=True`이고 `CONFIRM_SEND=True`일 때만 실행됩니다. 실행을 시작하면 논문마다 `새 실행 ID`가 출력되니 적어 두세요. 중간에 끊기면 `RESUME={'paper_a': '실행ID', 'paper_b': '실행ID'}`에 **두 논문의 실행 ID를 모두** 넣고 다시 실행하세요. 이미 저장까지 끝난 논문은 다시 부르지 않고 저장된 결과를 그대로 쓰며, 끊긴 논문만 이어서 실행합니다. `RESUME`에 넣은 ID를 찾지 못하면(오타 등) 새 실행을 시작하지 않고 멈춥니다. 재개할 때는 입력 파일 해시·문장 목록·모델·max_tokens·묶음 크기·프롬프트가 처음 실행과 같은지 먼저 확인하고, 하나라도 다르면 멈춥니다. 끝난 묶음의 캐시도 다시 검증합니다."),
        code(r'''FULL_RUN = False
RESUME = {}          # 예: {"paper_a": "20261019-101500-api-1a2b3c"}
RUNS = {}
if FULL_RUN and not CONFIRM_SEND:
    raise SystemExit("CONFIRM_SEND가 False라 전송하지 않았습니다.")
if not FULL_RUN:
    print("전체 실행을 건너뜁니다(FULL_RUN=False). 예상:", {D.document_id: API.estimate(D, [s.id for s in D.sentences], CHUNK_SIZE) for D in (A, B)})
else:
    for D in (A, B):
        if API.is_saved(RUN_ROOT, D, RESUME.get(D.document_id)):   # 이미 저장까지 끝난 논문은 다시 부르지 않는다
            RUNS[D.document_id] = RESUME[D.document_id]
            print(D.document_id, "이미 저장이 끝난 실행이라 다시 부르지 않습니다:", RESUME[D.document_id]); continue
        core, whole, f, ex = API.analyze(D, caller, RUN_ROOT, run_id=RESUME.get(D.document_id), chunk_size=CHUNK_SIZE, max_retries=MAX_RETRIES)
        ok_ids = [s.id for s in D.sentences if s.id not in set(f["processing"]["failed_ids"])]
        rec = rv.base_record(D, "api", f["run_id"], ["core_v1.3", "whole_paper_hits_0.1"], **{k: v for k, v in f.items() if k != "run_id"})
        d = rv.save_validated_run(RUN_ROOT, D, f["run_id"], rec, core, whole, extra=ex, expected_ids=ok_ids)   # 검증 실패 시 저장하지 않음
        RUNS[D.document_id] = f["run_id"]
        print(D.document_id, "저장:", d, "| 처리:", f["processing"]["succeeded"], "성공 /", f["processing"]["failed"], "실패 | 사용량:", f["usage_total"])'''),
        md("## 7. 다시 읽기·일치도·집계\n저장 후 해시를 확인하고 다시 검사합니다. 초안 주석과의 비교는 일치도입니다."),
        code(r'''for D in (A, B):
    if D.document_id not in RUNS: print(D.document_id, "저장된 API 실행 없음"); continue
    r = rv.load_run(RUN_ROOT, D.document_id, RUNS[D.document_id])
    failed = r["record"]["processing"]["failed_ids"]
    print(D.document_id, "| core:", rv.validate_core(r["core"], D, [s.id for s in D.sentences if s.id not in set(failed)]) or "통과",
          "| whole:", rv.validate_whole(r["whole"], D) or "통과", "| 실패 문장:", len(failed))
    ag = rv.agreement_with_annotations(r["core"], D, "독립 분석(API)")
    if ag: print("  ", ag["label"], ag["counts"], "불일치 후보", len(ag["disagreement_candidates"]))'''),
        md("## 8. 화면 연결\nAPI 실행 결과로 화면을 만듭니다. 화면 맨 위에 어떤 엔진·실행·모델로 만든 결과인지 표시됩니다."),
        code(r'''import time
if len(RUNS) == 2:
    out = f"viewer_api_{time.strftime('%Y%m%d-%H%M%S')}.html"
    rv.build_viewer([rv.load_run(RUN_ROOT, "paper_a", RUNS["paper_a"]), rv.load_run(RUN_ROOT, "paper_b", RUNS["paper_b"])], [A, B], out)
    print("화면 파일:", out)
    try:
        from google.colab import files
        from IPython.display import HTML, display
        display(HTML(open(out, encoding="utf-8").read())); files.download(out)
    except ImportError:
        pass
else:
    print("두 논문의 전체 API 실행이 있어야 화면을 만듭니다.")'''),
        md("## 9. 결과 내려받기"),
        code(r'''import shutil
z = shutil.make_archive(f"rv_runs_api_{time.strftime('%Y%m%d-%H%M%S')}", "zip", RUN_ROOT)
print("내려받을 파일:", z)
try:
    from google.colab import files; files.download(z)
except ImportError:
    pass'''),
    ]
    nb.metadata["kernelspec"] = dict(name="python3", display_name="Python 3", language="python")
    return nb

nbf.write(local_nb(), "01_보고동사로다시읽기_로컬분석_API없음.ipynb")
nbf.write(api_nb(), "02_보고동사로다시읽기_API분석_Claude.ipynb")
for f in ["01_보고동사로다시읽기_로컬분석_API없음.ipynb", "02_보고동사로다시읽기_API분석_Claude.ipynb"]:
    nbf.validate(nbf.read(f, as_version=4)); print("valid", f)
