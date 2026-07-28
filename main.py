"""여행 추천 파이프라인 — 시작 지점.

실행: python main.py -date 2026-09-15

3단 파이프라인을 순서대로 돌린다:
  1) LLM 이 여행지를 추천한다 → JSON
  2) 그 도시로 지도 API 에서 맛집을 찾는다 → 리스트(0건 가능)
  3) 둘을 합쳐 Markdown 리포트를 만든다 → results/ 에 저장

각 단계는 별도 파일(recommend.py · places.py · report.py)에 있고, 이 파일은 **순서와 흐름만**
담당한다. 그래서 "어디서 무엇이 실패했는지"가 이 파일 하나만 읽어도 보인다.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

import config
import places
import recommend
import report


def parse_date(text):
    """'YYYY-MM-DD' 문자열을 검증한다. 형식이 틀리면 ValueError.

    `datetime.strptime` 이 형식·존재하는 날짜를 한 번에 본다 — 2026-02-30 같은
    "형식은 맞지만 없는 날짜"도 여기서 걸린다(정규식만 쓰면 통과해 버린다).
    """
    return dt.datetime.strptime(text, "%Y-%m-%d").date()


def build_parser():
    """CLI 옵션 정의. 미션 요구 필수 옵션 = -date."""
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="날짜를 주면 여행지를 추천받아 맛집까지 찾아 리포트를 만듭니다.",
        epilog='예) python main.py -date "2026-09-15"',
    )
    parser.add_argument("-date", required=True, help='여행 날짜 "YYYY-MM-DD"')
    parser.add_argument("--size", type=int, default=places.DEFAULT_SIZE, help="맛집 개수(기본 5)")
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="같은 날짜의 저장 결과가 있어도 무시하고 다시 호출한다",
    )
    return parser


def save_results(date_text, data, report_text):
    """원본 데이터(JSON)와 리포트(.md)를 results/ 에 날짜 이름으로 저장 → (json경로, md경로)."""
    os.makedirs(config.RESULTS_DIR, exist_ok=True)
    json_path = os.path.join(config.RESULTS_DIR, f"{date_text}.json")
    md_path = os.path.join(config.RESULTS_DIR, f"{date_text}.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    return json_path, md_path


def load_cache(date_text):
    """같은 날짜의 저장 결과가 있으면 읽어서 돌려준다(보너스 — 캐싱). 없으면 None.

    왜 캐싱하나: 외부 API 는 호출마다 돈·쿼터·시간이 든다. 같은 날짜로 리포트 형식만
    고쳐 다시 뽑는 경우가 흔한데, 그때마다 API 를 부를 이유가 없다.
    """
    path = os.path.join(config.RESULTS_DIR, f"{date_text}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None  # 캐시가 깨졌으면 없는 셈 치고 새로 호출한다


def run(argv=None):
    """파이프라인 본체. 정상 종료 0, 사용법 오류·중단 1."""
    args = build_parser().parse_args(argv)

    # ① 입력 검증 — 형식이 틀리면 사용법을 보여주고 즉시 종료
    try:
        parse_date(args.date)
    except ValueError:
        print(f"[중단] 날짜 형식이 올바르지 않습니다: {args.date!r}", file=sys.stderr)
        build_parser().print_help(sys.stderr)
        return 1

    config.load_dotenv()
    errors = []

    # ② 캐시 확인 — 있으면 API 호출을 건너뛴다(보너스)
    cached = None if args.no_cache else load_cache(args.date)
    if cached:
        print(f"[캐시] {args.date} 저장 결과를 재사용합니다(API 호출 없음).", file=sys.stderr)
        recommendation = cached.get("recommendation") or {}
        restaurants = cached.get("restaurants") or []
        errors = list(cached.get("errors") or [])
    else:
        # ③ 키 확인 — 없으면 즉시 종료하고 설정 방법을 안내
        llm_key = config.get_key(config.LLM_KEY_NAME)
        if not llm_key:
            print(config.missing_key_message(config.LLM_KEY_NAME), file=sys.stderr)
            return 1
        map_key = config.get_key(config.MAP_KEY_NAME)
        if not map_key:
            print(config.missing_key_message(config.MAP_KEY_NAME), file=sys.stderr)
            return 1

        # ④ 1단계 — LLM 추천
        print(f"[1/3] {args.date} 여행지 추천 요청 중...", file=sys.stderr)
        recommendation = recommend.recommend(llm_key, args.date, errors)
        if recommendation is None:
            # 1단계 실패는 치명적이다 — 추천 도시가 없으면 2·3단계가 성립하지 않는다.
            print("[중단] 여행지 추천에 실패했습니다. 사유:", file=sys.stderr)
            for message in errors:
                print(f"  - {message}", file=sys.stderr)
            return 1
        city = recommendation["recommended_city"]
        print(f"      추천: {city}", file=sys.stderr)

        # ⑤ 2단계 — 맛집 검색(실패해도 계속)
        print(f"[2/3] {city} 맛집 검색 중...", file=sys.stderr)
        restaurants = places.find_restaurants(map_key, city, errors, size=args.size)
        print(f"      {len(restaurants)}곳 확보", file=sys.stderr)

    # ⑥ 3단계 — 리포트 생성·저장
    print("[3/3] 리포트 생성 중...", file=sys.stderr)
    report_text = report.build_report(args.date, recommendation, restaurants, errors)
    data = {
        "date": args.date,
        "recommendation": recommendation,
        "restaurants": restaurants,
        "errors": errors,
    }
    json_path, md_path = save_results(args.date, data, report_text)
    print(f"[완료] {json_path} · {md_path}", file=sys.stderr)
    if errors:
        print(f"      (경고 {len(errors)}건 — 리포트 errors 섹션 참조)", file=sys.stderr)

    print(report_text)  # 결과 본문은 stdout 으로 — 파이프로 넘길 수 있게
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
