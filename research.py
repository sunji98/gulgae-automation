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

# 구글 시트 열기 — 탭 없으면 자동 생성
try:
    doc = gc.open_by_key(SPREADSHEET_ID)
    try:
        research_sheet = doc.worksheet("굴개의 웰니스 리서치")
    except gspread.exceptions.WorksheetNotFound:
        research_sheet = doc.add_worksheet(
            title="굴개의 웰니스 리서치", rows=500, cols=12
        )
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

# 트렌드 1개씩 요청 (JSON 잘림 방지)
system_prompt = """
당신은 한국 20~30대 여성들의 건강한 라이프스타일을 돕는 웰니스 콘텐츠 전략가이다.
유행성보다 실효성을 우선 평가하며, 즉시 실천 가능한 정보를 선별한다.

반드시 JSON 객체 하나만 출력하라. 다른 텍스트, 설명, 마크다운 절대 금지.
형식:
{
  "트렌드명": "",
  "왜 주목받는가": "",
  "해결하는 문제": "",
  "실제 적용 난이도": "",
  "한국 여성 적합도": "",
  "한국식 적용 방법": "",
  "콘텐츠 소재 아이디어": "아이디어1 / 아이디어2 / 아이디어3 / 아이디어4 / 아이디어5",
  "릴스 가능": "가능 또는 불가능",
  "피드 가능": "가능 또는 불가능",
  "향후 성장 가능성": "",
  "출처 키워드": ""
}
"""

# 탐색할 주제 10개
topics = [
    "최근 미국에서 유행하는 건강 식단 트렌드 1가지",
    "최근 유럽에서 유행하는 건강 식단 트렌드 1가지",
    "최근 호주에서 유행하는 건강 식단 트렌드 1가지",
    "최근 미국에서 유행하는 여성 운동 습관 트렌드 1가지",
    "최근 유럽에서 유행하는 여성 운동 습관 트렌드 1가지",
    "최근 미국에서 주목받는 여성 건강 이슈 트렌드 1가지",
    "최근 유럽에서 주목받는 여성 건강 이슈 트렌드 1가지",
    "최근 미국에서 유행하는 웰니스 라이프스타일 트렌드 1가지",
    "최근 호주에서 유행하는 웰니스 라이프스타일 트렌드 1가지",
    "최근 전 세계에서 주목받는 웰니스 여행 트렌드 1가지",
]

today = datetime.now().strftime("%Y-%m-%d")
rows_to_add = []

for i, topic in enumerate(topics, 1):
    print(f"🔍 [{i}/10] 리서치 중: {topic}")
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=system_prompt,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{
                "role": "user",
                "content": f"웹검색으로 {topic}를 조사하고, 한국 20~30대 여성에게 적합한지 분석해서 JSON으로 출력해줘."
            }]
        )

        # 텍스트 추출
        full_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                full_text += block.text

        # JSON 파싱 (코드블록 제거)
        clean = full_text.strip()
        if "```" in clean:
            parts = clean.split("```")
            for part in parts:
                if part.startswith("json"):
                    clean = part[4:].strip()
                    break
                elif "{" in part:
                    clean = part.strip()
                    break

        # { } 사이만 추출
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start != -1 and end > start:
            clean = clean[start:end]

        trend = json.loads(clean)
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
        print(f"  ✅ {trend.get('트렌드명', '')} 완료!")

    except Exception as e:
        print(f"  ❌ [{i}번] 실패: {e}")
        continue

# 구글 시트에 한 번에 저장
if rows_to_add:
    research_sheet.append_rows(rows_to_add)
    print(f"\n🎉 웰니스 리서치 완료! {len(rows_to_add)}개 트렌드가 '굴개의 웰니스 리서치' 탭에 저장됐어요!")
else:
    print("저장된 트렌드가 없습니다.")
