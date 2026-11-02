# 보고동사로 다시 읽기 — 코랩 실행본 안내

맥주 찌꺼기를 다룬 화학 논문 두 편(논문 A: ACS Omega 2025, 논문 B: Molecules 2024)을 논문 전체에서 다시 읽는 도구입니다.
색칠 → 흐름 그래프 → 클릭 → 원래 문맥으로 돌아가기가 중심입니다.

## 노트북 두 개
| 노트북 | 분석 엔진 | 외부 전송 |
|---|---|---|
| `01_보고동사로다시읽기_로컬분석_API없음.ipynb` | spaCy 구문분석 + 규칙(`engine_local.py`) | 없음(설치 때 spaCy·영어 모델만 내려받음) |
| `02_보고동사로다시읽기_API분석_Claude.ipynb` | Anthropic Claude API(`engine_api.py`) | 문장 원문을 API로 보냄(초안 주석 CSV는 보내지 않음) |

두 노트북은 같은 순서를 따릅니다: 설치 → 파일 준비 → 입력 검사 → 소량 시험 → 분석 → 검증 → 저장 → 다시 읽기 → (일치도) → 집계 → 화면.
입력 검사·저장·다시 읽기·검증·화면은 공통 모듈 `rvtool.py` 하나를 함께 씁니다.

## 연구자 사전 실습 노트북
`보고동사로다시읽기_연구자사전실습.ipynb`는 버셀 세션 전에 황 교수님(화학)과 윤 교수님(언어학)이 함께 실행해 보는 용도입니다. 단계 안내는 학생용과 같이 자세하고, 단계마다 실행 목적·성공 기준·검토할 점을 붙였습니다. 판정이 의심스러운 문장을 `검토메모.csv`에 한 줄씩 남기는 칸이 있으며, 이 메모는 정답표가 아니라 검토 기록입니다. 외부 AI를 쓰지 않습니다.

## 학생 실습용 노트북
`보고동사로다시읽기_학생실습.ipynb`는 수업용입니다. 한국어·영어 설명, 실습 칸(`my_sentence`, `my_word` 등을 바꿔 보기), 생각해 볼 질문이 들어 있습니다. 외부 AI를 쓰지 않고 API 키도 필요 없습니다. 학생에게는 이 노트북과 `rv_colab.zip` 두 파일만 나눠 주면 됩니다.

## 코랩에서 쓰는 법
1. 노트북을 코랩에서 엽니다(파일 → 노트북 업로드).
2. 위에서부터 칸을 차례로 실행합니다. "파일 준비" 칸에서 `rv_colab.zip`을 올리면 자동으로 풀립니다. ZIP은 새 임시 폴더에 풀어 필수 파일이 모두 있을 때만 덮어써 옮기므로, 같은 세션에서 새 ZIP을 올려도 이전 파일과 섞이지 않습니다. 필수 파일이 빠진 ZIP이면 아무것도 옮기지 않고 멈춥니다.
3. ZIP을 올릴 수 없으면 아래 파일을 **하나씩** 올리면 제자리로 옮겨집니다.
   - 필수 10개: `rvtool.py`, `engine_local.py`, `engine_api.py`, `viewer_template.html`, `core_v1.3.json`, `whole_paper_hits_v0.1.json`, `paper_a_input.txt`, `paper_a_structure.tsv`, `paper_b_input.txt`, `paper_b_structure.tsv`
   - 선택 2개(일치도 계산용): `paper_a_draft_v1.3.csv`, `paper_b_draft_v1.3.csv`
4. API 노트북은 코랩 왼쪽 🔑(보안 비밀)에 `ANTHROPIC_API_KEY`를 넣고 노트북 접근을 허용합니다. 넣지 않으면 실행 중 입력창이 뜹니다. 키는 어디에도 저장되지 않습니다.
5. API 노트북의 `CONFIRM_SEND`는 기본값이 **False**입니다. 직접 `True`로 바꾸기 전에는 소량 시험 칸에서 멈추고 아무것도 전송하지 않습니다.
6. `CONFIRM_SEND = True`로 바꾸면 시험 문장 2개만 보내는 소량 시험이 실행되고, 전체 실행과 똑같이 정식 저장 → 다시 읽기(해시 확인) → 검증 → 부분 화면(분석한 2문장만 색칠, 나머지는 '미분석')까지 이어집니다. ① 노트북의 소량 시험도 같은 순서를 따릅니다.
7. 전체 실행은 `FULL_RUN = True`로 따로 켜야 합니다. 시작할 때 논문마다 출력되는 `새 실행 ID`를 적어 두세요. 끊기면 `RESUME`에 **두 논문의 실행 ID를 모두** 넣어 다시 실행합니다. 저장까지 끝난 논문은 다시 부르지 않고(추가 요금 없음) 끊긴 논문만 이어서 실행합니다. `RESUME`의 ID를 찾지 못하면(오타 등) 새 실행을 시작하지 않고 멈춥니다. 재개 전에 처음 실행의 입력·설정(`work/manifest.json`: 입력 TXT·TSV 해시, document_version, 문장 목록, 공급자·모델·max_tokens, 묶음 크기, 프롬프트 버전과 해시, 엔진 버전)과 같은지 확인하고, 하나라도 다르면 멈춥니다. 끝난 묶음의 캐시도 다시 검증하며, 이미 저장이 끝난 실행은 재개하지 않습니다.
8. 모델 ID(`MODEL`)는 Anthropic 문서 모델 목록에서 확인해 넣으세요: https://docs.claude.com/en/docs/about-claude/models

## 로컬 서버(FastAPI)
코랩 대신 내 컴퓨터에서 같은 로컬 엔진을 HTTP로 쓸 수 있습니다(외부 API 엔진은 서버에 넣지 않았습니다).
```
pip install -r requirements.txt
uvicorn server.main:app --reload
```
- `GET /health`, `GET /documents`(전처리 기록 대조 포함), `GET /documents/{id}/sentences`
- `POST /analyze/sentence` 임의 문장 즉석 분석(저장 안 함), `POST /runs/local` 분석 후 검증 통과 시 저장
- `GET /runs`, `GET /runs/{doc}/{run_id}`, `GET /runs/{doc}/{run_id}/agreement`, `GET /viewer?paper_a=&paper_b=`
- **클라이언트 화면** `http://localhost:8000/app`: 노트북이 만드는 화면(`viewer_template.html`)과 같은 화면을 서버 자료로 엽니다. 실행 ID를 주지 않으면 두 논문의 가장 최근 전체 실행을 보여 주고, `?paper_a=<실행ID>&paper_b=<실행ID>`로 고를 수 있습니다. 저장된 실행이 없으면 화면에서 바로 로컬 분석을 실행할 수 있습니다. 화면 자료는 `GET /viewer-data`(JSON)로 받습니다.
- 결과 폴더는 기본 `rv_runs/`이며 `RV_RUN_ROOT`로 바꿀 수 있습니다. 인증이 없으니 내 컴퓨터에서만 쓰세요.

## 결과가 저장되는 방식
- `rv_runs/<document_id>/<run_id>/`에 실행마다 새 폴더가 생깁니다. 같은 이름이 있으면 멈추고 덮어쓰지 않습니다.
- `run.json`: 엔진, 범위(`core_v1.3`, `whole_paper_hits_0.1`), 입력 판본, 입력 파일 해시(TXT·TSV·CSV), 규칙·프롬프트·스키마 버전, 모델·설정, 처리 상태(성공·실패 문장), 검증 결과, 출력 파일 해시.
- `core.json`: 명세서 v1.3 문장별 결과(스키마 v1.3을 **수정 없이** 사용).
- `whole.json`: 논문 전체 표현별 결과(별도 스키마 `whole_paper_hits_v0.1`). `start/end`는 Python 코드포인트 기준이며 `sentence[start:end]==text`를 검사합니다. 화면에 넣을 때만 JavaScript 위치로 바꿉니다.
- API 실행은 `work/`에 묶음별 응답 원본(`*.raw.json`), 형식 오류(`*.parse_error.json`), 스키마·ID·위치 검사 실패(`*.schema_error.json`) 기록을 남깁니다. 완료 캐시(`chunk_###.ok.json`)는 응답이 v1.3 core 스키마·ID 대응·whole 위치 검사를 **모두 통과한 뒤에만** 만들고, 응답 원본 파일 이름과 해시를 함께 적습니다.
- 응답이 `max_tokens`에 걸려 잘리면 같은 요청을 되풀이하지 않고 묶음을 반으로 나눠 다시 보냅니다(`*.truncated.json` 기록). 한 문장도 들어가지 않으면 그 묶음을 '실패'로 기록하니 `MAX_TOKENS`를 늘리세요.
- 다시 열 때 출력 파일 해시를 확인해 저장 후 바뀐 파일을 잡아냅니다.

## 지켜야 할 해석
- 모든 결과는 **후보**입니다. 사람이 확인하지 않았습니다.
- 초안 주석 CSV(Claude 판정 초안, status=pending)와의 비교는 **일치도**이지 정확도가 아닙니다. 불일치 후보에는 인용 번호·보고동사 유무·**보고동사 문자열**·인용 방식 가운데 다른 항목이 `differences`로 적힙니다.
- 로컬 노트북의 `USE_ANNOTATIONS=True`는 초안 주석을 그대로 가져와 표시하는 별도 모드입니다. 이 모드의 결과는 같은 CSV와 비교하지 않습니다(노트북이 막습니다).
- `role`(선행연구 보고·자기 결과 제시·해석·방법·지시·검토 필요)은 이 도구의 분류이며 Hyland(2001)의 과정·평가 분류 자체가 아닙니다. core 층은 인용 표지가 있는 문장만 대상으로 하므로 Hyland의 탐색 절차를 완전히 재현하지 않습니다.
- 두 논문을 서로 다른 엔진이나 모드로 분석했다면 수치를 직접 비교하지 마세요. 화면 맨 위에 실행 정보가 표시됩니다.
- PDF 추출·DOI 수집은 범위 밖입니다. SLA(감성 분석)와 섞지 않습니다.

## 입력 판본
`inputs/`의 TXT·TSV는 2026-10-15에 Europe PMC XML에서 만든 **원래 전처리 파일**입니다. 입력 머리부에 document_version이 없어 노트북에서 `preproc-v1.2-xml-20261015`로 정합니다.
인계 묶음의 재포장 파일(`*_repacked`)과 대조한 결과는 `tests/input_reconciliation.json`과 `시험기록_및_미해결.md`에 있습니다.
