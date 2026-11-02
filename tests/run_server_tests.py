"""서버 시험(PRD FR-15~20): FastAPI TestClient로 실제 HTTP 서버 없이 부른다. 외부 API 호출 없음.
결과는 tests/server_test_log.json에 남는다. 필요: fastapi, httpx, spaCy + en_core_web_sm."""
import os, sys, json, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, ROOT)
RUN_ROOT = tempfile.mkdtemp(prefix="rv_server_runs_")
os.environ["RV_RUN_ROOT"] = RUN_ROOT          # 서버를 불러오기 전에 정해야 한다
from fastapi.testclient import TestClient
from server.main import app
import engine_local as L
c = TestClient(app)
log = []
def check(name, cond, detail=""):
    log.append(dict(test=name, passed=bool(cond), detail=str(detail)[:300])); print(("통과" if cond else "실패"), name, "" if cond else detail)

# FR-15 상태·문서
r = c.get("/health").json()
check("FR-15 /health: 판본 표시", r["status"] == "ok" and r["rule_version"] == L.RULE_VERSION, r)
docs = c.get("/documents").json()
check("FR-15 /documents: A 249문장·B 215문장", [d["sentences"] for d in docs] == [249, 215], [d.get("sentences") for d in docs])
check("FR-3 /documents: 전처리 기록 대조가 모두 일치", all(x["status"] == "일치" for d in docs for x in d["preprocessing_record"]))
s = c.get("/documents/paper_a/sentences").json()
check("FR-15 문장 목록: ID 순서 그대로", len(s) == 249 and s[0]["order"] == 1 and s[-1]["order"] == 249)
check("FR-15 없는 문서는 404", c.get("/documents/paper_x/sentences").status_code == 404)
# FR-16 즉석 분석(저장하지 않음)
r = c.post("/analyze/sentence", json=dict(text="Chen et al. [32] reported that the yield increased.")).json()
check("FR-16 즉석 분석: reported → 선행연구, 저장 없음", r["core"]["reporting_verb"] == "reported" and r["core"]["citation_form"] == "integral" and not os.listdir(RUN_ROOT), r["core"])
check("FR-16 빈 문장은 422", c.post("/analyze/sentence", json=dict(text="  ")).status_code == 422)
# FR-17 로컬 실행 저장
smoke = ["3.2.3-007", "3.3.1-012"]
r = c.post("/runs/local", json=dict(document_id="paper_a", sentence_ids=smoke))
RID = r.json().get("run_id")
check("FR-17 부분 실행 저장(201)", r.status_code == 201 and os.path.exists(os.path.join(RUN_ROOT, "paper_a", RID, "run.json")), r.text)
rf = c.post("/runs/local", json=dict(document_id="paper_b")); RIDB = rf.json().get("run_id")
check("FR-17 전체 실행 저장", rf.status_code == 201 and rf.json()["hits"] > 0, rf.text)
check("FR-17 없는 문장 ID는 422, 저장 없음", c.post("/runs/local", json=dict(document_id="paper_a", sentence_ids=["9-999"])).status_code == 422
      and len(os.listdir(os.path.join(RUN_ROOT, "paper_a"))) == 1)
ra = c.post("/runs/local", json=dict(document_id="paper_a", use_annotations=True)).json()["run_id"]
# FR-18 실행 목록·다시 읽기·일치도
open(os.path.join(RUN_ROOT, ".DS_Store"), "w").close()   # macOS가 만드는 파일이 있어도 목록이 깨지지 않아야 함
lst = c.get("/runs")
check("FR-18 /runs: 실행 3건(폴더 밖 파일 무시)", lst.status_code == 200 and len(lst.json()) == 3, lst.text[:200])
check("FR-18 /runs?document_id=paper_b: 1건", len(c.get("/runs", params=dict(document_id="paper_b")).json()) == 1)
r = c.get(f"/runs/paper_a/{RID}").json()
check("FR-18 실행 다시 읽기: 연결 시험 문장 결과", {x["sentence_id"]: x for x in r["core"]}["3.2.3-007"]["reporting_verb"] == "reported"
      and {x["sentence_id"]: x for x in r["core"]}["3.3.1-012"]["citation_numbers"] == [40, 41] and r["record"]["validation"]["core"] == "통과")
check("FR-18 없는 실행은 404", c.get("/runs/paper_a/20990101-000000-local-nothere").status_code == 404)
check("FR-18 잘못된 실행 ID('..')는 400", c.get("/runs/paper_a/%2E%2E").status_code == 400)   # 그냥 '..'는 클라이언트가 경로를 접어 버려 서버에 닿지 않는다
ag = c.get(f"/runs/paper_b/{RIDB}/agreement")
check("FR-12·18 일치도: '정확도 아님' 표시와 불일치 후보", ag.status_code == 200 and "정확도가 아님" in ag.json()["label"] and ag.json()["counts"]["sentences"] == 49, ag.text[:200])
check("FR-5·18 주석 재사용 결과는 일치도 계산 거부(400)", c.get(f"/runs/paper_a/{ra}/agreement").status_code == 400)
core_path = os.path.join(RUN_ROOT, "paper_b", RIDB, "core.json"); orig = open(core_path, "rb").read()
open(core_path, "ab").write(b" ")
check("FR-11 저장 후 바뀐 파일은 409", c.get(f"/runs/paper_b/{RIDB}").status_code == 409)
open(core_path, "wb").write(orig)
# FR-19 화면
v = c.get("/viewer", params=dict(paper_a=RID, paper_b=RIDB))
check("FR-19 화면 HTML(두 논문)", v.status_code == 200 and "text/html" in v.headers["content-type"] and "__DATA__" not in v.text and len(v.text) > 100000)
v1 = c.get("/viewer", params=dict(paper_a=RID))
check("FR-14·19 부분 실행 화면: 미분석 표시용 데이터", v1.status_code == 200 and '"partial":true' in v1.text and '"analyzed":2' in v1.text)
check("FR-19 실행 ID 없으면 400", c.get("/viewer").status_code == 400)
# 클라이언트 화면(/app): viewer_template.html을 그대로 쓰고 자료만 /viewer-data에서 받음
from server.client import client_html
tpl = open(os.path.join(ROOT, "viewer_template.html"), encoding="utf-8").read()
app_html = c.get("/app")
check("클라이언트 /app: HTML, 자료 자리표시 없음", app_html.status_code == 200 and "__DATA__" not in app_html.text and "viewer-data" in app_html.text)
style = lambda h: h[h.index("<style>"):h.index("</style>")]; body = lambda h: h[h.index("<body>"):h.index("<script>", h.index("<body>"))]
check("클라이언트 /app: 템플릿과 같은 스타일·본문 구조", style(app_html.text) == style(tpl) and body(app_html.text) == body(tpl))
check("클라이언트 /app: 템플릿의 화면 코드를 고치지 않고 그대로 포함", tpl[tpl.index("const SRC="):tpl.rindex("</script>")] in app_html.text)
check("클라이언트 / → /app", c.get("/", follow_redirects=False).headers.get("location") == "/app")
vd = c.get("/viewer-data").json()
check("/viewer-data: 실행 ID가 없으면 두 논문의 가장 최근 전체 실행", [d["id"] for d in vd] == ["paper_a", "paper_b"] and vd[1]["run"]["run_id"] == RIDB and not vd[0]["run"]["partial"], [d["run"] for d in vd])
vd2 = c.get("/viewer-data", params=dict(paper_a=RID)).json()
check("/viewer-data: 실행 ID를 주면 그 실행(부분 실행 2/249)", len(vd2) == 1 and vd2[0]["run"]["partial"] and vd2[0]["run"]["analyzed"] == 2)
import re as _re
built = c.get("/viewer", params=dict(paper_a=RID)).text
check("/viewer-data와 /viewer(한 파일 화면)의 자료가 같음", json.loads(_re.search(r"const DATA=(.*?);\n", built).group(1).replace("<\\/", "</")) == vd2)
empty = tempfile.mkdtemp(); import server.main as SM; old_root = SM.RUN_ROOT; SM.RUN_ROOT = empty
check("/viewer-data: 저장된 전체 실행이 없으면 404", c.get("/viewer-data").status_code == 404)
SM.RUN_ROOT = old_root
# FR-20 API 엔진은 노출하지 않음
paths = {r.path for r in app.routes}
check("FR-20 API 엔진 경로 없음", not any("api" in p.lower() and p not in ("/openapi.json",) for p in paths) and "engine_api" not in sys.modules, sorted(paths))

json.dump(dict(environment="FastAPI TestClient(로컬). 외부 API 호출 없음.", passed=sum(x["passed"] for x in log), total=len(log), tests=log),
          open(os.path.join(HERE, "server_test_log.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\n{sum(x['passed'] for x in log)}/{len(log)} 통과")
