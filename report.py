"""3단계 — 앞 두 단계 결과를 합쳐 여행 리포트(Markdown)를 만든다.

입력: 1차 추천 JSON + 맛집 목록(0건일 수 있음) + 오류 목록(빈 리스트일 수 있음).
출력: 사람이 읽는 Markdown 텍스트.

**맛집이 0건이어도 리포트는 나온다** — 그 자리에 "데이터 없음"을 적는다.
빈 섹션을 지워버리면 사용자는 "검색을 안 한 건지 결과가 없는 건지" 알 수 없다.
"""

from __future__ import annotations


def build_report(date, recommendation, restaurants, errors):
    """리포트 Markdown 문자열을 만든다(순수 함수 — 파일·네트워크를 건드리지 않는다).

    순수 함수로 둔 이유: 입력만 주면 결과가 정해지므로 API 없이도 테스트할 수 있다.
    """
    city = recommendation.get("recommended_city", "미상")
    lines = [
        f"# {date} 여행 리포트 — {city}",
        "",
        "## 추천 지역과 이유",
        "",
        f"**{city}**",
        "",
        recommendation.get("reason", "(추천 근거 없음)"),
        "",
        "## 날씨",
        "",
        recommendation.get("weather", "(날씨 정보 없음)"),
        "",
        "## 행사·축제",
        "",
    ]

    events = recommendation.get("events") or []
    if events:
        lines += [f"- {event}" for event in events]
    else:
        lines.append("- 데이터 없음")
    lines += ["", "## 맛집", ""]

    if restaurants:
        lines.append("| 이름 | 주소 | 분류 | 링크 |")
        lines.append("|---|---|---|---|")
        for place in restaurants:
            url = place.get("url") or ""
            link = f"[지도]({url})" if url else "-"
            lines.append(
                f"| {place.get('name', '')} | {place.get('address', '')} "
                f"| {_short_category(place.get('category', ''))} | {link} |"
            )
    else:
        lines.append("데이터 없음 (검색 결과가 없거나 API 호출에 실패했습니다)")

    lines += ["", "## 1일 일정 제안", ""]
    lines += _build_schedule(city, restaurants)

    lines += ["", "## errors", ""]
    if errors:
        lines += [f"- {message}" for message in errors]
    else:
        lines.append("- 없음")
    lines.append("")
    return "\n".join(lines)


def _short_category(category):
    """'음식점 > 한식 > 국밥' → '국밥'. 표가 가로로 길어지는 것을 막는다."""
    parts = [p.strip() for p in category.split(">") if p.strip()]
    return parts[-1] if parts else "-"


def _build_schedule(city, restaurants):
    """오전·오후·저녁 3단 일정. 맛집이 있으면 실제 상호를 끼워 넣는다.

    맛집이 없어도 일정 자체는 만든다 — 리포트의 뼈대는 데이터 유무와 무관해야 한다.
    """
    lunch = restaurants[0]["name"] if len(restaurants) >= 1 else "현지 맛집"
    dinner = restaurants[1]["name"] if len(restaurants) >= 2 else "현지 맛집"
    return [
        f"- **오전**: {city} 도착, 대표 명소 한 곳 둘러보기",
        f"- **오후**: 점심({lunch}) 후 시내·해안 산책, 카페 휴식",
        f"- **저녁**: 저녁 식사({dinner}) 후 야경 스팟 방문",
    ]
