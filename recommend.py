"""1단계 — LLM 에게 여행지를 추천받아 **JSON 으로** 돌려받는다.

왜 JSON 인가: 다음 단계(맛집 검색)가 `recommended_city` 값을 **프로그램이 읽어서** 써야 한다.
줄글로 받으면 "제주도가 좋겠습니다"에서 도시 이름을 잘라내는 코드를 따로 짜야 하고,
LLM 이 표현을 바꿀 때마다 그 코드가 깨진다. 출력 형식을 고정하는 것이 연결의 핵심이다.

⚠ 이 미션은 날씨·행사의 **정확도**를 평가하지 않는다. 중요한 것은 "구조화된 출력"과
"다음 단계 입력으로의 연결"이다.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4o-mini"

# 응답에서 ```json … ``` 코드펜스를 벗기기 위한 패턴. LLM 이 펜스를 붙이는 일이 잦다.
FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$")

# 1차 추천 JSON 의 필수 키와 타입 — 검증의 기준이 되는 단일 출처.
REQUIRED_KEYS = {
    "recommended_city": str,
    "weather": str,
    "events": list,
    "reason": str,
}


def build_prompt(date, retry=False):
    """LLM 에 보낼 지시문을 만든다. retry=True 면 "키만 다시 JSON 으로" 로 좁힌다.

    재시도 프롬프트를 따로 두는 이유: 1차 실패는 보통 설명을 덧붙이다 JSON 이 깨진 경우다.
    같은 프롬프트로 다시 부르면 같은 실수를 반복하므로, **형식만 강조한 짧은 지시**로 바꾼다.
    """
    if retry:
        return (
            f"{date} 여행지 추천. 아래 4개 키만 담은 JSON 하나만 출력하라. 설명·코드펜스 금지.\n"
            '{"recommended_city": "도시명", "weather": "날씨 요약", '
            '"events": ["행사1"], "reason": "추천 근거"}'
        )
    return f"""당신은 국내 여행 플래너다. 여행 날짜는 {date} 이다.

이 시기에 가기 좋은 국내 여행지 한 곳을 추천하고, 결과를 **JSON 하나로만** 출력하라.

[출력 형식 — 이 4개 키를 반드시 포함]
- "recommended_city": 문자열. 도시/지역 이름 하나 (예: "제주", "강릉")
- "weather": 문자열. 그 시기의 일반적인 날씨 요약
- "events": 문자열 배열. 그 시기 행사·축제 후보 1~3개
- "reason": 문자열. 추천 근거 2~4문장

[규칙]
- JSON 외의 설명·인사말·코드펜스를 붙이지 마라.
- 지명은 지도 검색이 가능한 실제 지명으로 쓴다.
"""


def call_llm(api_key, prompt, timeout=60):
    """OpenAI Chat Completions 호출 → 응답 텍스트.

    HTTP 요청 구조: **POST** 로 본문(JSON)을 보내고 응답(JSON)을 받는다.
    인증은 `Authorization: Bearer <키>` 헤더 — 키를 URL 에 넣지 않는다(로그·기록에 남으므로).
    """
    body = json.dumps(
        {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        OPENAI_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload["choices"][0]["message"]["content"]


def parse_recommendation(text):
    """LLM 응답 텍스트 → dict. 형식이 틀리면 ValueError.

    검증을 두 단계로 한다: ① JSON 으로 읽히는가 ② 필수 키가 올바른 타입으로 있는가.
    ②를 빼면 `{"city": "제주"}` 같은 응답이 통과해 다음 단계에서 KeyError 로 죽는다 —
    **문제를 만든 곳에서 잡아야** 원인 추적이 쉽다.
    """
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
    data["events"] = [str(e) for e in data["events"]]
    return data


def recommend(api_key, date, errors, timeout=60):
    """1단계 전체 — 호출 → 파싱, 실패 시 **재시도 1회**. 최종 실패면 None.

    재시도를 1회로 제한한 이유: 무한 재시도는 쿼터를 태우고 사용자를 기다리게 한다.
    두 번 실패하면 프롬프트나 모델 쪽 문제라 더 돌려도 같은 결과일 가능성이 높다.
    실패 사유는 errors 리스트에 쌓아 리포트 `errors` 섹션에 남긴다.
    """
    for attempt in (1, 2):
        try:
            text = call_llm(api_key, build_prompt(date, retry=(attempt == 2)), timeout)
            return parse_recommendation(text)
        except urllib.error.HTTPError as exc:
            # 401/403=키·권한, 429=쿼터 초과, 5xx=서버 — 상태코드로 원인이 갈린다.
            errors.append(f"LLM HTTP {exc.code} (시도 {attempt}회차): {_http_hint(exc.code)}")
            if exc.code in (401, 403):
                break  # 키 문제는 재시도해도 같다 — 즉시 포기
        except urllib.error.URLError as exc:
            errors.append(f"LLM 네트워크 오류(시도 {attempt}회차): {exc.reason}")
        except ValueError as exc:
            errors.append(f"LLM 응답 형식 오류(시도 {attempt}회차): {exc}")
    return None


def _http_hint(code):
    """상태코드별 대응 안내 — 무엇을 점검해야 하는지."""
    hints = {
        401: "인증 실패. API 키 값·헤더 이름을 확인하세요",
        403: "권한 없음. 키의 사용 권한·결제 상태를 확인하세요",
        429: "요청 한도(쿼터) 초과. 잠시 후 재시도하거나 플랜을 확인하세요",
        500: "서버 오류. 잠시 후 재시도하세요",
    }
    return hints.get(code, "응답 코드를 확인하세요")
