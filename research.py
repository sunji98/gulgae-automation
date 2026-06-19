import os
import json
import anthropic
import gspread
from datetime import datetime
from google.auth import default
from google.auth.transport.requests import Request

# 깃허브 금고(Secrets)에서 값 가져오기
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")

# 구글 인증 (Workload Identity Federation)
try:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds, _ = default(scopes=scopes)
    if not creds.valid:
        creds.refresh(Request())
    gc = gspread.authorize(creds)
except Exception as e:
    print(f"구글 인증 실패: {e}")
    exit(1)

client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

# 구글 시트 열기 — "굴개의 웰니스 리서치" 탭 없으면 자동 생성
try:
    doc = gc.open_by_key(SPREADSHEET_ID)
    try:
        research_sheet = doc.worksheet("굴개의 웰니스 리서치")
    except gspread.exceptions.WorksheetNotFound:
        research_sheet = doc.add_worksheet(
            title="굴개의 웰니스 리서치", rows=500, cols=12
        )
        # 헤더 추가
        headers = [
            "리서치 날짜", "트렌드명", "왜 주목받는가", "해결하는 문제",
            "실제 적용 난이도(1~5)", "한국 여성 적합도(1~5)", "한국식 적용 방법",
            "콘텐츠 소재 아이디어", "릴스 가능", "피드 가능", "향후 성장 가능성", "출처/키워드"
        ]
        research_sheet.append_row(headers)
        print("새 탭 '굴개의 웰니스 리서치' 생성 완료!")
except Exception as e:
    print(f"구글 시트를 열 수 없습니다: {e}")
    exit(1)

# 리서치 프롬프트 (웹검색 포함)
system_prompt = """
당신은 한국 20~30대 여성들의 건강한 라이프스타일 형성을 돕는 웰니스 콘텐츠 전략가이자 리서처이다.
유행성보다 실효성을 우선적으로 평가하며, 사용자가 즉시 실천할 수 있는 정보를 선별한다.

결과는 반드시 JSON 배열 형식으로만 출력하라. 다른 텍스트는 절대 포함하지 마라.
형식:
[
  {
    "트렌드명": "",
    "왜 주목받는가": "",
    "해결하는 문제": "",
    "실제 적용 난이도": "1~5 숫자",
    "한국 여성 적합도": "1~5 숫자",
    "한국식 적용 방법": "",
    "콘텐츠 소재 아이디어": "아이디어1 / 아이디어2 / 아이디어3 / 아이디어4 / 아이디어5",
    "릴스 가능": "가능/불가능",
    "피드 가능": "가능/불가능",
    "향후 성장 가능성": "",
    "출처 키워드": ""
  }
]
"""

user_prompt = """
웹검색을 통해 최근 3개월 이내 미국, 유럽, 호주의 웰니스 트렌드를 리서치해줘.

[목표]
한국 20~30대 여성들이 건강한 습관을 만들 수 있도록 도와줄 실질적인 아이디어를 찾는 것이 목적이다.
단순히 유행하는 트렌드가 아니라 실제 효과가 있고 향후 한국에서도 관심을 가질 가능성이 높은 정보를 우선적으로 선별해라.

[우선 탐색 영역]
1. 건강 식단
2. 운동 습관
3. 여성 건강
4. 웰니스 라이프스타일
5. 웰니스 여행

10개 이상의 트렌드를 JSON 배열로 출력하라.
"""

print("🔍 웹검색으로 웰니스 트렌드 리서치 중...")

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=8000,
    system=system_prompt,
    tools=[{"type": "web_search_20250305", "name": "web_search"}],
    messages=[{"role": "user", "content": user_prompt}]
)

# 응답에서 텍스트 추출 (웹검색 결과 포함)
full_text = ""
for block in response.content:
    if hasattr(block, "text"):
        full_text += block.text

# JSON 파싱
try:
    # ```json 코드블록 제거
    clean = full_text.strip()
    if "```" in clean:
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    trends = json.loads(clean.strip())
except Exception as e:
    print(f"JSON 파싱 실패: {e}")
    print("원본 응답:", full_text[:500])
    exit(1)

# 구글 시트에 저장
today = datetime.now().strftime("%Y-%m-%d")
rows_to_add = []

for trend in trends:
    row = [
        today,
        trend.get("트렌드명", ""),
        trend.get("왜 주목받는가", ""),
        trend.get("해결하는 문제", ""),
        trend.get("실제 적용 난이도", ""),
        trend.get("한국 여성 적합도", ""),
        trend.get("한국식 적용 방법", ""),
        trend.get("콘텐츠 소재 아이디어", ""),
        trend.get("릴스 가능", ""),
        trend.get("피드 가능", ""),
        trend.get("향후 성장 가능성", ""),
        trend.get("출처 키워드", "")
    ]
    rows_to_add.append(row)

research_sheet.append_rows(rows_to_add)
print(f"🎉 웰니스 리서치 완료! {len(rows_to_add)}개 트렌드가 '굴개의 웰니스 리서치' 탭에 저장됐어요!")
