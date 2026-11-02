"""노트북 시험: 로컬 Jupyter 커널(nbclient)에서 실행한다. 구글 코랩이 아니며, 실제 API도 부르지 않는다.
② 노트북은 'API 설정' 칸을 가짜 호출기(tests/fake_caller_cell.py)로 바꿔 실행한다. 설치 칸은 건너뛴다."""
import os, sys, json, shutil, glob, tempfile
import nbformat, nbclient
from nbclient.exceptions import CellExecutionError
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
NB1 = glob.glob(os.path.join(ROOT, "01_*.ipynb"))[0]; NB2 = glob.glob(os.path.join(ROOT, "02_*.ipynb"))[0]
FAKE = open(os.path.join(HERE, "fake_caller_cell.py"), encoding="utf-8").read()
ZIP_FOR_TEST = os.environ.get("RV_ZIP", "/mnt/user-data/outputs/rv_colab.zip")
log = []
def check(name, cond, detail=""):
    log.append(dict(test=name, passed=bool(cond), detail=str(detail)[:400])); print(("통과" if cond else "실패"), name, "" if cond else detail)
def workdir():
    d = tempfile.mkdtemp(prefix="nbtest_")
    for p in ["rvtool.py", "engine_local.py", "engine_api.py", "viewer_template.html", "schemas", "inputs", "annotations"]:
        src = os.path.join(ROOT, p); (shutil.copytree if os.path.isdir(src) else shutil.copy)(src, os.path.join(d, p))
    return d
def run(path, d, edits=()):
    nb = nbformat.read(path, as_version=4)
    for c in nb.cells:
        if c.cell_type != "code": continue
        if c.source.startswith("!pip"): c.source = 'print("설치 칸 생략(시험 환경)")'
        for cond, fn in edits:
            if cond in c.source: c.source = fn(c.source)
    err = None
    try: nbclient.NotebookClient(nb, timeout=600, kernel_name="python3", resources={"metadata": {"path": d}}).execute()
    except CellExecutionError as e: err = str(e)
    return nb, err
def runs(d, pat): return [p for p in glob.glob(os.path.join(d, "rv_runs", "*", pat)) if os.path.isdir(p)]

# 1) 로컬 노트북 전체
d1 = workdir(); nb, err = run(NB1, d1)
check("노트북①: 모든 칸 오류 없이 실행", err is None, err)
sm = [p for p in runs(d1, "*-local-smoke-*") if os.path.exists(os.path.join(p, "run.json"))]
check("노트북①: 소량 시험 정식 저장(run.json) 생성", len(sm) == 1 and json.load(open(os.path.join(sm[0], "run.json")))["run_kind"] == "smoke")
check("노트북①: 소량 시험 부분 화면 파일 생성", len(glob.glob(os.path.join(d1, "viewer_local_smoke_*.html"))) == 1)
check("노트북①: 전체 화면 파일 생성", len(glob.glob(os.path.join(d1, "viewer_local_2*.html"))) == 1)
nbformat.write(nb, os.path.join(HERE, "01_executed_here.ipynb"))

# 2) API 노트북, CONFIRM_SEND 기본값(False) 그대로 → 소량 시험 칸에서 멈추고 전송 없음
d2 = workdir(); nb, err = run(NB2, d2, [('MODEL = "claude', lambda s: FAKE)])
check("노트북②: CONFIRM_SEND 기본값이 False", "CONFIRM_SEND = False" in open(NB2, encoding="utf-8").read())
check("노트북②: 기본값으로는 소량 시험 칸에서 멈춤", err is not None and "CONFIRM_SEND" in err, (err or "")[:200])
check("노트북②: 기본값으로는 호출·작업 폴더 없음", runs(d2, "*-api-*") == [])
nbformat.write(nb, os.path.join(HERE, "02_executed_confirm_false.ipynb"))

# 3) API 노트북, 전송 동의 + 전체 실행(가짜 호출기)
d3 = workdir()
nb, err = run(NB2, d3, [('MODEL = "claude', lambda s: FAKE), ("CONFIRM_SEND = False", lambda s: s.replace("CONFIRM_SEND = False", "CONFIRM_SEND = True")),
                        ("FULL_RUN = False", lambda s: s.replace("FULL_RUN = False", "FULL_RUN = True"))])
check("노트북②(가짜 호출): 모든 칸 오류 없이 실행", err is None, err)
saved = [p for p in runs(d3, "*-api-*") if os.path.exists(os.path.join(p, "run.json"))]
kinds = sorted(json.load(open(os.path.join(p, "run.json"))).get("run_kind", "full") for p in saved)
check("노트북②(가짜 호출): 소량 시험 1건 + 전체 2건 정식 저장", kinds == ["full", "full", "smoke"], kinds)
check("노트북②(가짜 호출): 소량 시험 부분 화면 생성", len(glob.glob(os.path.join(d3, "viewer_api_smoke_*.html"))) == 1)
check("노트북②(가짜 호출): 전체 화면 생성", len(glob.glob(os.path.join(d3, "viewer_api_2*.html"))) == 1)
nbformat.write(nb, os.path.join(HERE, "02_executed_with_fake_caller.ipynb"))

# 3-b) 학생 실습 노트북(외부 AI 없음)
NB3 = glob.glob(os.path.join(ROOT, "보고동사로다시읽기_학생실습.ipynb"))[0]
d4 = workdir(); nb, err = run(NB3, d4)
check("학생 노트북: 모든 칸 오류 없이 실행", err is None, err)
src = "".join(c.source for c in nbformat.read(NB3, as_version=4).cells if c.cell_type == "code")
check("학생 노트북: API·키 관련 코드 없음", not any(k in src for k in ("engine_api", "ANTHROPIC", "getpass", "userdata")))
check("학생 노트북: 화면 파일 생성", len(glob.glob(os.path.join(d4, "보고동사로다시읽기_화면_*.html"))) == 1)
nbformat.write(nb, os.path.join(HERE, "student_executed_here.ipynb"))

# 3-c) 연구자 사전 실습 노트북(외부 AI 없음) + 검토 메모 기록
NB4 = glob.glob(os.path.join(ROOT, "보고동사로다시읽기_연구자사전실습.ipynb"))[0]
d5 = workdir(); nb, err = run(NB4, d5, [('memo_id       = ""', lambda s: s.replace('memo_id       = ""', 'memo_id       = "3.3.2-020"').replace('memo_reviewer = ""', 'memo_reviewer = "시험"').replace('memo_opinion  = ""', 'memo_opinion  = "시험 기록"'))])
check("연구자 노트북: 모든 칸 오류 없이 실행", err is None, err)
outs = "".join(o.get("text", "") for c in nb.cells if c.cell_type == "code" for o in c.outputs if o.get("output_type") == "stream")
check("연구자 노트북: 실습 1 기대값과 실제 출력 '일치'", "주어 = 선행연구 → 일치" in outs)
check("연구자 노트북: 전처리 기록 대조가 모두 일치로 출력", outs.count("일치") >= 6 and "불일치" not in outs.split("전처리 기록과 비교")[1][:400])
src4 = "".join(c.source for c in nbformat.read(NB4, as_version=4).cells if c.cell_type == "code")   # 설명문 말고 코드 셀만 검사
check("연구자 노트북: API·키 관련 코드 없음", not any(k in src4 for k in ("engine_api", "ANTHROPIC", "getpass", "userdata")))
memo = os.path.join(d5, "검토메모.csv")
check("연구자 노트북: 검토 메모 1건 기록", os.path.exists(memo) and sum(1 for _ in open(memo, encoding="utf-8-sig")) == 2)
import csv as _csv
rows_ = list(_csv.reader(open(memo, encoding="utf-8-sig")))
check("연구자 노트북: 메모에 문서 판본·실행 ID 포함", rows_[0][2:4] == ["문서 판본", "실행 ID"] and "research-practice" in rows_[1][3], rows_[:2])
saved_ = [p for p in glob.glob(os.path.join(d5, "rv_runs", "*", "*research-practice*"))]
check("연구자 노트북: 검증 통과 기록과 제외 후보 파일 저장", len(saved_) == 2 and all(os.path.exists(os.path.join(p, "excluded.json")) and json.load(open(os.path.join(p, "run.json")))["validation"]["core"] == "통과" for p in saved_))
# 메모를 비워 둔 채 실행하면 기록하지 않고 멈춤
d6 = workdir(); nb6, err6 = run(NB4, d6)
check("연구자 노트북: 메모 칸을 모두 비우면 기록 없이 끝까지 실행(모두 실행 가능)", err6 is None and not os.path.exists(os.path.join(d6, "검토메모.csv")), err6)
d6b = workdir(); nb6b, err6b = run(NB4, d6b, [('memo_id       = ""', lambda s: s.replace('memo_id       = ""', 'memo_id       = "3.3.2-020"'))])
check("연구자 노트북: 메모 칸을 일부만 채우면 기록 없이 멈춤", err6b is not None and "memo_reviewer" in err6b and not os.path.exists(os.path.join(d6b, "검토메모.csv")))
# 필수 파일이 없으면 자료 올리기 셀에서 바로 멈춤
d7 = tempfile.mkdtemp(prefix="nbtest_empty_"); nb7, err7 = run(NB4, d7)
check("연구자 노트북: 필수 파일이 없으면 자료 올리기 셀에서 멈춤", err7 is not None and "FileNotFoundError" in err7 and "필수 파일이 없습니다" in err7)
# ZIP 하나만 있는 빈 폴더에서 시작
d8 = tempfile.mkdtemp(prefix="nbtest_zip_"); shutil.copy(ZIP_FOR_TEST, os.path.join(d8, "rv_colab.zip"))
nb8, err8 = run(NB4, d8, [('memo_id       = ""', lambda s: s.replace('memo_id       = ""', 'memo_id       = "1-001"').replace('memo_reviewer = ""', 'memo_reviewer = "시험"').replace('memo_opinion  = ""', 'memo_opinion  = "시험"'))])
check("연구자 노트북: rv_colab.zip만 있는 폴더에서 끝까지 실행", err8 is None, err8)
# 이전 실습 파일이 남아 있는 폴더에, 필수 파일 하나가 빠진 새 ZIP을 올린 경우 → 복사하지 않고 멈춤
import zipfile as _zf
d9 = workdir(); bad_zip = os.path.join(d9, "rv_colab.zip")
with _zf.ZipFile(ZIP_FOR_TEST) as zin, _zf.ZipFile(bad_zip, "w") as zout:
    for n in zin.namelist():
        if not n.endswith("inputs/paper_b_structure.tsv"): zout.writestr(n, zin.read(n))
before = open(os.path.join(d9, "inputs", "paper_b_structure.tsv"), "rb").read()
nb9, err9 = run(NB4, d9)
check("연구자 노트북: 새 ZIP에 필수 파일이 빠지면(옛 파일이 있어도) 복사 없이 멈춤",
      err9 is not None and "올린 ZIP에 필수 파일이 없습니다" in err9 and open(os.path.join(d9, "inputs", "paper_b_structure.tsv"), "rb").read() == before, (err9 or "")[:200])
# 오래된 공통 모듈과 섞이면 멈춤
d10 = workdir(); src_ = open(os.path.join(d10, "rvtool.py"), encoding="utf-8").read().replace("def save_validated_run(", "def _removed_save_validated_run(")
open(os.path.join(d10, "rvtool.py"), "w", encoding="utf-8").write(src_)
nb10, err10 = run(NB4, d10)
check("연구자 노트북: 오래된 공통 모듈이면 판본 안내와 함께 멈춤", err10 is not None and "공통 모듈 판본이 이 노트북보다 오래되었습니다" in err10)
nbformat.write(nb, os.path.join(HERE, "researcher_executed_here.ipynb"))


# 3-d) (2026-11-02) 노트북 ①·②의 ZIP 처리: 이전 파일이 남은 폴더에 새 ZIP을 올리면 새 파일을 씀
d11 = workdir(); shutil.copy(ZIP_FOR_TEST, os.path.join(d11, "rv_colab.zip"))
old_ = open(os.path.join(d11, "rvtool.py"), encoding="utf-8").read().replace('TOOL_VERSION = "', 'TOOL_VERSION = "OLD-')
open(os.path.join(d11, "rvtool.py"), "w", encoding="utf-8").write(old_)
nb11, err11 = run(NB1, d11)
outs11 = "".join(o.get("text", "") for c in nb11.cells if c.cell_type == "code" for o in c.outputs if o.get("output_type") == "stream")
check("노트북①: 옛 파일이 남은 폴더에 새 ZIP을 올리면 새 공통 모듈을 씀", err11 is None and "공통 모듈: rvtool-" in outs11 and "OLD-" not in outs11, (err11 or outs11[:300]))
d12 = workdir(); bad12 = os.path.join(d12, "rv_colab.zip")
with _zf.ZipFile(ZIP_FOR_TEST) as zin, _zf.ZipFile(bad12, "w") as zout:
    for n in zin.namelist():
        if not n.endswith("engine_api.py"): zout.writestr(n, zin.read(n))
before12 = open(os.path.join(d12, "rvtool.py"), "rb").read()
open(os.path.join(d12, "rvtool.py"), "ab").write(b"\n# old\n"); before12 = open(os.path.join(d12, "rvtool.py"), "rb").read()
nb12, err12 = run(NB2, d12)
check("노트북②: 새 ZIP에 필수 파일이 빠지면 복사 없이 멈춤", err12 is not None and "올린 ZIP에 필수 파일이 없습니다" in err12 and open(os.path.join(d12, "rvtool.py"), "rb").read() == before12, (err12 or "")[:200])
# 3-e) (2026-11-02) 노트북② 재개: A는 저장까지 끝났고 B는 중간에 끊긴 상태 → A는 다시 부르지 않고 B만 이어서 실행
sys.path.insert(0, ROOT); import rvtool as _rv, engine_api as _API
d13 = workdir()
def _doc(d): return _rv.load_document(f"{d13}/inputs/{d}_input.txt", f"{d13}/inputs/{d}_structure.tsv", d, f"{d13}/annotations/{d}_draft_v1.3.csv", document_version="preproc-v1.2-xml-20261015")
A13, B13 = _doc("paper_a"), _doc("paper_b")
class _Prep:
    model = "FAKE-no-network"
    def __init__(self, fail_after=None): self.calls, self.fail_after = 0, fail_after
    def settings(self): return dict(provider="fake", model=self.model)
    def __call__(self, system, user):
        self.calls += 1
        if self.fail_after is not None and self.calls > self.fail_after: raise TimeoutError("끊김(시험)")
        p_ = json.loads(user); D_ = {"paper_a": A13, "paper_b": B13}[p_["document_id"]]; m_ = D_.by_id(); out = []
        for x in p_["sentences"]:
            nums = _rv.citation_numbers(m_[x["sentence_id"]].text)
            out.append(dict(sentence_id=x["sentence_id"], has_citation=bool(nums), citation_numbers=nums, reporting_verb="", citation_form="non_integral" if nums else "", note="", hits=[]))
        return json.dumps(dict(results=out)), dict(usage={})
RR = os.path.join(d13, "rv_runs")
ca, wa, fa, xa = _API.analyze(A13, _Prep(), RR, sleep=0, log=lambda *a: None)
_rv.save_run(RR, A13, fa["run_id"], _rv.base_record(A13, "api", fa["run_id"], ["core_v1.3"], **{k: v for k, v in fa.items() if k != "run_id"}), ca, wa)
_, _, fb, _ = _API.analyze(B13, _Prep(fail_after=3), RR, max_retries=1, sleep=0, log=lambda *a: None)   # B: 3묶음 뒤 끊김(저장 안 함)
resume_src = f'RESUME = {{"paper_a": "{fa["run_id"]}", "paper_b": "{fb["run_id"]}"}}'
nb13, err13 = run(NB2, d13, [('MODEL = "claude', lambda s: FAKE), ("CONFIRM_SEND = False", lambda s: s.replace("CONFIRM_SEND = False", "CONFIRM_SEND = True")),
                             ("FULL_RUN = False", lambda s: s.replace("FULL_RUN = False", "FULL_RUN = True").replace("RESUME = {}", resume_src))])
outs13 = "".join(o.get("text", "") for c in nb13.cells if c.cell_type == "code" for o in c.outputs if o.get("output_type") == "stream")
a_full = [p for p in runs(d13, "*-api-*") if os.sep + "paper_a" + os.sep in p and json.load(open(os.path.join(p, "run.json"))).get("run_kind", "full") == "full"]
check("노트북② 재개: 저장된 A는 다시 부르지 않고 끊긴 B만 이어서 저장, 화면 생성",
      err13 is None and "이미 저장이 끝난 실행이라 다시 부르지 않습니다" in outs13 and len(a_full) == 1 and _API.is_saved(RR, B13, fb["run_id"])
      and len(glob.glob(os.path.join(d13, "viewer_api_2*.html"))) == 1, (err13 or outs13[-400:]))
d14 = workdir()
nb14, err14 = run(NB2, d14, [('MODEL = "claude', lambda s: FAKE), ("CONFIRM_SEND = False", lambda s: s.replace("CONFIRM_SEND = False", "CONFIRM_SEND = True")),
                             ("FULL_RUN = False", lambda s: s.replace("FULL_RUN = False", "FULL_RUN = True").replace("RESUME = {}", 'RESUME = {"paper_a": "20990101-000000-api-typo00"}'))])
a14 = [p for p in runs(d14, "*-api-*") if os.sep + "paper_a" + os.sep in p]
check("노트북② 재개: RESUME의 실행 ID를 잘못 적으면 새 실행 없이 멈춤(소량 시험 폴더만 있음)",
      err14 is not None and "재개할 실행을 찾지 못했습니다" in err14 and len(a14) == 1 and "smoke" in json.load(open(os.path.join(a14[0], "run.json"))).get("run_kind", ""), (err14 or "")[:200])

# 4) 만든 화면을 브라우저에서 열어 스크립트 오류 확인(가능할 때만)
try:
    import asyncio
    from playwright.async_api import async_playwright
    async def browse(files):
        out = {}
        async with async_playwright() as p:
            b = await p.chromium.launch()
            for f in files:
                pg = await b.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
                await pg.goto("file://" + f); await pg.wait_for_timeout(800)
                out[os.path.basename(f)] = dict(errors=errs, tabs_hidden=await pg.evaluate("[document.getElementById('t-b').hidden, document.getElementById('t-c').hidden]"),
                                                info=await pg.evaluate("document.getElementById('runinfo').textContent"))
            await b.close()
        return out
    views = [f for d in (d1, d3) for f in glob.glob(os.path.join(d, "viewer_*.html")) if not f.endswith("viewer_template.html")]
    res = asyncio.run(browse(views))
    check("화면: 생성된 4개 화면 모두 브라우저 스크립트 오류 없음", len(res) == 4 and all(not v["errors"] for v in res.values()), res)
    sm_views = {k: v for k, v in res.items() if "smoke" in k}
    check("화면: 부분 화면은 논문 B·비교 탭을 숨기고 '부분 실행'을 표시", all(v["tabs_hidden"] == [True, True] and "부분 실행" in v["info"] for v in sm_views.values()) and len(sm_views) == 2, sm_views)
except ImportError:
    log.append(dict(test="화면 브라우저 확인", passed=None, detail="playwright 없음: 건너뜀"))
json.dump(dict(environment="로컬 Jupyter 커널(nbclient). 구글 코랩 아님. 실제 API 호출 없음(가짜 호출기).",
               passed=sum(1 for x in log if x["passed"]), total=len(log), tests=log),
          open(os.path.join(HERE, "notebook_test_log.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\n{sum(1 for x in log if x['passed'])}/{len(log)} 통과")
