# [시험용 대체] 실제 API 대신 가짜 호출기. 네트워크 호출 없음. 두 번째 호출은 일부러 형식 오류를 냅니다.
import engine_api as API, json as _j
class FakeCaller:
    model="FAKE-no-network"; calls=0
    def settings(self): return dict(provider="fake", model=self.model)
    def __call__(self, system, user):
        FakeCaller.calls+=1
        p=_j.loads(user); D={"paper_a":A,"paper_b":B}[p["document_id"]]; m=D.by_id(); out=[]
        if FakeCaller.calls==2: return "형식이 틀린 응답", dict(usage={})
        for x in p["sentences"]:
            i=x["sentence_id"]; s=m[i].text; nums=rv.citation_numbers(s); a=D.annotations[i]
            v=a.get("reporting_verb","") if nums else ""
            out.append(dict(sentence_id=i,has_citation=bool(nums),citation_numbers=nums,reporting_verb=v,citation_form=a.get("citation_form","") if nums else "",note="",
                            hits=[dict(text=t,occurrence=1,role="prior",attr="선행연구",agent="선행연구") for t in v.split(", ") if t]))
        return _j.dumps(dict(results=out),ensure_ascii=False), dict(usage=dict(input_tokens=10,output_tokens=10))
CHUNK_SIZE, MAX_RETRIES = 20, 3
caller=FakeCaller(); print("가짜 호출기 사용:", caller.settings())