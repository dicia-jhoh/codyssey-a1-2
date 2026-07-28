"""API 키 없이 리포트 생성 단계만 확인하는 데모.

실행: python demo_offline.py

왜 필요한가: 3단계(리포트)는 순수 함수라 네트워크 없이도 돌릴 수 있다. 채점자·학습자가
키를 발급받지 않고도 **산출물 형태**를 볼 수 있어야 한다. 여기 쓰는 데이터는 실제 API 응답과
같은 구조의 예시값이며, 실행하면 `results/demo-*.md` 가 생긴다.
"""

from __future__ import annotations

import json
import os

import config
import report

SAMPLE_RECOMMENDATION = {
    "recommended_cities": ["강릉", "속초"],
    "weather": "9월 중순 강릉은 낮 23~26도로 선선하고 습도가 낮아 해안 산책에 좋습니다.",
    "events": ["강릉커피축제(가을 시즌)", "정동진 해변 야간 조명"],
    "reason": (
        "여름 성수기가 지나 숙소·해변이 한산해집니다. 강릉은 바다와 커피거리를 하루에 묶을 수 있고, "
        "속초는 설악산 초입 단풍이 시작돼 성격이 다른 하루를 고를 수 있습니다. "
        "두 도시 모두 KTX·고속버스로 서울에서 2~3시간이면 닿습니다."
    ),
}

SAMPLE_RESTAURANTS = {
    "강릉": [
        {
            "name": "초당순두부마을",
            "address": "강원 강릉시 초당순두부길 30",
            "category": "음식점 > 한식 > 두부요리",
            "url": "https://place.map.kakao.com/00000001",
            "lng": 128.8961,
            "lat": 37.7952,
        },
        {
            "name": "강릉 회센터",
            "address": "강원 강릉시 창해로 100",
            "category": "음식점 > 일식 > 회",
            "url": "https://place.map.kakao.com/00000002",
            "lng": 128.9512,
            "lat": 37.7712,
        },
    ],
    "속초": [
        {
            "name": "속초 중앙시장 닭강정",
            "address": "강원 속초시 중앙로147번길 12",
            "category": "음식점 > 간식 > 닭강정",
            "url": "https://place.map.kakao.com/00000003",
            "lng": 128.5918,
            "lat": 38.2070,
        },
    ],
}


def main():
    date = "demo-2026-09-15"

    print("== 사례 1: 정상(2개 지역, 맛집 3곳) ==")
    text = report.build_report(date, SAMPLE_RECOMMENDATION, SAMPLE_RESTAURANTS, [])
    print(text)

    print("\n== 사례 2: 한 지역만 실패(나머지는 그대로 나온다) ==")
    text_empty = report.build_report(
        date,
        SAMPLE_RECOMMENDATION,
        {"강릉": SAMPLE_RESTAURANTS["강릉"], "속초": []},
        ["'속초' 지도 API HTTP 401: 인증 실패. REST API 키 값·헤더 형식을 확인하세요"],
    )
    print(text_empty)

    os.makedirs(config.RESULTS_DIR, exist_ok=True)
    with open(f"{config.RESULTS_DIR}/{date}.md", "w", encoding="utf-8") as f:
        f.write(text)
    with open(f"{config.RESULTS_DIR}/{date}.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "date": date,
                "recommendation": SAMPLE_RECOMMENDATION,
                "restaurants": SAMPLE_RESTAURANTS,
                "errors": [],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"\n저장: {config.RESULTS_DIR}/{date}.md · {config.RESULTS_DIR}/{date}.json")


if __name__ == "__main__":
    main()
