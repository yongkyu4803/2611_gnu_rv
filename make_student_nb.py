import nbformat as nbf
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
C = []
C.append(md("""# 🗺️ Class Roadmap — 보고동사로 다시 읽기 실습

---
## Step 1 — 구글 코랩 접속 / Open Google Colab
1. 브라우저에서 **[colab.research.google.com](https://colab.research.google.com)** 접속
2. 구글 계정으로 로그인

---
## Step 2 — 노트북 올리기 / Upload the Notebook
1. 코랩 시작 화면에서 **파일 업로드** 탭 클릭
2. 오늘 받은 **`보고동사로다시읽기_학생실습.ipynb`** 파일 선택
3. 파일이 열리면 준비 완료! ✅

---
## Step 3 — 셀 실행 방법 / How to Run a Cell
- 셀을 클릭한 뒤 **`Shift + Enter`** → 실행 후 다음 셀로 이동
- 또는 셀 왼쪽 **▶ 버튼** 클릭
- **위에서부터 순서대로** 실행하세요. 중간을 건너뛰면 오류가 납니다.
  Run the cells **from top to bottom**. Skipping cells causes errors.

---
## Step 4 — 설치 / Install
- `Step 0` 설치 셀을 **가장 먼저** 실행하세요 (1~2분 걸립니다)
- `준비 완료!` 메시지가 나오면 성공 ✅

---
## Step 5 — 실습 파일 올리기 / Upload the Practice Files
- `Step 1` 셀을 실행하면 **파일 선택** 버튼이 나옵니다
- 오늘 받은 **`rv_colab.zip`** 을 고르세요. 자동으로 풀립니다.

---
## Step 6 — 결과를 보는 두 가지 방법 / Two Ways to See Results

| 보고 싶은 것 | 방법 | 모양 |
|--------------|------|------|
| 숫자, 표, 목록 | `print()` | 글자로 출력 / plain text |
| **색칠한 문장, 읽기 화면** | `show_sentence()`, `display()` | 형광펜 색칠 / highlighted text |

⚠️ **주의 / Note**: 코랩의 파일은 창을 닫으면 사라집니다. 마지막 셀에서 결과를 내려받으세요.
Colab files disappear when you close the window. Download your results in the last cell."""))
C.append(md("""# 📚 보고동사로 다시 읽기 / Re-reading a Paper through Reporting Verbs
# 화학 논문 두 편, 누가 무엇을 보았다고 말하는가

**목표 / Goal**
과학 논문의 문장에서 **누가 무엇을 보았다고 말하는지** 동사를 통해 읽어 냅니다.
We read **who says they found what** in research articles, by looking at verbs.

**오늘 읽을 논문 / Today's papers** (두 편 모두 CC BY 4.0 공개 논문 / both open access)
| | 논문 / Paper | 주제 / Topic |
|--|------|------|
| A | Paiva Santiago et al. (2025), *ACS Omega* | 맥주 찌꺼기에서 초음파와 심층공융용매로 페놀 추출 |
| B | Bleus et al. (2024), *Molecules* | 맥주 찌꺼기·몰트 먼지에서 고온 수열 추출 |

---
**사용 도구 / Tools**
- `spaCy` — 문장의 품사와 구조를 분석하는 파이썬 라이브러리 / analyzes parts of speech and sentence structure
- `rvtool` — 이 수업을 위해 만든 도구(입력 검사·저장·화면) / a tool made for this class

이 노트북은 **외부 AI를 쓰지 않습니다.** 모든 분석은 여러분의 코랩 안에서 규칙으로 이루어집니다.
This notebook **does not use any external AI.** All analysis runs by rules inside your Colab."""))
C.append(md("""---
## 🧭 보고동사란? / What is a Reporting Verb?

### 같은 *show*, 다른 역할 / Same *show*, different jobs

과학 논문에는 **세 종류의 목소리**가 섞여 있습니다.
A research article mixes **three kinds of voices.**

```text
Chen et al. [32] reported the surface tension of 50 DESs.   ← 다른 연구자가 말한 것 / what OTHER researchers said
The results showed a decrease in viscosity.                 ← 이 논문의 결과 / THIS paper's own result
Figure 2 shows the effect of temperature.                   ← 그림을 가리킴 / pointing to a figure
```

Hyland(2001)는 보고(reporting)를 **"명제 내용을 다른 출처에 돌리는 것"** 으로 정의했습니다.
Hyland (2001) defined reporting as **attributing content to another source.**
그래서 첫 번째 문장만 엄밀한 의미의 보고동사입니다. 하지만 오늘은 **세 목소리를 모두** 색칠해서 구별해 봅니다.
So only the first is a reporting verb in the strict sense — but today we colour **all three** to tell them apart.

### 형광펜 색 / Highlighter colours

| 색 / Colour | 역할 / Role | 예 / Example |
|------|------|------|
| 🟨 노랑 | 선행연구 보고 / reporting prior research | *Chen et al. [32] **reported*** |
| 🟩 초록 | 자기 결과 제시 / presenting own results | *The results **showed*** |
| 🟪 보라 | 해석·주장 / interpreting, arguing | *This **suggests** that* |
| 🟦 청회색 | 연구 수행·방법 / own procedures | *Samples **were prepared*** |
| ⬜ 회색 | 그림·표·본문 지시 / pointing to figures, tables, sections | *Figure 2 **shows*** |
| 🟧 빗금 | 역할 검토 필요 / needs checking | 컴퓨터가 결정하지 못한 것 |

⚠️ 이 색은 **컴퓨터가 붙인 후보**입니다. 정답이 아닙니다. 여러분이 직접 읽고 판단하는 것이 오늘의 핵심입니다.
These colours are **candidates made by the computer**, not answers. Your own reading is the point of today's class."""))
C.append(md("""---
## ⚙️ Step 0 — 설치 / Installation
아래 셀을 실행하면 `spaCy`와 영어 모델이 설치됩니다. 처음 한 번만 하면 됩니다.
Run the cell below to install `spaCy` and its English model. Once per session."""))
C.append(code("!pip install spacy jsonschema -q\n!python -m spacy download en_core_web_sm -q"))
C.append(code('import spacy\nnlp = spacy.load("en_core_web_sm")\nprint("준비 완료! / Ready!  spaCy", spacy.__version__)'))
C.append(md("""---
## 📂 Step 1 — 실습 파일 올리기 / Upload the Practice Files
셀을 실행하고 **파일 선택**을 눌러 `rv_colab.zip`을 고르세요.
Run the cell, click **Choose Files**, and pick `rv_colab.zip`.
`필수 파일: 모두 있음` 이 나오면 성공 ✅"""))
C.append(code(r'''import os, zipfile, shutil, glob
NEED = ["rvtool.py", "engine_local.py", "viewer_template.html", "schemas/core_v1.3.json", "schemas/whole_paper_hits_v0.1.json",
        "inputs/paper_a_input.txt", "inputs/paper_a_structure.tsv", "inputs/paper_b_input.txt", "inputs/paper_b_structure.tsv"]
def arrange():
    for z in glob.glob("*.zip"):
        with zipfile.ZipFile(z) as f: f.extractall(".")
    if os.path.isdir("rv_colab"):
        for p in os.listdir("rv_colab"):
            if not os.path.exists(p): shutil.move(os.path.join("rv_colab", p), p)
arrange()
if [p for p in NEED if not os.path.exists(p)]:
    try:
        from google.colab import files
        print("rv_colab.zip 을 올려 주세요 / Please upload rv_colab.zip")
        files.upload(); arrange()
    except ImportError:
        pass
missing = [p for p in NEED if not os.path.exists(p)]
print("필수 파일 / Required files:", "모두 있음 ✅" if not missing else f"없음 ❌ {missing}")'''))
C.append(md("""---
## 📖 Step 2 — 논문 불러오기 / Load the Papers
두 논문은 이미 **한 줄에 한 문장**으로 정리되어 있고, 문장마다 번호(ID)가 붙어 있습니다.
Both papers are already split into **one sentence per line**, each with an ID.

```text
3.2.3-007   Chen et al.[32] reported the surface tension of 50 DESs …
 ↑ 3.2.3절의 7번째 문장 / sentence 7 of section 3.2.3
```"""))
C.append(code(r'''import sys, importlib, html, re
sys.path.insert(0, ".")
import rvtool as rv, engine_local as L
A = rv.load_document("inputs/paper_a_input.txt", "inputs/paper_a_structure.tsv", "paper_a", document_version="preproc-v1.2-xml-20261015")
B = rv.load_document("inputs/paper_b_input.txt", "inputs/paper_b_structure.tsv", "paper_b", document_version="preproc-v1.2-xml-20261015")
KO = {"ABS": "초록", "INT": "서론", "MET": "방법", "RD": "결과·논의", "CON": "결론"}
for D, name in ((A, "논문 A"), (B, "논문 B")):
    d = rv.describe(D)
    print(f"{name}: 문장 {d['sentences']}개, 문단 {d['paragraphs']}개, 인용이 있는 문장 {d['citing_sentences']}개")
    print("   절별 문장 수 / sentences per section:", {KO[k]: v for k, v in d["by_section"].items()})'''))
C.append(md("""---
## 🖍️ 실습 도구 만들기 / Helper for Highlighting
아래 셀은 문장을 **형광펜으로 칠해 보여 주는 도구** `show_sentence()`를 만듭니다. 그냥 실행만 하면 됩니다.
This cell defines `show_sentence()`, which shows a sentence with highlighter colours. Just run it."""))
C.append(code(r'''from IPython.display import HTML, display
COLOR = {"prior": "#F1DC5A", "result": "#BFE3C4", "interpret": "#DDD0F2", "method": "#CFDDEA", "ref": "#DADDD9", "uncertain": "#F6E1BE"}
ROLE_KO = {"prior": "선행연구 보고", "result": "자기 결과 제시", "interpret": "해석·주장", "method": "연구 수행·방법", "ref": "그림·표·본문 지시", "uncertain": "역할 검토 필요"}
def analyze_text(text, sid="9-001"):
    """논문에 없는 문장도 분석할 수 있게 해 줍니다 / analyze any sentence you type"""
    s = rv.Sentence(sid, 1, text, "RD", "9", "practice", "P001", 1, len(text.split()))
    core, hits, excluded = L.analyze_sentence("practice", s, "en_core_web_sm")
    return core, hits
def show_sentence(text, hits=None, title=""):
    if hits is None: _, hits = analyze_text(text)
    out, cur = "", 0
    for h in sorted(hits, key=lambda h: h["start"]):
        out += html.escape(text[cur:h["start"]])
        out += f'<mark style="background:{COLOR[h["role"]]};padding:0 2px">{html.escape(h["text"])}</mark>'
        cur = h["end"]
    out += html.escape(text[cur:])
    out = re.sub(r"\[(\d[\d,\s–−-]*)\]", r'<span style="color:#2E5AA8;font-family:monospace">[\1]</span>', out)
    rows = "".join(f'<tr><td><b>{html.escape(h["text"])}</b></td><td style="background:{COLOR[h["role"]]}">{ROLE_KO[h["role"]]}</td><td>{html.escape(h.get("agent",""))}</td></tr>' for h in hits)
    display(HTML(f'<div style="font-family:Georgia,serif;font-size:17px;line-height:1.7;margin:6px 0">{("<small>"+html.escape(title)+"</small><br>") if title else ""}{out}</div>'
                 + (f'<table style="font-size:13px"><tr><th>동사 / verb</th><th>역할 / role</th><th>주어 / who</th></tr>{rows}</table>' if hits else "<small>찾은 동사가 없습니다 / no verbs found</small>")))
print("show_sentence() 준비 완료! / ready!")'''))
C.append(md("""---
## 🌿 실습 1 — 한 문장 읽기 / Exercise 1: Read One Sentence
**예문 / Example** (논문 A, 3.2.3-007)

*Despite the limited data … , Chen et al.[32] reported the surface tension of 50 DESs …*

- `Chen et al.` — 다른 연구자 / other researchers
- `[32]` — 참고문헌 32번 / reference no. 32
- `reported` — 그들이 **보고했다** / they **reported** → 🟨 선행연구 보고"""))
C.append(code(r'''# 논문 A의 3.2.3-007 문장을 꺼내서 색칠해 봅니다 / take sentence 3.2.3-007 from paper A
sentence = A.by_id()["3.2.3-007"].text
show_sentence(sentence, title="논문 A · 3.2.3-007")'''))
C.append(code(r'''# ── 실습 / Practice ───────────────────────────
# 따옴표 안의 문장을 바꿔 보세요! / Change the sentence inside the quotes!
my_sentence = "Smith et al. [5] demonstrated that the yield increased at higher temperatures."

show_sentence(my_sentence)'''))
C.append(md("""---
## 🌿 실습 2 — 같은 *show*, 다른 역할 / Exercise 2: Same Verb, Different Roles

| 문장 / Sentence | 누가? / Who? | 역할 / Role |
|------|------|------|
| *Wang et al. [55] **showed** …* | 다른 연구자 / others | 🟨 선행연구 보고 |
| *The results **showed** …* | 이 논문의 자료 / this paper's data | 🟩 자기 결과 제시 |
| *Figure 2 **shows** …* | 그림 / a figure | ⬜ 그림·표 지시 |

➡️ 동사만 보고는 알 수 없습니다. **주어**와 **인용 번호**를 함께 봐야 합니다.
➡️ The verb alone is not enough — look at the **subject** and the **citation number** too."""))
C.append(code(r'''examples = [
    "Wang et al. [55] showed that the solvent could be recovered.",
    "The results showed a substantial decrease in viscosity.",
    "Figure 2 shows the effect of temperature on the density.",
]
for e in examples:
    show_sentence(e)'''))
C.append(code(r'''# ── 실습 / Practice ───────────────────────────
# 같은 동사(found)로 세 가지 역할을 만들어 보세요! / Make three roles with the same verb "found"!
my_prior  = "Lee et al. [12] found that water lowers the viscosity."
my_result = "We found that the extraction yield was highest at 60 °C."
my_figure = "The details are found in Table 3."

for s in (my_prior, my_result, my_figure):
    show_sentence(s)'''))
C.append(md("""---
## 🔢 실습 3 — 인용 번호 읽기 / Exercise 3: Reading Citation Numbers
논문에서 `[23–25]`는 **23, 24, 25번** 세 개의 참고문헌을 뜻합니다.
`[23–25]` means **three references: 23, 24 and 25.**

| 표기 / Written as | 뜻 / Means |
|------|------|
| `[7]` | 7 |
| `[40],[41]` | 40, 41 |
| `[23–25]` | 23, 24, 25 |
| `[23]−[25]` | 23, 24, 25 |"""))
C.append(code(r'''for t in ["one source [7].", "two sources [40],[41].", "a range [23–25].", "another range [23]−[25]."]:
    print(f"{t:28s} → {rv.citation_numbers(t)}")'''))
C.append(code(r'''# ── 실습 / Practice ───────────────────────────
my_citation = "as shown in several studies [3,8–10]."
print(rv.citation_numbers(my_citation))'''))
C.append(md("""---
## 📊 실습 4 — 논문 전체 색칠하기 / Exercise 4: Colour the Whole Paper
이제 두 논문의 **모든 문장**을 분석합니다. 몇 초 걸립니다.
Now we analyze **every sentence** of both papers. It takes a few seconds."""))
C.append(code(r'''import collections
RUN_ROOT = "rv_runs"
RUNS = {}
for D, name in ((A, "논문 A"), (B, "논문 B")):
    core, whole, excluded, info = L.analyze(D)
    rid = rv.new_run_id("student")
    rv.save_run(RUN_ROOT, D, rid, rv.base_record(D, "local", rid, ["core_v1.3", "whole_paper_hits_0.1"], **info), core, whole)
    RUNS[D.document_id] = rid
    c = collections.Counter(h["role"] for h in whole)
    print(f"{name}: 색칠한 동사 {len(whole)}개")
    for r in ["prior", "result", "interpret", "method", "ref", "uncertain"]:
        print(f"   {ROLE_KO[r]:10s} {c[r]:4d}")'''))
C.append(code(r'''# ── 실습 / Practice ───────────────────────────
# 논문 A에서 보고 싶은 문장 번호를 넣어 보세요 / Put any sentence ID from paper A
my_id = "3.3.2-020"

r = rv.load_run(RUN_ROOT, "paper_a", RUNS["paper_a"])
hits = [h for h in r["whole"] if h["sentence_id"] == my_id]
show_sentence(A.by_id()[my_id].text, hits, title=f"논문 A · {my_id}")'''))
C.append(md("""---
## 🔍 실습 5 — 용례 찾기 / Exercise 5: Concordance (KWIC)
**콘코던스(KWIC)** 는 찾는 말을 **가운데** 두고 앞뒤 문맥을 나란히 보여 줍니다.
A **concordance (KWIC)** lines up every use of a word with its context on both sides.

```text
   …the surface tension of DES, Chen et al.[32] | reported | the surface tension of 50 …
```"""))
C.append(code(r'''def kwic(D, word, width=55, limit=30):
    n = 0
    for s in D.sentences:
        low = s.text.lower(); p = low.find(word.lower())
        while p >= 0 and n < limit:
            left, mid, right = s.text[max(0, p-width):p], s.text[p:p+len(word)], s.text[p+len(word):p+len(word)+width]
            print(f"{s.id:>10}  {left:>{width}} | {mid} | {right}")
            n += 1; p = low.find(word.lower(), p + 1)
    print(f"\n'{word}' 용례 {n}개 (최대 {limit}개 표시) / {n} hits shown")
kwic(A, "reported")'''))
C.append(code(r'''# ── 실습 / Practice ───────────────────────────
# 찾고 싶은 말과 논문(A 또는 B)을 바꿔 보세요 / Change the word and the paper
my_word  = "showed"
my_paper = B          # A 또는 B / A or B

kwic(my_paper, my_word)'''))
C.append(md("""---
## 🖥️ 실습 6 — 읽기 화면 열기 / Exercise 6: Open the Reading Screen
두 논문을 **색칠 → 흐름 그래프 → 클릭 → 원래 문맥** 순서로 읽는 화면을 만듭니다.
This builds a screen to read both papers: **colour → flow graph → click → original context.**

| 화면에서 / On the screen | 하는 일 / What it does |
|------|------|
| 꺾은선 그래프의 점 클릭 / click a point | 그 구간의 문장이 열림 / opens those sentences |
| 문장 클릭 / click a sentence | 앞뒤 문장과 문단이 열림 / shows context and paragraph |
| 용례 찾기 / search | 콘코던스 / concordance |
| 두 논문 나란히 / compare tab | 두 논문의 흐름 비교 / compare both papers |

화면이 코랩 안에서 잘 안 보이면, 내려받은 HTML 파일을 브라우저로 여세요.
If the screen looks cramped in Colab, open the downloaded HTML file in your browser."""))
C.append(code(r'''import time
view = f"보고동사로다시읽기_화면_{time.strftime('%H%M%S')}.html"
rv.build_viewer([rv.load_run(RUN_ROOT, "paper_a", RUNS["paper_a"]), rv.load_run(RUN_ROOT, "paper_b", RUNS["paper_b"])], [A, B], view)
print("화면 파일 / screen file:", view)
try:
    from google.colab import files
    display(HTML(open(view, encoding="utf-8").read()))
    files.download(view)
except ImportError:
    pass'''))
C.append(md("""---
## ⚖️ 실습 7 — 두 논문 비교 / Exercise 7: Compare the Two Papers
두 논문은 길이가 다르니 **1,000단어당** 몇 개인지로 비교합니다. 초록은 뺍니다.
The papers differ in length, so we compare **per 1,000 words** (abstract excluded)."""))
C.append(code(r'''rows = {}
for D, name in ((A, "A"), (B, "B")):
    r = rv.load_run(RUN_ROOT, D.document_id, RUNS[D.document_id])
    for x in rv.aggregate(D, r["whole"], exclude_abstract=True)["rows"]:
        rows.setdefault(ROLE_KO[x["role"]], {})[f"{name}·{KO[x['section_type']]}"] = x["per_1000_words"]
try:
    import pandas as pd
    display(pd.DataFrame(rows).T.fillna("–"))
except ImportError:
    for k, v in rows.items(): print(k, v)'''))
C.append(md("""### 💬 생각해 볼 질문 / Questions to Discuss
1. 🟨 선행연구 보고는 두 논문의 **어느 절**에 많이 나타나나요? 왜 그럴까요?
   In which **section** does prior-research reporting appear most? Why?
2. 🟦 연구 수행·방법이 결과·논의 절에도 나타난다면, 어떤 문장들인가요? (실습 4의 `my_id`로 확인)
   If own procedures appear in Results & Discussion, what are those sentences?
3. 🟧 역할 검토 필요 문장을 하나 골라, 여러분이라면 어떤 색을 칠할지 말해 보세요.
   Pick one "needs checking" sentence. Which colour would **you** give it?
4. 두 논문의 차이를 **원인**으로 설명할 수 있을까요, 아니면 **관찰**일 뿐일까요?
   Can we explain the difference as a **cause**, or is it only an **observation**?"""))
C.append(md("""---
## 💾 결과 내려받기 / Download Your Results
코랩 파일은 창을 닫으면 사라집니다. 아래 셀로 결과를 내려받으세요.
Colab files disappear when you close the window. Download your results now."""))
C.append(code(r'''z = shutil.make_archive(f"내결과_{time.strftime('%H%M%S')}", "zip", RUN_ROOT)
print("내려받을 파일 / file:", z)
try:
    from google.colab import files; files.download(z)
except ImportError:
    pass'''))
C.append(md("""---
## ✅ 오늘 배운 것 / What We Learned Today

| 실습 / Exercise | 배운 것 / What we learned |
|------|------|
| 1 | 보고동사 = 다른 출처에 돌리는 동사 / attributing to another source |
| 2 | 같은 동사도 **주어와 인용**에 따라 역할이 다르다 / role depends on subject and citation |
| 3 | 인용 번호 읽기 `[23–25]` = 23, 24, 25 |
| 4 | 논문 전체 색칠과 역할별 개수 / colouring a whole paper |
| 5 | 콘코던스(KWIC)로 용례 모아 보기 / gathering uses with a concordance |
| 6 | 그래프 → 클릭 → 원래 문맥으로 돌아가 읽기 / graph → click → context |
| 7 | 1,000단어당 비교와 해석의 조심 / fair comparison and careful interpretation |

---
**핵심 원리 / Key Principle**

> 동사만 보지 말고, **누가(주어)** 그리고 **어디서 왔는지(인용)** 를 함께 본다.
> Don't look at the verb alone — look at **who** (subject) and **where it comes from** (citation).

- 🟨 다른 연구자 + 인용 번호 → 선행연구 보고 / others + citation → reporting prior research
- 🟩 이 논문의 자료·우리(we) → 자기 결과 / this paper's data, *we* → own results
- ⬜ Figure·Table → 그림·표 지시 / pointing to figures and tables

⚠️ 컴퓨터의 색은 **후보**입니다. 마지막 판단은 언제나 읽는 사람이 합니다.
The computer's colours are **candidates**. The final judgement is always the reader's."""))
nb = nbf.v4.new_notebook(); nb.cells = C
nb.metadata["kernelspec"] = dict(name="python3", display_name="Python 3", language="python")
nb.metadata["colab"] = dict(provenance=[])
nbf.write(nb, "보고동사로다시읽기_학생실습.ipynb"); nbf.validate(nbf.read("보고동사로다시읽기_학생실습.ipynb", as_version=4)); print("ok", len(C))
