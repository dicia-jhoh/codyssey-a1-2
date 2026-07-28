"""2단계 — 1단계가 고른 도시로 맛집을 검색한다 (Kakao Local API).

**이 단계가 실패해도 프로그램은 멈추지 않는다.** 맛집을 "데이터 없음"으로 두고 3단계(리포트)로
넘어간다. 이유: 사용자가 원하는 최종 산출물은 리포트이고, 맛집은 그 일부다.
부분 실패로 전체를 버리면 남는 게 없다.

1단계와의 연결: `recommend()` 가 돌려준 dict 의 `recommended_city` 값이 여기 검색어가 된다.
JSON 으로 받았기 때문에 문자열 파싱 없이 `data["recommended_city"]` 한 줄로 이어진다.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

KAKAO_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
DEFAULT_SIZE = 5  # 권장 5곳


def search_places(api_key, city, size=DEFAULT_SIZE, timeout=30):
    """도시명으로 맛집 검색 → 아이템 리스트. 호출 실패는 예외로 올린다(호출자가 처리).

    HTTP 요청 구조: **GET** 으로 질의를 URL 쿼리스트링에 실어 보낸다.
    (POST 와 차이 — GET 은 "읽기", 조건이 URL 에 드러나고 캐시·북마크가 가능하다.
     POST 는 "보내기", 본문에 데이터를 담아 길거나 민감한 값에 쓴다.)
    인증은 `Authorization: KakaoAK <키>` 헤더. 401/403 이면 키 값·헤더 이름·도메인 설정을 점검한다.
    """
    query = urllib.parse.urlencode({"query": f"{city} 맛집", "size": size})
    request = urllib.request.Request(
        f"{KAKAO_URL}?{query}",
        headers={"Authorization": f"KakaoAK {api_key}"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return [_to_item(doc) for doc in payload.get("documents", [])]


def _to_item(doc):
    """Kakao 응답 1건 → 우리 형식으로 정규화.

    응답 필드 이름을 그대로 쓰지 않고 한 번 옮기는 이유: 나중에 Naver Local 로 바꿔도
    이 함수만 고치면 리포트 코드는 그대로다(제공자 이름이 리포트까지 새지 않는다).
    좌표는 Kakao 가 x=경도(lng), y=위도(lat) 로 준다 — 뒤바꾸면 지도에 엉뚱한 곳이 찍힌다.
    """
    return {
        "name": doc.get("place_name", ""),
        "address": doc.get("road_address_name") or doc.get("address_name", ""),
        "category": doc.get("category_name", ""),
        "url": doc.get("place_url", ""),
        "lng": _to_float(doc.get("x")),  # x = 경도
        "lat": _to_float(doc.get("y")),  # y = 위도
    }


def _to_float(value):
    """문자열 좌표를 숫자로. 값이 없거나 숫자가 아니면 None(리포트에서 좌표 생략)."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def find_restaurants(api_key, city, errors, size=DEFAULT_SIZE, timeout=30):
    """2단계 전체 — 실패해도 예외를 밖으로 내보내지 않고 **빈 리스트**를 돌려준다.

    검색 결과가 0건인 경우와 호출이 실패한 경우를 둘 다 빈 리스트로 처리하되,
    실패는 errors 에 사유를 남겨 리포트에서 구분할 수 있게 한다
    (0건 = 그 지역에 결과가 없음 / 실패 = 우리 쪽 문제).
    """
    try:
        items = search_places(api_key, city, size=size, timeout=timeout)
    except urllib.error.HTTPError as exc:
        errors.append(f"지도 API HTTP {exc.code}: {_hint(exc.code)}")
        return []
    except urllib.error.URLError as exc:
        errors.append(f"지도 API 네트워크 오류: {exc.reason}")
        return []
    except (json.JSONDecodeError, KeyError) as exc:
        errors.append(f"지도 API 응답 파싱 실패: {exc}")
        return []
    if not items:
        errors.append(f"'{city}' 맛집 검색 결과 0건")
    return items


def _hint(code):
    hints = {
        401: "인증 실패. REST API 키 값과 헤더 형식('KakaoAK <키>')을 확인하세요",
        403: "권한 없음. 앱 설정의 플랫폼(도메인) 등록과 API 사용 권한을 확인하세요",
        429: "요청 한도 초과. 잠시 후 재시도하세요",
    }
    return hints.get(code, "응답 코드를 확인하세요")
