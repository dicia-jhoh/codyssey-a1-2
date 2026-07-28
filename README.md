# 여행 추천 파이프라인 (A1-2: API 연동 기초)

미션 projectNo=143002 / lcorsNo=1128003 / uqstnNo=188027 (Advanced · 개념학습 · 40h)

**날짜 하나를 주면 여행 리포트가 나옵니다.** 터미널에서 `python main.py -date "2026-09-15"` 를 치면
LLM 이 여행지를 추천하고 → 그 도시의 맛집을 지도 API 로 찾고 → 둘을 합친 Markdown 리포트를 만듭니다.

```
[사용자] -date 2026-09-15
    ↓
[1단계] LLM API ─────→ {"recommended_city": "강릉",                    ← 필수: 대표 도시 1개
                        "recommended_cities": ["강릉", "속초"],       ← 보너스: 후보 목록
                        "weather": …, "events": […], "reason": …}
    ↓ 대표 도시(+후보 목록)를 반복문으로 전달
[2단계] 지도 API ────→ {"강릉": [{"name": "초당순두부마을", …}, …], "속초": [ … ]}  (지역별, 0건 가능)
    ↓ 둘 다 전달
[3단계] 리포트 생성 ──→ results/2026-09-15.md  +  results/2026-09-15.json
```

---

## 이 미션의 위치 — 앞뒤 미션과의 연결

| 이어받은 것 | 어디서 | 이 프로젝트에서 |
|---|---|---|
| 노코드 워크플로우 사고(Trigger → Action → 분기 → 출력) | **B1-3** | 같은 흐름을 Make/n8n 상자가 아니라 **Python 코드**로 짰습니다. 상자 하나가 함수 하나입니다 |
| 구조화 출력 프롬프트 설계 | **B1-1** | 1단계 프롬프트가 "JSON 만 출력하라"를 강제하는 방식(아래 §LLM 출력 구조화) |
| 함수 분리·커밋 단위 감각 | **A1-1** | 파일 6개 역할 분리 + 기능 단위 커밋 |

**다음 미션으로 넘길 것**: `results/` 날짜 파일명 규약과 "부분 실패해도 산출물은 낸다"는 오류 정책은
A2-2(뉴스 트렌드 파이프라인)에서 그대로 씁니다. LLM 출력을 JSON 으로 강제하는 패턴은
A1-3·A2-1·M1-2 에서 반복됩니다. 이 미션의 확장판이 **M2-2(멀티 에이전트 여행 플래너)** 입니다 —
같은 소재인데, 여기서는 흐름을 사람이 짜고 거기서는 LLM 이 스스로 판단합니다.

---

## 실행 방법

```bash
# 1. 저장소 내려받기
git clone https://github.com/dicia-jhoh/codyssey-a1-2.git
cd codyssey-a1-2

# 2. Python 버전 확인 (3.10 이상)
python --version

# 3. API 키 설정 — .env 파일을 만듭니다 (키는 코드에 적지 않습니다)
cp .env.example .env
#    편집기로 .env 를 열어 YOUR_KEY 자리에 실제 키를 넣으세요

# 4. 실행
python main.py -date "2026-09-15"
```

**키 없이 산출물 형태만 보려면**: `python demo_offline.py` — 리포트 생성 단계만 예시 데이터로 돌립니다.

| 옵션 | 뜻 |
|---|---|
| `-date "YYYY-MM-DD"` | **필수.** 여행 날짜 |
| `--size N` | **지역당** 맛집 개수(기본 5) |
| `--no-cache` | 같은 날짜의 저장 결과가 있어도 무시하고 API 를 다시 호출 |

---

## 필요한 API 키 2개

| 용도 | 서비스 | 환경변수 이름 | 발급처 |
|---|---|---|---|
| 1단계 여행지 추천 | OpenAI (LLM) | `OPENAI_API_KEY` | platform.openai.com |
| 2단계 맛집 검색 | Kakao Local (지도/장소) | `KAKAO_REST_API_KEY` | developers.kakao.com |

지도 API 는 **Kakao Local** 을 골랐습니다. 국내 장소 검색이 가능하고, 응답이 JSON 이며,
필요한 필드(상호·주소·분류·링크·좌표)를 전부 줍니다.

**Naver Local Search 로 바꾸려면** `places.py` 의 `search_places()` 와 `_to_item()` 두 함수만
고치면 됩니다 — 응답 필드를 우리 형식으로 한 번 옮겨 두었기 때문에 리포트 코드는 그대로입니다.
두 서비스의 인증 방식 차이:

| | Kakao Local (현재) | Naver Local Search |
|---|---|---|
| 발급 단위 | REST API 키 **1개** | 클라이언트 **ID + Secret 2개** |
| 헤더 | `Authorization: KakaoAK <REST키>` | `X-Naver-Client-Id: <ID>`<br>`X-Naver-Client-Secret: <Secret>` |
| 환경변수(예) | `KAKAO_REST_API_KEY` | `NAVER_CLIENT_ID` · `NAVER_CLIENT_SECRET` |
| 엔드포인트 | `dapi.kakao.com/v2/local/search/keyword.json` | `openapi.naver.com/v1/search/local.json` |
| 좌표 필드 | `x`=경도 · `y`=위도 | `mapx` · `mapy`(카텍 좌표계 — 변환 필요) |

**401/403 이 날 때 점검 순서**:

| 서비스 | 무엇을 먼저 보나 |
|---|---|
| Kakao | ① 헤더 형식이 `KakaoAK <키>` 인가(`Bearer` 아님, 접두어와 키 사이 공백 1칸) ② **REST API 키**를 썼는가(JavaScript·Admin 키가 아니라) ③ 앱 설정에서 플랫폼(도메인) 등록과 "카카오맵" API 사용 권한이 켜져 있는가 |
| Naver | ① 헤더 **이름 오타** — `X-Naver-Client-Id`/`X-Naver-Client-Secret`(대소문자·하이픈 정확히) ② ID 와 Secret 을 **뒤바꿔 넣지 않았는가** ③ 애플리케이션에 "검색" API 가 추가돼 있는가 ④ 값 앞뒤에 공백·따옴표가 섞이지 않았는가 |

두 서비스 다 **키 자체가 틀린 경우와 권한이 없는 경우가 같은 401/403 으로 온다**는 점이 함정입니다.
그래서 키를 다시 복사해 넣어 보는 것보다 **콘솔에서 API 사용 권한부터 확인**하는 편이 빠릅니다.

> 이 저장소에는 **실제 키가 들어 있지 않습니다.** `.env` 는 `.gitignore` 에 있고,
> 형식만 보여주는 `.env.example` 에는 `YOUR_KEY` 자리표시자만 있습니다.

---

## 파일 구조

```
main.py            시작 지점 — CLI 옵션·단계 순서·결과 저장
config.py          키 관리 — .env/환경변수 읽기, 미설정 안내
recommend.py       1단계 — LLM 호출·JSON 검증·재시도
places.py          2단계 — 지도 API 호출·응답 정규화
report.py          3단계 — Markdown 리포트 생성 (순수 함수)
demo_offline.py    키 없이 리포트 단계만 확인하는 데모
docs/run-log.md    실행 결과 전문(실측)
results/           산출물 저장 위치 (gitignore — 실행하면 생깁니다)
```

**단계마다 파일을 나눈 이유**: 각 단계의 실패 모드가 완전히 다릅니다. LLM 은 형식이 깨지고,
지도 API 는 인증·쿼터로 막히고, 리포트는 데이터가 비어서 문제가 생깁니다. 한 파일에 섞으면
어느 단계의 문제인지 구분하는 데 시간이 듭니다. `main.py` 만 읽으면 흐름이, 각 파일을 열면
그 단계의 사정이 보입니다.

---

## 핵심 개념 설명

### REST API — 요청/응답 구조와 GET/POST 차이

**REST API 는 "정해진 주소로 요청을 보내면 정해진 형식으로 답이 오는" 약속**입니다.
이 프로그램은 두 개의 API 를 서로 다른 메서드로 부릅니다:

| | 1단계 LLM (OpenAI) | 2단계 지도 (Kakao) |
|---|---|---|
| **메서드** | `POST` | `GET` |
| **보내는 곳** | 요청 **본문(body)** 에 JSON | **URL 쿼리스트링** (`?query=강릉+맛집&size=5`) |
| **인증** | `Authorization: Bearer <키>` 헤더 | `Authorization: KakaoAK <키>` 헤더 |
| **응답** | JSON | JSON |

**GET 과 POST 의 차이**:

| | GET | POST |
|---|---|---|
| 의미 | **읽기** — 서버 상태를 바꾸지 않는다 | **보내기** — 서버에 데이터를 준다 |
| 데이터 위치 | URL 에 노출 | 본문에 담김 |
| 길이 제한 | URL 길이 한계 있음 | 사실상 제한 없음 |
| 캐시·북마크 | 가능 | 불가 |
| 이 프로젝트 | 맛집 검색(조건이 짧고 읽기만) | LLM 호출(프롬프트가 길고 본문에 담아야) |

**왜 키를 URL 이 아니라 헤더에 넣나**: URL 은 서버 접속 기록·프록시 로그·브라우저 히스토리에
그대로 남습니다. 헤더는 그런 곳에 기본으로 기록되지 않습니다. 같은 이유로 키를 쿼리스트링에
받는 API 라도 가능하면 헤더 방식을 씁니다.

### LLM 출력을 JSON 으로 구조화해 다음 단계로 넘기는 흐름

이 프로그램의 핵심 설계입니다.

```python
# 1단계가 돌려준 것 (dict)
{"recommended_city": "강릉",                  # 필수 — 대표 도시
 "recommended_cities": ["강릉", "속초"],       # 보너스 — 후보 목록(대표가 첫 번째)
 "weather": "...", "events": [...], "reason": "..."}

# 2단계는 대표 도시를 기본으로, 목록이 있으면 반복해서 이어받는다
main_city = recommendation["recommended_city"]
cities = recommendation.get("recommended_cities") or [main_city]
restaurants = {}
for city in cities:
    restaurants[city] = places.find_restaurants(map_key, city, errors, size=args.size)
```

**줄글로 받으면 왜 안 되나**: LLM 이 "이번 가을엔 강릉이 좋겠습니다"라고 답하면, 프로그램은
"강릉"이라는 세 글자를 문장에서 잘라내야 합니다. 그 잘라내기 코드는 LLM 이 표현을 조금만 바꿔도
(`"강릉시를 추천드립니다"`, `"저는 강릉을 골랐어요"`) 깨집니다.

**JSON 으로 받으면** 값을 꺼내는 코드가 `data["recommended_city"]` 한 줄로 끝나고, LLM 이 문장을
어떻게 쓰든 영향받지 않습니다. **출력 형식을 고정하는 것이 두 단계를 잇는 접합부**입니다.

형식을 강제하는 방법은 셋을 함께 씁니다:
1. 프롬프트에 **필수 키와 타입을 명시**하고, "JSON 외의 설명·코드펜스를 붙이지 마라"를 규칙으로 넣는다.
2. 받은 뒤 **코드펜스를 벗기고**(LLM 이 습관적으로 ```` ```json ````을 붙입니다) JSON 으로 읽는다.
3. **필수 키와 타입을 검증**한다 — `{"city": "강릉"}` 처럼 키 이름이 다른 응답을 여기서 잡습니다.

3번을 빼면 다음 단계에서 `KeyError` 로 죽는데, 그때는 원인이 "LLM 응답 형식"이라는 게 보이지 않습니다.
**문제는 만들어진 자리에서 잡아야** 합니다.

> 이 미션은 날씨·행사의 **정확도**를 평가하지 않습니다. 중요한 것은 "구조화된 출력"과
> "다음 단계 입력으로의 연결"입니다.

### 외부 API 의 대표 오류와 대응 원칙

| 오류 종류 | 어떻게 나타나나 | 원인 | 이 프로그램의 대응 |
|---|---|---|---|
| **인증** | HTTP 401 / 403 | 키가 틀림·만료·권한 없음·도메인 미등록 | 재시도해도 같으므로 **즉시 포기**하고 점검 안내 |
| **쿼터** | HTTP 429 | 요청 한도 초과 | 사유를 남기고 진행(잠시 후 재시도 안내) |
| **네트워크** | 연결 실패·타임아웃 | 인터넷·DNS·서버 다운 | 사유를 남기고 진행. LLM 은 1회 재시도 |
| **파싱** | JSON 오류·키 누락 | 응답 형식이 기대와 다름 | LLM 은 **형식만 강조한 프롬프트로 1회 재시도**, 지도는 데이터 없음 처리 |

**대응 원칙 셋**:
1. **치명/비치명을 가른다** — 1단계 실패는 중단(추천 도시가 없으면 2·3단계가 성립하지 않음),
   2단계 실패는 계속(맛집은 리포트의 일부).
2. **재시도는 유한하게** — LLM 파싱 실패만 **1회**. 무한 재시도는 쿼터를 태우고 사용자를 세워둡니다.
   인증 오류는 재시도 자체를 하지 않습니다(결과가 같습니다).
3. **실패를 삼키지 않는다** — 모든 실패는 `errors` 리스트에 쌓여 리포트 `errors` 섹션과
   `results/*.json` 에 남습니다. 조용히 넘어가면 "왜 맛집이 없지?"를 알 수 없습니다.

### API 키를 `.env`/환경변수로 관리하는 이유

| 이유 | 구체적으로 |
|---|---|
| **유출 방지** | 코드에 적으면 `git commit` 과 함께 GitHub 에 올라갑니다. 공개 저장소의 키는 봇이 몇 분 안에 긁어갑니다 |
| **교체 용이** | 키를 바꿔도 코드를 고치지 않습니다 — `.env` 값만 바꾸면 됩니다. 개발·운영 환경에 다른 키를 쓸 수도 있습니다 |
| **과금 사고 예방** | 유출된 키로 남이 API 를 쓰면 **내 계정에 청구**됩니다. 쿼터가 걸린 서비스는 서비스 중단까지 이어집니다 |

이 프로젝트의 3중 방어:
1. `config.py` 는 **환경변수 이름만** 알고 값은 모릅니다(`LLM_KEY_NAME = "OPENAI_API_KEY"`).
2. `.gitignore` 에 `.env` 가 들어 있어 실수로 `git add .` 를 해도 올라가지 않습니다.
3. `.env.example` 로 **형식만** 공유합니다 — 값은 `YOUR_KEY` 자리표시자입니다.

**환경변수 설정 예시**(값은 자리표시자입니다):

```bash
# macOS / Linux — 지금 터미널 세션에만 적용
export OPENAI_API_KEY="YOUR_KEY"

# Windows PowerShell — 지금 세션에만 적용
$env:OPENAI_API_KEY="YOUR_KEY"
```

**키가 이미 유출됐다면**: 코드에서 지우는 것으론 부족합니다(git 이력에 남습니다).
해당 키를 **즉시 폐기하고 재발급**해야 합니다.

---

## 산출물 — `results/` 폴더

실행 날짜를 파일명으로 씁니다.

| 파일 | 내용 |
|---|---|
| `results/2026-09-15.json` | 원본 데이터 — `recommendation`(1차 JSON) · `restaurants`(`{도시: [아이템…]}`, 0건 가능) · `errors`(배열) |
| `results/2026-09-15.md` | 최종 리포트 — 추천 지역·이유 / 날씨 / 행사 / 맛집 / 1일 일정 / errors |

**둘 다 남기는 이유**: `.md` 는 사람이 읽고, `.json` 은 프로그램이 다시 읽습니다.
캐싱 기능이 `.json` 을 재사용해 API 호출 없이 리포트만 다시 만듭니다.

`results/` 는 `.gitignore` 에 있습니다 — **실행하면 다시 만들어지는 산출물**이고,
사람마다 날짜·결과가 달라 저장소에 넣으면 충돌만 생깁니다.

### 리포트 실물 (오프라인 데모 출력)

```markdown
# demo-2026-09-15 여행 리포트 — 강릉 · 속초

## 추천 지역과 이유
**강릉**  **속초**

여름 성수기가 지나 숙소·해변이 한산해집니다. 강릉은 바다와 커피거리를 하루에 묶을 수 있고,
속초는 설악산 초입 단풍이 시작돼 성격이 다른 하루를 고를 수 있습니다.

## 날씨
9월 중순 강릉은 낮 23~26도로 선선하고 습도가 낮아 해안 산책에 좋습니다.

## 행사·축제
- 강릉커피축제(가을 시즌)
- 정동진 해변 야간 조명

## 맛집 (지역별)

### 강릉
| 이름 | 주소 | 분류 | 링크 |
|---|---|---|---|
| 초당순두부마을 | 강원 강릉시 초당순두부길 30 | 두부요리 | [지도](…) |
| 강릉 회센터 | 강원 강릉시 창해로 100 | 회 | [지도](…) |

### 속초
| 이름 | 주소 | 분류 | 링크 |
|---|---|---|---|
| 속초 중앙시장 닭강정 | 강원 속초시 중앙로147번길 12 | 닭강정 | [지도](…) |

## 1일 일정 제안 (지역별)

### 강릉
- **오전**: 강릉 도착, 대표 명소 한 곳 둘러보기
- **오후**: 점심(초당순두부마을) 후 시내·해안 산책, 카페 휴식
- **저녁**: 저녁 식사(강릉 회센터) 후 야경 스팟 방문

### 속초
- **오전**: 속초 도착, 대표 명소 한 곳 둘러보기
- **오후**: 점심(속초 중앙시장 닭강정) 후 시내·해안 산책, 카페 휴식
- **저녁**: 저녁 식사(현지 맛집) 후 야경 스팟 방문

## errors
- 없음
```

**한 지역만 실패한 경우**(같은 데모의 사례 2 — 속초 검색이 401 로 실패):

```markdown
### 강릉
| 이름 | 주소 | 분류 | 링크 |
|---|---|---|---|
| 초당순두부마을 | … | 두부요리 | [지도](…) |     ← 정상 출력

### 속초
데이터 없음 (검색 결과가 없거나 API 호출에 실패했습니다)

## errors
- '속초' 지도 API HTTP 401: 인증 실패. REST API 키 값·헤더 형식을 확인하세요
```

리포트는 **그래도 생성됩니다.** 전문은 [`docs/run-log.md`](docs/run-log.md) 에 있습니다.

---

## 실행 결과 로그 (실측)

**날짜 형식이 틀린 경우** — 사용법을 출력하고 종료합니다:

```
$ python main.py -date 2026-13-99
[중단] 날짜 형식이 올바르지 않습니다: '2026-13-99'
usage: main.py [-h] -date DATE [--size SIZE] [--no-cache]
```

`2026-02-30` 처럼 **형식은 맞지만 존재하지 않는 날짜**도 걸립니다 —
`datetime.strptime` 이 실제 달력을 보기 때문입니다(정규식만 쓰면 통과합니다).

**키가 없는 경우** — 즉시 멈추고 설정 방법을 안내합니다:

```
$ python main.py -date 2026-09-15
[중단] 환경변수 OPENAI_API_KEY 가 설정되어 있지 않습니다.

키를 설정하는 방법 (셋 중 하나):
  1) macOS / Linux — export OPENAI_API_KEY="YOUR_KEY"
  2) Windows PowerShell — $env:OPENAI_API_KEY="YOUR_KEY"
  3) 프로젝트 폴더에 .env 파일 만들기 (권장)
```

안내문에도 **실제 키 값은 나오지 않습니다** — `YOUR_KEY` 자리표시자만 씁니다.

> 실제 API 키로 실행한 화면 캡처는 **실제 연동 시 이 자리**에 추가합니다.
> 키 발급이 필요 없는 검증 경로(입력 검증·키 안내·리포트 생성)는 위 로그와
> [`docs/run-log.md`](docs/run-log.md) 에 실행 출력 원문으로 남겼습니다.

---

## 보너스 (수행)

**보너스 2 — 결과 캐싱**: 같은 `-date` 로 다시 실행하면 `results/<날짜>.json` 이 있는지 보고,
있으면 **API 를 호출하지 않고** 그 데이터로 리포트만 다시 만듭니다.

```
$ python main.py -date 2026-09-15     # 두 번째 실행
[캐시] 2026-09-15 저장 결과를 재사용합니다(API 호출 없음).
```

`--no-cache` 로 강제로 다시 호출할 수 있습니다. 캐시 파일이 깨져 있으면 없는 셈 치고 새로 호출합니다.

**왜 캐싱이 필요한가**: 외부 API 는 호출마다 돈·쿼터·시간이 듭니다. 리포트 형식만 고쳐 다시 뽑는
경우가 흔한데, 그때마다 LLM 과 지도 API 를 부를 이유가 없습니다. 이것이 "외부 API 비용·속도
최적화"의 가장 기본적인 형태입니다.

**보너스 1 — 복수 지역 추천**: 1단계가 대표 도시 외에 후보를 **2~3개** 함께 추천하고,
2단계가 지역마다 맛집을 찾고, 리포트가 지역별 섹션으로 정리합니다.

**필수 필드를 배열로 바꾸지 않고 나란히 둔 이유**: 미션 필수 스키마는 `recommended_city`(단수)입니다.
그걸 배열로 교체하면 보너스를 켜는 순간 필수 요구가 깨집니다. 그래서 `recommended_city`(대표 1개)는
그대로 두고 `recommended_cities`(후보 목록)를 **추가**했습니다 — 목록이 없어도 대표 도시 하나로
정상 동작합니다. **보너스는 확장이지 대체가 아닙니다.**

```
[1/3] 2026-09-15 여행지 추천 요청 중...
      추천: 강릉, 속초
[2/3] 2개 지역 맛집 검색 중...
      강릉: 5곳
      속초: 5곳
```

- **반복 처리**: `for city in cities:` 로 2단계를 돌립니다(목록의 첫 번째가 대표 도시). 한 지역이 실패해도 `continue` 없이
  다음 지역이 계속 돕니다 — 실패한 지역만 "데이터 없음"이 되고 나머지는 정상 출력됩니다.
- **결과 구조 설계**: 맛집을 평평한 리스트가 아니라 **`{도시: [아이템…]}` 딕셔너리**로 담습니다.
  리스트로 하면 "이 가게가 어느 도시 것인지"를 항목마다 다시 표시해야 하고, 지역별로 나눠 출력할 때
  매번 걸러내야 합니다. 도시를 키로 두면 `restaurants["속초"]` 한 줄로 꺼냅니다.
- **API 요청 관리**: 지역이 늘면 호출 수도 비례해 늘어납니다(2지역 = 2회). 그래서 도시 수를
  `MAX_CITIES = 3` 으로 제한하고, 캐싱(보너스 2)이 재실행 시 호출을 0으로 만듭니다.

---

## 제약 조건 준수

| 제약 | 어떻게 지켰나 |
|---|---|
| Python 3.10 이상 | 3.14 사용 |
| 터미널 실행(웹 UI 불필요) | `argparse` CLI |
| API 키를 코드/README/결과물에 직접 작성 금지 | 코드에는 **환경변수 이름만**, README·안내문에는 `YOUR_KEY` 자리표시자만 |
| `.env` 또는 환경변수 사용 | `config.load_dotenv()` — 환경변수가 있으면 그쪽이 우선 |
| 키 미설정 시 즉시 종료 + 안내 | `config.missing_key_message()` |
| 지도 API 실패 시에도 리포트 생성 | 맛집 = "데이터 없음", `errors` 에 사유 기록 |
| LLM JSON 파싱 실패 재시도 최대 1회 | `recommend.recommend()` 의 `for attempt in (1, 2)` |
| `try-except` 로 호출·파싱 오류 처리 | 각 단계에서 `HTTPError`·`URLError`·`JSONDecodeError` 구분 처리 |
| `results/` 에 날짜 기준 저장 | `results/YYYY-MM-DD.json` · `.md` |
| 외부 라이브러리 | 표준 라이브러리만(`urllib`·`json`·`argparse`·`datetime`). `.env` 로더도 직접 구현 |

---

## 코드 근거 — 어느 파일의 어느 부분이 무엇을 하나

아래는 이 저장소에 실제로 들어 있는 코드입니다. 설명만으로는 "정말 그렇게 짰는지" 알 수 없으므로,
평가·학습에 필요한 부분을 **원문 그대로** 옮겨 둡니다. 전체 코드는 각 `.py` 파일에 있습니다.

### 1. `-date` 옵션과 날짜 형식 검증 (`main.py`)

```python
def parse_date(text):
    """'YYYY-MM-DD' 문자열을 검증한다. 형식이 틀리면 ValueError."""
    return dt.datetime.strptime(text, "%Y-%m-%d").date()


def build_parser():
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="날짜를 주면 여행지를 추천받아 맛집까지 찾아 리포트를 만듭니다.",
        epilog='예) python main.py -date "2026-09-15"',
    )
    parser.add_argument("-date", required=True, help='여행 날짜 "YYYY-MM-DD"')
    parser.add_argument("--size", type=int, default=places.DEFAULT_SIZE, help="맛집 개수(기본 5)")
    parser.add_argument("--no-cache", action="store_true", help="저장 결과를 무시하고 다시 호출")
    return parser
```

형식이 틀리면 **파이프라인을 시작하지 않고** 사용법을 띄운 뒤 종료 코드 1 로 끝냅니다.

```python
    try:
        parse_date(args.date)
    except ValueError:
        print(f"[중단] 날짜 형식이 올바르지 않습니다: {args.date!r}", file=sys.stderr)
        build_parser().print_help(sys.stderr)
        return 1
```

`strptime` 을 쓴 이유: 정규식은 `2026-02-30` 처럼 "형식은 맞지만 존재하지 않는 날짜"를 통과시킵니다.

### 2. 1차 LLM 응답의 JSON 파싱과 필수 키 검증 (`recommend.py`)

```python
REQUIRED_KEYS = {
    "recommended_city": str,  # 대표 도시 1개 — 미션 필수 필드
    "weather": str,
    "events": list,
    "reason": str,
}


def parse_recommendation(text):
    cleaned = FENCE.sub("", text.strip())
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 파싱 실패: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("최상위가 객체(dict)가 아님")
    for key, expected in REQUIRED_KEYS.items():
        if key not in data:
            raise ValueError(f"필수 키 누락: {key}")
        if not isinstance(data[key], expected):
            raise ValueError(f"{key} 타입 불일치(기대 {expected.__name__})")
```

검증을 **키 존재 + 타입** 두 겹으로 둔 이유: `{"recommended_city": 123}` 같은 응답이 통과하면
2단계에서 엉뚱한 검색어로 API 를 부르고, 원인이 2단계에 있는 것처럼 보입니다.
`FENCE` 는 LLM 이 자주 붙이는 ` ```json ` 코드펜스를 벗기는 정규식입니다.

### 3. 1차 결과를 2단계 입력으로 넘기는 연결 (`main.py`)

```python
        main_city = recommendation["recommended_city"]  # 필수 필드 — 대표 도시
        cities = recommendation.get("recommended_cities") or [main_city]  # 보너스 — 후보 목록
        print(f"      추천: {main_city} (후보 {', '.join(cities)})", file=sys.stderr)

        print(f"[2/3] {len(cities)}개 지역 맛집 검색 중...", file=sys.stderr)
        restaurants = {}
        for city in cities:
            found = places.find_restaurants(map_key, city, errors, size=args.size)
            restaurants[city] = found
```

JSON 으로 받았기 때문에 `recommendation["recommended_city"]` **한 줄**로 이어집니다.
줄글로 받았다면 문장에서 지명을 잘라내는 코드가 필요하고, LLM 이 표현을 바꿀 때마다 깨집니다.

### 4. `results/` 저장 — 원본 JSON + 리포트 (`main.py`)

```python
def save_results(date_text, data, report_text):
    os.makedirs(config.RESULTS_DIR, exist_ok=True)
    json_path = os.path.join(config.RESULTS_DIR, f"{date_text}.json")
    md_path = os.path.join(config.RESULTS_DIR, f"{date_text}.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    return json_path, md_path
```

원본 JSON 을 같이 남기는 이유: 리포트 형식을 바꿔 다시 뽑을 때 API 를 다시 부르지 않아도 됩니다
(이 파일이 곧 보너스 2의 캐시입니다).

### 5. API 키를 코드에 두지 않는다 (`config.py`)

```python
# 이 프로그램이 쓰는 환경변수 이름들. 값이 아니라 **이름만** 코드에 있다.
LLM_KEY_NAME = "OPENAI_API_KEY"  # LLM(1단계) — OpenAI 계열
MAP_KEY_NAME = "KAKAO_REST_API_KEY"  # 지도/장소 검색(2단계) — Kakao Local


def get_key(name):
    """환경변수에서 키를 읽는다. 없으면 None(호출한 쪽이 안내 후 종료)."""
    value = os.environ.get(name, "").strip()
    return value or None
```

저장소 전체에서 키 **값**이 등장하는 곳은 없습니다. 안내문에도 `YOUR_KEY` 자리표시자만 씁니다.

### 6. 흐름을 함수·모듈로 나눈 방식 (`main.py` 가 순서만 담당)

```python
import config
import places
import recommend
import report
```

`main.py` 에는 HTTP 호출도, 문자열 조립도 없습니다. 세 단계를 **부르는 순서**와
"어디서 멈출지"만 있습니다. 그래서 실패했을 때 `main.py` 하나만 읽어도 어느 단계인지 보입니다.

| 파일 | 책임 | 밖으로 내보내는 것 |
|---|---|---|
| `config.py` | 키·경로 | `get_key` · `load_dotenv` · `missing_key_message` |
| `recommend.py` | 1단계 LLM | `recommend()` → dict 또는 None |
| `places.py` | 2단계 지도 | `find_restaurants()` → list(실패해도 빈 리스트) |
| `report.py` | 3단계 문서 | `build_report()` → str (순수 함수) |
| `main.py` | 순서·입출력 | 종료 코드 |

### 7·8. 지도 API 제공자를 바꿔도 리포트가 안 깨지는 이유 (`places.py`)

```python
def _to_item(doc):
    return {
        "name": doc.get("place_name", ""),
        "address": doc.get("road_address_name") or doc.get("address_name", ""),
        "category": doc.get("category_name", ""),
        "url": doc.get("place_url", ""),
        "lng": _to_float(doc.get("x")),  # x = 경도
        "lat": _to_float(doc.get("y")),  # y = 위도
    }
```

Kakao 응답 필드명(`place_name`·`x`·`y`)이 리포트까지 새지 않도록 **입구에서 한 번 옮깁니다**.
Naver Local 로 바꾸면 고칠 곳은 `search_places` 와 이 함수 두 개뿐이고, `report.py` 는 그대로입니다.
좌표는 Kakao 가 `x`=경도, `y`=위도로 주므로 뒤바꾸면 지도에 엉뚱한 곳이 찍힙니다.

### 9. 오류를 모아 리포트에 남기는 방식 (`places.py` · `report.py`)

```python
def find_restaurants(api_key, city, errors, size=DEFAULT_SIZE, timeout=30):
    try:
        items = search_places(api_key, city, size=size, timeout=timeout)
    except urllib.error.HTTPError as exc:
        errors.append(f"'{city}' 지도 API HTTP {exc.code}: {_hint(exc.code)}")
        return []
    except urllib.error.URLError as exc:
        errors.append(f"'{city}' 지도 API 네트워크 오류: {exc.reason}")
        return []
    except (json.JSONDecodeError, KeyError) as exc:
        errors.append(f"'{city}' 지도 API 응답 파싱 실패: {exc}")
        return []
    if not items:
        errors.append(f"'{city}' 맛집 검색 결과 0건")
    return items
```

각 단계는 예외를 **자기 자리에서** 문장으로 바꿔 `errors` 리스트에 넣고, 리포트가 마지막에 모아
보여줍니다. 화면에 흘려보내지 않는 이유: 산출물(`.md`)만 받은 사람도 무엇이 빠졌는지 알아야 합니다.

```python
    lines += ["## errors", ""]
    if errors:
        lines += [f"- {message}" for message in errors]
    else:
        lines.append("- 없음")
```

### 10. GET 과 POST 를 각각 어디에 썼나

```python
# places.py — 조회이므로 GET, 조건은 쿼리스트링에
    query = urllib.parse.urlencode({"query": f"{normalize_city(city)} 맛집", "size": size})
    request = urllib.request.Request(
        f"{KAKAO_URL}?{query}",
        headers={"Authorization": f"KakaoAK {api_key}"},
        method="GET",
    )
```

같은 프로그램 안에서도 목적이 다르면 방식이 갈립니다. 1단계는 긴 지시문을 보내야 하므로
POST 로 본문에 담습니다 — URL 길이 제한도 없고, 프롬프트가 접속 기록에 남지도 않습니다.

```python
# recommend.py — 긴 프롬프트를 보내야 하므로 POST, 본문은 JSON
    request = urllib.request.Request(
        OPENAI_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
```

인증 헤더 형식도 서비스마다 다릅니다 — Kakao 는 `KakaoAK <키>`, OpenAI 는 `Bearer <키>`.
둘 다 **헤더**에 넣고 URL 에는 넣지 않습니다(URL 은 접속 기록·로그에 그대로 남습니다).

### 11. 1차 프롬프트 설계 (`recommend.py`)

```python
    return f"""당신은 국내 여행 플래너다. 여행 날짜는 {date} 이다.

이 시기에 가기 좋은 국내 여행지 2~3곳을 추천하고, 결과를 **JSON 하나로만** 출력하라.

[출력 형식 — 이 5개 키를 반드시 포함]
- "recommended_city": 문자열. **대표** 도시 이름 하나 (예: "강릉")
- "recommended_cities": 문자열 배열. 대표 도시를 **첫 번째**로 포함한 2~3개
- "weather": 문자열. 그 시기의 일반적인 날씨 요약
- "events": 문자열 배열. 그 시기 행사·축제 후보 1~3개
- "reason": 문자열. 추천 근거 2~4문장 (왜 이 지역들인지)

[규칙]
- JSON 외의 설명·인사말·코드펜스를 붙이지 마라.
- 지명은 지도 검색이 가능한 실제 지명으로 쓴다.
"""
```

키 이름·타입·개수를 예시와 함께 못 박습니다. "지도 검색이 가능한 실제 지명" 이라는 한 줄이
2단계 실패를 크게 줄입니다 — 프롬프트가 **다음 단계의 제약**을 알고 있어야 합니다.

### 12. 401 / 403 이 떴을 때 무엇을 점검하나 (`recommend.py` · `places.py`)

```python
def _http_hint(code):
    hints = {
        401: "인증 실패. API 키 값·헤더 이름을 확인하세요",
        403: "권한 없음. 키의 사용 권한·결제 상태를 확인하세요",
        429: "요청 한도(쿼터) 초과. 잠시 후 재시도하거나 플랜을 확인하세요",
        500: "서버 오류. 잠시 후 재시도하세요",
    }
    return hints.get(code, "응답 코드를 확인하세요")
```

점검 순서는 **좁은 것부터**입니다: ① 키 값에 공백·따옴표가 섞였는가 → ② 헤더 이름·접두사가
맞는가(`Bearer` ‖ `KakaoAK`) → ③ 콘솔에서 그 키의 사용 권한·플랫폼 등록 → ④ 결제·쿼터 상태.
401 은 대개 ①②, 403 은 ③④ 입니다. 그래서 재시도 루프에서 이 둘은 **즉시 포기**합니다.

```python
            if exc.code in (401, 403):
                break  # 키 문제는 재시도해도 같다 — 즉시 포기
```

### 13. 환경변수 우선순위 (`config.py`)

```python
def load_dotenv(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
```

`if key not in os.environ` 한 줄이 우선순위를 정합니다 — **터미널에서 준 값이 `.env` 를 이깁니다.**
배포 환경에서 파일보다 환경변수가 우선인 관례와 같고, 임시로 다른 키를 써 볼 때 파일을 고치지
않아도 됩니다. 외부 라이브러리(python-dotenv) 없이 표준 라이브러리만으로 구현했습니다.

### 14. 재시도 전략 — 왜 1회이고, 두 번째는 무엇이 다른가 (`recommend.py`)

```python
def recommend(api_key, date, errors, timeout=60):
    for attempt in (1, 2):
        try:
            text = call_llm(api_key, build_prompt(date, retry=(attempt == 2)), timeout)
            return parse_recommendation(text)
        except urllib.error.HTTPError as exc:
            errors.append(f"LLM HTTP {exc.code} (시도 {attempt}회차): {_http_hint(exc.code)}")
            if exc.code in (401, 403):
                break
        except urllib.error.URLError as exc:
            errors.append(f"LLM 네트워크 오류(시도 {attempt}회차): {exc.reason}")
        except ValueError as exc:
            errors.append(f"LLM 응답 형식 오류(시도 {attempt}회차): {exc}")
    return None
```

**같은 프롬프트로 다시 부르지 않습니다.** 1차 실패는 대개 설명을 덧붙이다 JSON 이 깨진 경우라,
2회차는 형식만 강조한 짧은 지시로 바꿉니다:

```python
    if retry:
        return (
            f"{date} 여행지 추천. 아래 4개 키만 담은 JSON 하나만 출력하라. 설명·코드펜스 금지.\n"
            '{"recommended_city": "대표도시", "recommended_cities": ["대표도시", "도시2"], '
            '"weather": "날씨 요약", "events": ["행사1"], "reason": "추천 근거"}'
        )
```

1회로 제한한 이유: 무한 재시도는 쿼터를 태우고 사용자를 기다리게 합니다. 두 번 실패하면
프롬프트·모델 쪽 문제라 더 돌려도 같은 결과일 가능성이 높습니다.

### 15. 검색 결과가 0건일 때 (`report.py`)

```python
    for city in cities:
        found = restaurants.get(city) or []
        label = f"{city} (대표)" if city == main_city else city
        lines += [f"### {label}", ""]
        if found:
            lines.append("| 이름 | 주소 | 분류 | 링크 |")
            ...
        else:
            lines.append("데이터 없음 (검색 결과가 없거나 API 호출에 실패했습니다)")
```

**섹션을 지우지 않습니다.** 지워 버리면 읽는 사람은 "검색을 안 한 건지 결과가 없는 건지"
구분할 수 없습니다. 0건과 호출 실패의 구분은 `errors` 섹션이 담당합니다.

### 16. 캐싱 (보너스 2) (`main.py`)

```python
def load_cache(date_text):
    path = os.path.join(config.RESULTS_DIR, f"{date_text}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None  # 캐시가 깨졌으면 없는 셈 치고 새로 호출한다
```

같은 날짜로 다시 실행하면 API 를 **한 번도** 부르지 않습니다. 캐시 파일이 깨져 있으면 예외를
올리지 않고 "없는 셈" 치므로, 캐시 때문에 프로그램이 멈추는 일은 없습니다. `--no-cache` 로 무시.

### 17. 검색어 정규화 (`places.py`)

```python
CITY_ALIASES = {
    "제주도": "제주시",
    "울릉도": "울릉군",
    "여수시": "여수",
    "강원도 강릉": "강릉",
}


def normalize_city(city):
    cleaned = " ".join(str(city).split())
    return CITY_ALIASES.get(cleaned, cleaned)
```

1단계 LLM 은 "제주도"·"강원도 강릉" 처럼 **사람이 쓰는 표기**를 줍니다. 지도 API 는 행정구역
표기에 더 잘 맞습니다. 보정을 2단계 입구 한 곳에 두면 프롬프트를 건드리지 않고 검색 품질을
올릴 수 있고, 대응표만 늘리면 됩니다.

---

## 심층 인터뷰 대응 — 왜 그렇게 했고, 무엇을 포기했나

위 "코드 근거" 절이 **무엇을 했는지**라면, 여기는 **왜 그렇게 했고 무엇이 한계인지**입니다.
설계에는 항상 버린 선택지가 있고, 그 이유를 말할 수 있어야 다음에 바꿀 수 있습니다.

### Q1. 세 단계를 함수·모듈로 나눈 기준은? 호출 흐름을 끝까지 설명해 보라

나눈 기준은 **"바뀌는 이유가 다르면 다른 파일"** 입니다.

- `recommend.py` 는 LLM 제공자·프롬프트가 바뀔 때 바뀝니다.
- `places.py` 는 지도 제공자가 바뀔 때 바뀝니다.
- `report.py` 는 사람이 읽는 형식이 바뀔 때 바뀝니다.
- `config.py` 는 배포 환경이 바뀔 때 바뀝니다.

세 가지가 한 파일에 있으면 "리포트 표 모양을 고치려다 API 호출을 건드리는" 일이 생깁니다.

호출 흐름은 한 방향입니다(되돌아오는 화살표가 없습니다):

```
main.run()
  ├─ config.load_dotenv()            .env → os.environ (환경변수가 우선)
  ├─ config.get_key(LLM_KEY_NAME)    없으면 missing_key_message() 출력 후 return 1
  ├─ load_cache(date)                있으면 아래 두 단계를 통째로 건너뜀
  ├─ recommend.recommend(key, date, errors)
  │     └─ build_prompt → call_llm(POST) → parse_recommendation
  │          실패 시 build_prompt(retry=True) 로 1회 더 → 그래도 실패면 None
  ├─ (도시마다) places.find_restaurants(key, city, errors)
  │     └─ normalize_city → search_places(GET) → _to_item 정규화
  │          예외는 여기서 문장으로 바꿔 errors 에 넣고 [] 반환
  ├─ report.build_report(date, recommendation, restaurants, errors)   순수 함수
  └─ save_results(...)               results/<날짜>.json · .md
```

`errors` 리스트가 세 단계를 관통하는 유일한 공유 상태입니다. 각 단계는 **자기가 만든 실패만**
여기에 넣고, 남의 항목을 읽거나 지우지 않습니다.

### Q2. 왜 예외를 밖으로 던지지 않고 `errors` 리스트에 모으나? 그 방식의 대가는?

이 프로그램의 최종 산출물은 **리포트 한 장**입니다. 맛집 검색이 실패했다고 리포트를 안 주면
사용자에게 남는 게 없습니다. 그래서 2·3단계 실패는 "치명적이지 않은 실패"로 다루고,
**1단계 실패만 치명적**으로 봅니다(추천 도시가 없으면 검색할 대상 자체가 없습니다).

```python
        if recommendation is None:
            print("[중단] 여행지 추천에 실패했습니다. 사유:", file=sys.stderr)
            for message in errors:
                print(f"  - {message}", file=sys.stderr)
            return 1
```

**대가 세 가지**를 압니다.

1. 예외가 사라지므로 호출한 쪽이 "성공인지 부분 실패인지" 를 반환값만으로는 모릅니다.
   그래서 빈 리스트와 `errors` 항목을 **짝으로** 봐야 합니다.
2. `errors` 를 인자로 넘기는 방식은 함수가 밖의 리스트를 고치는 부수효과입니다.
   규모가 커지면 로깅 객체나 결과 래퍼(`Result` 타입)로 바꾸는 편이 낫습니다.
3. 실패가 조용히 쌓이므로 **리포트에 반드시 노출**해야 합니다 — 그래서 `errors` 섹션은
   비어 있어도 "- 없음" 을 찍고 지우지 않습니다.

### Q3. 제공자 교체를 위한 구조라는데, 실제로 Naver 로 바꾸면 무엇을 고치나?

고칠 곳은 `places.py` 안의 **두 함수뿐**입니다.

| 바꿔야 하는 것 | 위치 | Kakao → Naver |
|---|---|---|
| 요청 URL·인증 헤더 | `search_places` | `KakaoAK <키>` → `X-Naver-Client-Id`+`X-Naver-Client-Secret` 2개 |
| 응답 필드 이름 | `_to_item` | `place_name`→`title`, `x/y`→`mapx/mapy`(좌표계도 다름) |
| 응답 배열 키 | `search_places` | `documents` → `items` |

`report.py`·`main.py` 는 한 글자도 안 바뀝니다. **경계를 `_to_item` 한 곳에 세웠기 때문**입니다.

이 구조의 이름은 흔히 어댑터(adapter)라고 부릅니다. 다만 지금은 제공자가 하나뿐이라
**추상 클래스나 인터페이스를 만들지 않았습니다** — 구현체가 하나일 때 인터페이스를 먼저
만드는 것은 대개 이른 추상화입니다. 두 번째 제공자가 실제로 생기는 시점에
`search(city) -> list[item]` 시그니처를 공통으로 뽑는 것이 맞는 순서라고 봅니다.

### Q4. GET 과 POST 를 나눈 기준을 기술적으로 더 설명하라

| | GET (2단계 지도) | POST (1단계 LLM) |
|---|---|---|
| 의미 | 조회 — 서버 상태를 바꾸지 않는다 | 처리 요청 — 서버가 무언가를 만든다 |
| 데이터 위치 | URL 쿼리스트링 | 요청 본문(body) |
| 길이 제한 | 사실상 있다(URL 길이) | 사실상 없다 |
| 캐시·재시도 | 안전하다(같은 URL = 같은 결과) | 안전하지 않다(같은 요청이 두 번 처리될 수 있다) |
| 기록에 남는가 | URL 이 접속 로그·브라우저 기록에 남는다 | 본문은 보통 안 남는다 |

이 프로그램에서 갈린 이유는 **길이와 기록** 입니다. 프롬프트는 수백 자라 URL 에 넣기 부적절하고,
사용자 질의가 서버 접속 로그에 그대로 남는 것도 바람직하지 않습니다. 반대로 맛집 검색은
조건이 짧고, "같은 도시 = 같은 결과" 라서 GET 이 맞습니다.

멱등성(idempotent) 관점도 있습니다 — GET 은 여러 번 불러도 안전하므로 재시도 로직을 넣기 쉽고,
POST 는 그렇지 않아 1단계 재시도를 **1회로 못 박았습니다**.

### Q5. LLM 출력을 JSON 으로 강제한 이유를 "연동" 관점에서 설명하라

핵심은 **다음 단계가 사람이 아니라 프로그램**이라는 점입니다.

자유 텍스트로 받으면 `"이번 가을에는 강릉이 좋겠습니다"` 에서 `강릉` 을 잘라내야 하고, 그 코드는
다음 세 가지에 전부 깨집니다: ① LLM 이 문장을 바꿀 때 ② 도시가 두 개일 때 ③ 존댓말·수식어가
붙을 때. 즉 **결합이 문장 표현에 걸립니다.**

JSON 으로 받으면 결합이 **키 이름**에 걸립니다. 키는 우리가 프롬프트에서 정한 약속이라,
LLM 이 표현을 바꿔도 `data["recommended_city"]` 는 그대로 동작합니다. 계약이 명시적이 되는 셈이고,
그래서 `REQUIRED_KEYS` 로 **계약 위반을 입구에서 검사**할 수 있습니다.

부수 효과도 있습니다 — 검증 지점이 생기므로 실패를 1단계에서 잡습니다. 자유 텍스트였다면
잘라내기가 실패해도 빈 문자열이 조용히 흘러가 2단계에서 엉뚱한 검색을 합니다.

### Q6. 401 / 403 이 났을 때 실제로 무엇을 어떤 순서로 하나

원인부터 나눕니다. **401 = "당신이 누구인지 모르겠다"(인증), 403 = "누군지는 알겠는데 권한이
없다"(인가).** 그래서 점검 대상이 다릅니다.

| 순서 | 무엇을 | 어떻게 확인 | 주로 걸리는 코드 |
|---|---|---|---|
| 1 | 키가 실제로 실렸는가 | `python -c "import os;print(bool(os.environ.get('KAKAO_REST_API_KEY')))"` | 401 |
| 2 | 키 값에 공백·따옴표가 섞였나 | `.env` 줄 끝 공백, `"` 포함 여부 | 401 |
| 3 | 헤더 이름·접두사가 맞나 | Kakao `KakaoAK `, OpenAI `Bearer ` (접두사 뒤 공백 1칸) | 401 |
| 4 | 키 종류가 맞나 | Kakao 는 REST API 키(JavaScript 키 아님) | 401·403 |
| 5 | 콘솔에서 권한·플랫폼 등록 | 앱 설정에서 해당 API 사용 on, 도메인 등록 | 403 |
| 6 | 결제·쿼터 상태 | 카드 등록, 무료 한도 소진 여부 | 403·429 |

실제 순서를 이렇게 잡은 이유는 **확인 비용이 싼 것부터**이기 때문입니다. 1~3은 터미널에서
몇 초면 끝나고, 5~6은 콘솔에 들어가야 합니다. 경험상 401 의 대부분은 2번(줄 끝 공백)입니다.

그래서 코드는 401·403 에서 재시도하지 않고 즉시 포기합니다 — **사람이 설정을 고치기 전에는
몇 번을 불러도 같은 응답**이고, 재시도는 쿼터만 태웁니다.

### Q7. `.env`/환경변수를 쓰는 이유를 보안뿐 아니라 운영 관점에서 설명하라

**보안**: 코드는 저장소에 올라가고, 저장소는 복제·포크·검색됩니다. 공개 저장소에 올라간 키는
자동 수집기에 수 분 내로 잡힙니다. `.env` 를 `.gitignore` 에 넣는 것은 "실수해도 안 올라가게"
하는 장치입니다.

**운영**: 같은 코드가 여러 환경에서 돌아야 합니다.

| 환경 | 키를 어디서 주나 |
|---|---|
| 내 노트북 | `.env` 파일 |
| 동료 노트북 | 각자의 `.env`(값이 다름) |
| CI / 자동화 | 저장소 시크릿 → 환경변수로 주입 |
| 서버 배포 | 컨테이너·서비스 설정의 환경변수 |

**코드는 넷 다 동일**합니다. 키를 코드에 적으면 환경 수만큼 코드가 갈라지고, 키를 교체할 때마다
커밋이 필요합니다. 반대로 지금 구조는 키 교체가 **배포 없이** 끝납니다.

형상 관리 관점에서 하나 더 — `.env.example` 처럼 **키 이름만 담긴 파일**은 커밋해도 됩니다.
새 사람이 무엇을 채워야 하는지 알 수 있고, 값은 없으니 위험하지 않습니다.

### Q8. 파싱 전략을 더 설명하라. 왜 LLM 이 JSON 을 깨뜨리며, 무엇을 방어했나

깨지는 원인은 대체로 셋입니다.

1. **코드펜스** — ` ```json ` 으로 감싸서 보냅니다. 가장 흔합니다.
2. **덧말** — "아래와 같습니다:" 같은 문장을 앞뒤에 붙입니다.
3. **진짜 깨진 JSON** — 따옴표·쉼표 누락. 드물지만 있습니다.

1번은 `FENCE` 정규식으로 벗기고, 2·3번은 재시도 프롬프트로 대응합니다. 재시도 프롬프트는
길이를 크게 줄이고 예시 JSON 을 통째로 보여줍니다 — **설명할 여지를 없애면 덧말도 줄어듭니다.**

의도적으로 **하지 않은** 방어도 적어 둡니다.

- 텍스트에서 `{` 부터 `}` 까지 잘라내는 방식: 중첩 괄호·문자열 안 괄호에서 틀립니다.
  지금 데이터 구조에서는 동작하겠지만, 조용히 틀리는 코드보다 명확히 실패하는 편이 낫습니다.
- 정규식으로 키를 하나씩 긁어내는 방식: JSON 을 안 쓰는 것과 같아집니다(Q5 의 결합 문제 재발).
- 3회 이상 재시도: 쿼터·대기시간 대비 성공률이 낮습니다.

더 큰 규모라면 제공자의 구조화 출력 기능(JSON mode / response_format)이 정답입니다.
이 미션은 표준 라이브러리 범위를 지키려고 프롬프트 강제 + 검증으로 풀었습니다.

### Q9. 검색 0건일 때의 표기 정책이 왜 사용자에게 유용한가

리포트를 받는 사람이 궁금한 것은 "맛집이 없다" 가 아니라 **"내가 뭘 해야 하나"** 입니다.
그래서 세 가지를 구분해서 보여줍니다.

| 상황 | 리포트에 나타나는 모습 | 사용자가 할 일 |
|---|---|---|
| 결과 있음 | 표에 목록 | 없음 |
| 결과 0건 | "데이터 없음" + errors 에 `'속초' 맛집 검색 결과 0건` | 검색어를 좁히거나 인근 도시로 |
| 호출 실패 | "데이터 없음" + errors 에 `HTTP 401 …` | 키·권한을 고친다 |

섹션 자체를 지우면 두 번째와 세 번째가 **구분되지 않을 뿐 아니라**, 애초에 검색을 시도했는지도
알 수 없습니다. 빈 자리를 남겨 두는 것이 "여기까지는 확인했다" 는 정보가 됩니다.
일정 제안도 같은 이유로 맛집 없이 생성합니다 — 뼈대는 데이터 유무와 무관해야 합니다.

### Q10. 캐싱의 무효화 전략과 한계는?

지금 캐시 키는 **날짜 하나**이고, 무효화 수단은 `--no-cache` **수동 하나**입니다.
이 단순함은 의도한 것이지만 한계가 분명합니다.

| 한계 | 언제 문제가 되나 | 대응 |
|---|---|---|
| 만료가 없다 | 어제 뽑은 리포트를 오늘도 그대로 씀 | 파일 mtime 이 N일 지나면 무시 |
| 옵션이 키에 없다 | `--size 5` 로 만든 캐시를 `--size 20` 이 재사용 | 캐시 키를 `날짜+옵션 해시` 로 |
| 부분 실패도 캐시된다 | 401 로 맛집이 빈 결과가 그대로 굳음 | `errors` 가 비어 있을 때만 저장 |
| 프롬프트 변경을 모른다 | 프롬프트를 고쳐도 옛 결과가 나옴 | 캐시 키에 프롬프트 버전 포함 |

고칠 위치는 **`load_cache` 와 `save_results` 두 곳**입니다. 세 번째 항목은 특히 실전에서 먼저
아프기 때문에, 규모가 커지면 "성공한 결과만 캐시" 를 가장 먼저 넣겠습니다.

### Q11. 추천 도시가 "광역시/도" 처럼 넓게 나오면? 정규화 전략을 더 일반적으로

지금 구현한 `CITY_ALIASES` 는 **대응표 방식**이라 정확하지만 아는 만큼만 고칩니다.
넓은 지명 문제는 층을 나눠 대응하는 것이 맞습니다.

1. **표기 정리**(구현함) — 공백·군더더기 제거, 별칭 치환. 비용 0, 예측 가능.
2. **행정구역 축소**(다음 단계) — "경기도" 처럼 시/군을 포함하는 광역 단위면 대표 도시로
   내린다. `"경상북도" → "경주시"` 같은 대응표를 한 단계 더 두거나, 1단계 프롬프트에
   "시/군 단위로 답하라"를 넣어 애초에 넓게 안 나오게 한다.
3. **질의 분해**(더 큰 규모) — "부산 맛집" 대신 `부산 서면 맛집`·`부산 해운대 맛집` 처럼
   구/동 단위로 여러 번 검색해 합친다. 호출 수가 늘지만 결과 품질이 크게 오른다.
4. **좌표 기반 검색**(정공법) — 지명을 좌표로 바꾼 뒤(geocoding) 반경 검색을 쓴다.
   "넓은 지명" 문제가 반경 파라미터로 바뀌므로 표기 흔들림에서 자유롭다.

지금 1번만 넣은 이유는 **미션 범위(표준 라이브러리·API 2개)** 안에서 비용 대비 효과가 가장
크기 때문입니다. 실제 서비스라면 4번이 정답이고, `places.py` 에 `_geocode(city)` 를 추가해
`search_places` 가 좌표를 받도록 바꾸면 됩니다.

---

## 준비물 (전제 지식 0)

| 확인 항목 | 없으면 |
|---|---|
| Python 3.10 이상 | [python.org](https://www.python.org/downloads/) 에서 설치("Add to PATH" 체크) |
| Git | [git-scm.com](https://git-scm.com/) |
| OpenAI API 키 | platform.openai.com 가입 후 발급(유료 — 소액 충전 필요) |
| Kakao REST API 키 | developers.kakao.com 에서 앱 생성 후 발급(무료) |
| 터미널 사용 | 아래 "따라 하기" 를 그대로 치면 됩니다 |

**키가 없어도** `python demo_offline.py` 로 리포트 생성 단계는 확인할 수 있습니다.
설치할 파이썬 패키지는 없습니다(표준 라이브러리만 사용).

## 용어 사전

| 용어 | 뜻 (이 문서에서) |
|---|---|
| **API** | 프로그램끼리 대화하는 규격. "이 주소로 이렇게 물으면 이렇게 답한다"는 약속 |
| **REST API** | 웹 주소(URL)와 HTTP 메서드로 요청하는 방식의 API |
| **엔드포인트** | API 의 특정 기능에 해당하는 주소 (예: `.../search/keyword.json`) |
| **GET / POST** | 읽기 요청 / 보내기 요청. 위 §REST API 절 참고 |
| **헤더(header)** | 요청에 붙이는 부가 정보. 인증 키·데이터 형식 등을 담는다 |
| **쿼리스트링** | URL 뒤 `?key=value&…` 부분. GET 요청의 조건을 담는다 |
| **JSON** | `{"키": "값"}` 형태의 데이터 표기법. 사람도 읽고 프로그램도 읽는다 |
| **파싱(parsing)** | 글자 덩어리를 프로그램이 쓸 수 있는 구조로 바꾸는 일 |
| **환경변수** | 운영체제가 들고 있는 이름-값 쌍. 프로그램이 읽을 수 있고 코드에는 안 적힌다 |
| **`.env`** | 환경변수를 적어 두는 파일. 저장소에 올리지 않는다 |
| **쿼터(quota)** | 정해진 기간에 쓸 수 있는 요청 한도 |
| **타임아웃** | 응답을 기다리는 최대 시간. 넘으면 실패로 친다 |
| **캐싱** | 한 번 받은 결과를 저장해 두고 다시 쓰는 것 |
| **자리표시자(placeholder)** | 실제 값 대신 넣어 둔 예시 문구 (`YOUR_KEY` 등) |

## 따라 하기

API 를 처음 써도 이 순서대로 하면 됩니다.

1. **키 없이 먼저 돌려 보기** — `python demo_offline.py`. 리포트가 어떻게 생겼는지 봅니다.
   여기까지는 인터넷·키가 필요 없습니다.
2. **Kakao 키 발급** — developers.kakao.com 로그인 → "내 애플리케이션" → 앱 만들기 →
   "앱 키" 탭의 **REST API 키**를 복사합니다(무료).
3. **OpenAI 키 발급** — platform.openai.com → API keys → Create new secret key.
   **이때 한 번만 보이므로 바로 복사**하세요(유료, 소액 충전 필요).
4. **`.env` 만들기** — `cp .env.example .env` 후 편집기로 열어 `YOUR_KEY` 를 실제 키로 바꿉니다.
   **따옴표 없이** 값만 넣습니다.
5. **잘못된 날짜로 먼저 실행** — `python main.py -date 2026-13-99`.
   사용법이 나오면 입력 검증이 동작하는 것입니다.
6. **정상 실행** — `python main.py -date "2026-09-15"`. 단계별 진행 메시지가 뜨고
   `results/` 폴더에 파일 2개가 생깁니다.
7. **캐시 확인** — 같은 명령을 한 번 더 칩니다. `[캐시] … 재사용` 이 뜨고 즉시 끝납니다.
8. **일부러 실패시켜 보기** — `.env` 의 `KAKAO_REST_API_KEY` 값을 아무 글자로 바꾸고 실행합니다.
   맛집이 "데이터 없음"이 되지만 **리포트는 그대로 나오고** `errors` 에 401 사유가 남습니다.
   이것이 "부분 실패에도 산출물을 낸다"는 설계입니다.
9. **직접 고쳐 보기** — 맛집 개수를 바꾸려면 `--size 10`, 리포트 항목을 바꾸려면
   `report.py` 의 `build_report()` 만 열면 됩니다.
