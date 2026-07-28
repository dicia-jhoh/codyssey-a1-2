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
    "recommended_city": "강릉",
    "weather": "9월 중순 강릉은 낮 23~26도로 선선하고 습도가 낮아 해안 산책에 좋습니다.",
    "events": ["강릉커피축제(가을 시즌)", "정동진 해변 야간 조명"],
    "reason": (
        "여름 성수기가 지나 숙소·해변이 한산해집니다. 바다와 커피거리를 하루에 묶을 수 있어 "
        "1일 일정으로 밀도가 높고, KTX 로 서울에서 2시간이면 닿아 이동 부담이 적습니다."
    ),
}

SAMPLE_RESTAURANTS = [
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
]


def main():
    date = "demo-2026-09-15"

    print("== 사례 1: 정상(맛집 2곳) ==")
    text = report.build_report(date, SAMPLE_RECOMMENDATION, SAMPLE_RESTAURANTS, [])
    print(text)

    print("\n== 사례 2: 맛집 0건 + 오류 발생(리포트는 계속 생성된다) ==")
    text_empty = report.build_report(
        date,
        SAMPLE_RECOMMENDATION,
        [],
        ["지도 API HTTP 401: 인증 실패. REST API 키 값·헤더 형식을 확인하세요"],
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
