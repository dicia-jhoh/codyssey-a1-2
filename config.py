"""설정 계층 — API 키와 실행 옵션을 한 곳에서 읽는다.

**키는 코드에 절대 적지 않는다.** 환경변수 또는 `.env` 파일에서만 읽는다.
이유 셋(미션 요구이자 실제 사고 예방책):
  1. 협업·공유 때 실수로 키가 공개되는 것을 막는다(코드를 올려도 키는 안 올라간다).
  2. 키를 교체해도 코드를 고치지 않는다 — 운영·배포에서 값만 바꾸면 된다.
  3. 과금·쿼터가 걸린 서비스에서 유출 사고를 예방한다.
"""

from __future__ import annotations

import os

# 이 프로그램이 쓰는 환경변수 이름들. 값이 아니라 **이름만** 코드에 있다.
LLM_KEY_NAME = "OPENAI_API_KEY"  # LLM(1단계) — OpenAI 계열
MAP_KEY_NAME = "KAKAO_REST_API_KEY"  # 지도/장소 검색(2단계) — Kakao Local

RESULTS_DIR = "results"


def load_dotenv(path=".env"):
    """`.env` 파일을 읽어 환경변수로 올린다(python-dotenv 없이 직접 구현).

    형식은 한 줄에 `KEY=VALUE`. `#` 로 시작하는 줄과 빈 줄은 건너뛴다.
    이미 환경변수로 설정돼 있으면 **덮어쓰지 않는다** — 터미널에서 준 값이 우선이다
    (배포 환경에서 파일보다 환경변수가 우선인 관례와 같다).
    """
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


def get_key(name):
    """환경변수에서 키를 읽는다. 없으면 None(호출한 쪽이 안내 후 종료)."""
    value = os.environ.get(name, "").strip()
    return value or None


def missing_key_message(name):
    """키가 없을 때 화면에 보여줄 안내문. 운영체제별 설정 방법을 알려준다.

    ⚠ 실제 키 값은 어디에도 출력하지 않는다 — 안내문에도 `YOUR_KEY` 자리표시자만 쓴다.
    """
    return f"""
[중단] 환경변수 {name} 가 설정되어 있지 않습니다.

키를 설정하는 방법 (셋 중 하나):

  1) macOS / Linux — 지금 터미널에만 적용
     export {name}="YOUR_KEY"

  2) Windows PowerShell — 지금 세션에만 적용
     $env:{name}="YOUR_KEY"

  3) 프로젝트 폴더에 .env 파일 만들기 (권장, 매번 안 쳐도 됨)
     {name}=YOUR_KEY
     ※ .env 는 .gitignore 에 들어 있어 GitHub 에 올라가지 않습니다.

키를 코드나 README 에 직접 적지 마세요. 공개 저장소에 올라가면 즉시 폐기·재발급해야 합니다.
"""
