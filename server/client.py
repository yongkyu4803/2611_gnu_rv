"""클라이언트 화면: viewer_template.html을 그대로 쓰고, 자료만 서버(/viewer-data)에서 받아 온다.

화면의 모양·동작 코드는 템플릿 한 곳에만 있다. 여기서는 템플릿 스크립트를
  const DATA=__DATA__;  …원래 코드…
에서
  (async()=>{ const DATA=await rvLoad(); …원래 코드… })();
로 감싸 자료를 받은 뒤 원래 코드가 그대로 돌게 할 뿐이다(템플릿을 고치면 클라이언트도 같이 바뀐다).
"""
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(HERE, "viewer_template.html")
MARK = "<script>\nconst DATA=__DATA__;\n"

LOADER = r"""<script>
(async()=>{
const RV_DOCS=['paper_a','paper_b'];
async function rvLoad(){
  const q=new URLSearchParams(location.search),p=new URLSearchParams();
  for(const k of RV_DOCS){if(q.get(k))p.set(k,q.get(k))}
  const r=await fetch('viewer-data'+(p.toString()?'?'+p:''),{headers:{Accept:'application/json'}});
  if(!r.ok){const e=await r.json().catch(()=>({}));throw Object.assign(new Error(e.detail||r.statusText),{status:r.status})}
  return r.json();
}
function rvFail(err){
  const e=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  document.getElementById('t-b').hidden=true;document.getElementById('t-c').hidden=true;
  document.getElementById('runinfo').textContent='';
  const none=err.status===404&&!location.search;
  document.getElementById('v-a').innerHTML=`<div class="panel"><h3>${none?'아직 저장된 분석 결과가 없습니다':'화면 자료를 불러오지 못했습니다'}</h3>
    <p class="hint">${e(err.message)}</p>
    ${none?'<p class="hint">로컬 규칙 엔진(spaCy, 외부 API 없음)으로 두 논문을 분석해 저장한 뒤 화면을 엽니다. 1분 안팎 걸립니다.</p><button class="btn" data-rv-run>로컬 분석 실행(논문 A·B)</button> <span class="hint" data-rv-msg></span>':''}</div>`;
  const b=document.querySelector('[data-rv-run]');
  if(b)b.onclick=async()=>{b.disabled=true;const m=document.querySelector('[data-rv-msg]');
    try{for(const d of RV_DOCS){m.textContent=d+' 분석 중…';const r=await fetch('runs/local',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({document_id:d})});
        if(!r.ok){const x=await r.json().catch(()=>({}));throw new Error(x.detail||r.statusText)}}
      location.reload()}catch(x){m.textContent='실패: '+x.message;b.disabled=false}};
}
document.getElementById('runinfo').textContent='분석 결과를 불러오는 중…';
let DATA;
try{DATA=await rvLoad()}catch(err){rvFail(err);return}
"""


def client_html():
    t = open(TEMPLATE, encoding="utf-8").read()
    if t.count(MARK) != 1 or not t.rstrip().endswith("</script>\n</body>\n</html>".rstrip()):
        raise RuntimeError("viewer_template.html의 스크립트 구조가 예상과 달라 클라이언트 화면을 만들 수 없습니다")
    t = t.replace(MARK, LOADER)
    i = t.rindex("</script>")
    return t[:i] + "})();\n" + t[i:]
