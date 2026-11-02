"""
보고동사로 다시 읽기 — FastAPI 서버

기존 모듈(rvtool, engine_local)을 그대로 감싼다. 외부 AI API(engine_api)는 비용이 들어 여기서 부르지 않는다.
실행: uvicorn server.main:app --reload   (프로젝트 루트에서)
"""
from __future__ import annotations
import os, sys, tempfile
from functools import lru_cache
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import rvtool as rv            # noqa: E402
import engine_local as L       # noqa: E402
from server.client import client_html   # noqa: E402

DOC_VERSION = os.environ.get("RV_DOC_VERSION", "preproc-v1.2-xml-20261015")
RUN_ROOT = os.environ.get("RV_RUN_ROOT", os.path.join(ROOT, "rv_runs"))
DOC_IDS = ("paper_a", "paper_b")
READONLY = os.environ.get("RV_READONLY") == "1"   # 공개 배포용: 새 실행 저장을 막는다(결과는 배포 때 미리 만든다)
MAX_SENTENCE_CHARS = 2000

app = FastAPI(title="보고동사로 다시 읽기", version=rv.TOOL_VERSION)


@lru_cache(maxsize=None)
def get_doc(document_id: str) -> rv.Document:
    if document_id not in DOC_IDS:
        raise HTTPException(404, f"알 수 없는 문서: {document_id}")
    ann = os.path.join(ROOT, "annotations", f"{document_id}_draft_v1.3.csv")
    return rv.load_document(os.path.join(ROOT, "inputs", f"{document_id}_input.txt"),
                            os.path.join(ROOT, "inputs", f"{document_id}_structure.tsv"), document_id,
                            ann if os.path.exists(ann) else None, document_version=DOC_VERSION)


class LocalRunRequest(BaseModel):
    document_id: str
    sentence_ids: Optional[list[str]] = None   # 없으면 전체 문장
    use_annotations: bool = False


class SentenceRequest(BaseModel):
    text: str


@app.get("/health")
def health():
    return dict(status="ok", tool_version=rv.TOOL_VERSION, rule_version=L.RULE_VERSION, readonly=READONLY)


@app.get("/documents")
def documents():
    return [dict(rv.describe(get_doc(d)), preprocessing_record=rv.check_preprocessing_record(get_doc(d))) for d in DOC_IDS]


@app.get("/documents/{document_id}/sentences")
def sentences(document_id: str):
    return [s.__dict__ for s in get_doc(document_id).sentences]


@app.post("/analyze/sentence")
def analyze_sentence(req: SentenceRequest):
    """임의의 영어 문장 하나를 로컬 규칙으로 분석한다(저장하지 않음)."""
    if not req.text.strip():
        raise HTTPException(422, "빈 문장입니다")
    if len(req.text) > MAX_SENTENCE_CHARS:
        raise HTTPException(422, f"문장이 너무 깁니다({MAX_SENTENCE_CHARS}자 이하)")
    s = rv.Sentence("0-001", 1, req.text, "", "", "", "", 1, len(req.text.split()))
    core, hits, excluded = L.analyze_sentence("adhoc", s, "en_core_web_sm")
    return dict(core=core, hits=hits, excluded=excluded)


@app.post("/runs/local", status_code=201)
def run_local(req: LocalRunRequest):
    """로컬 엔진으로 분석하고, 검증을 통과할 때만 새 실행 폴더에 저장한다."""
    if READONLY:
        raise HTTPException(403, "이 서버는 읽기 전용입니다. 분석 결과는 배포할 때 미리 만들어 두었습니다.")
    doc = get_doc(req.document_id)
    try:
        core, whole, excl, fields = L.analyze(doc, sentence_ids=req.sentence_ids, use_annotations=req.use_annotations)
    except rv.InputError as e:
        raise HTTPException(422, str(e))
    run_id = rv.new_run_id("local")
    kind = "partial" if req.sentence_ids else "full"
    rec = rv.base_record(doc, "local", run_id, ["core_v1.3", "whole_paper_hits_0.1"], run_kind=kind, **fields)
    try:
        d = rv.save_validated_run(RUN_ROOT, doc, run_id, rec, core, whole,
                                  extra=dict(excluded=excl), expected_ids=req.sentence_ids)
    except rv.ValidationFailed as e:
        raise HTTPException(500, str(e))
    return dict(run_id=run_id, run_dir=d, hits=len(whole), excluded=len(excl))


@app.get("/runs")
def runs(document_id: Optional[str] = None):
    return rv.list_runs(RUN_ROOT, document_id)


def _load(document_id: str, run_id: str):
    get_doc(document_id)
    if os.sep in run_id or run_id in ("", ".", ".."):
        raise HTTPException(400, "잘못된 실행 ID")
    try:
        return rv.load_run(RUN_ROOT, document_id, run_id)
    except FileNotFoundError:
        raise HTTPException(404, f"실행이 없습니다: {document_id}/{run_id}")
    except ValueError as e:   # 저장 후 바뀐 파일
        raise HTTPException(409, str(e))


@app.get("/runs/{document_id}/{run_id}")
def get_run(document_id: str, run_id: str):
    return _load(document_id, run_id)


@app.get("/runs/{document_id}/{run_id}/agreement")
def agreement(document_id: str, run_id: str):
    r = _load(document_id, run_id)
    if r["record"].get("use_annotations"):
        raise HTTPException(400, "주석 재사용 모드 결과는 같은 CSV와 비교하지 않습니다")
    ag = rv.agreement_with_annotations(r["core"], get_doc(document_id), "독립 분석")
    if ag is None:
        raise HTTPException(404, "초안 주석 CSV가 없습니다")
    return ag


def _latest_full(document_id: str) -> Optional[str]:
    """그 문서의 가장 최근 전체 실행(부분·소량 시험 제외). 없으면 None."""
    full = [r for r in rv.list_runs(RUN_ROOT, document_id) if r["run_kind"] == "full"]
    return max(full, key=lambda r: r["saved_at"] or "")["run_id"] if full else None


@app.get("/viewer-data")
def viewer_data(paper_a: Optional[str] = Query(None), paper_b: Optional[str] = Query(None)):
    """클라이언트 화면용 자료(JSON). 실행 ID를 주지 않으면 두 논문 각각의 가장 최근 전체 실행을 쓴다."""
    if not (paper_a or paper_b):
        paper_a, paper_b = _latest_full("paper_a"), _latest_full("paper_b")
        if not (paper_a or paper_b):
            raise HTTPException(404, "저장된 전체 실행이 없습니다. POST /runs/local로 먼저 분석하세요.")
    pairs = [(d, rid) for d, rid in (("paper_a", paper_a), ("paper_b", paper_b)) if rid]
    return rv.viewer_data([_load(d, rid) for d, rid in pairs], [get_doc(d) for d, _ in pairs])


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/app")


@app.get("/app", response_class=HTMLResponse)
def client_app():
    """클라이언트 화면. ?paper_a=<run_id>&paper_b=<run_id>로 실행을 고를 수 있다(없으면 가장 최근 전체 실행)."""
    return HTMLResponse(client_html())


@app.get("/viewer", response_class=HTMLResponse)
def viewer(paper_a: Optional[str] = Query(None), paper_b: Optional[str] = Query(None)):
    """저장된 실행으로 화면 HTML을 만든다. ?paper_a=<run_id>&paper_b=<run_id> (하나 또는 둘)."""
    pairs = [(d, rid) for d, rid in (("paper_a", paper_a), ("paper_b", paper_b)) if rid]
    if not pairs:
        raise HTTPException(400, "paper_a 또는 paper_b 실행 ID를 주세요")
    runs_, docs = [_load(d, rid) for d, rid in pairs], [get_doc(d) for d, _ in pairs]
    with tempfile.TemporaryDirectory() as t:
        out = rv.build_viewer(runs_, docs, os.path.join(t, "viewer.html"))
        return HTMLResponse(open(out, encoding="utf-8").read())
