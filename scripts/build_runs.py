"""배포용: 두 논문을 로컬 엔진으로 분석해 rv_runs/에 저장한다(Render 빌드 단계에서 실행).
검증을 통과한 결과만 저장하며, 이미 같은 규칙 판본의 전체 실행이 있으면 다시 만들지 않는다."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT)
import rvtool as rv, engine_local as L

RUN_ROOT = os.environ.get("RV_RUN_ROOT", os.path.join(ROOT, "rv_runs"))
DOC_VERSION = os.environ.get("RV_DOC_VERSION", "preproc-v1.2-xml-20261015")
for d in ("paper_a", "paper_b"):
    doc = rv.load_document(os.path.join(ROOT, "inputs", f"{d}_input.txt"), os.path.join(ROOT, "inputs", f"{d}_structure.tsv"), d,
                           document_version=DOC_VERSION)
    done = [r for r in rv.list_runs(RUN_ROOT, d) if r["run_kind"] == "full" and r["engine"] == "local"]
    if any(rv.load_run(RUN_ROOT, d, r["run_id"])["record"].get("rule_version") == L.RULE_VERSION for r in done):
        print(d, "이미 같은 규칙 판본의 실행이 있어 건너뜀"); continue
    core, whole, excl, fields = L.analyze(doc)
    rid = rv.new_run_id("deploy")
    rec = rv.base_record(doc, "local", rid, ["core_v1.3", "whole_paper_hits_0.1"], run_kind="full", **fields)
    print(d, "저장:", rv.save_validated_run(RUN_ROOT, doc, rid, rec, core, whole, extra=dict(excluded=excl)), "| 표현", len(whole))
