import os
import anthropic
import gspread
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

# 구글 시트 열기
try:
    doc = gc.open_by_key(SPREADSHEET_ID)
    calendar_sheet = doc.worksheet("마스터 캘린더")
except Exception as e:
    print(f"구글 시트를 열 수 없습니다: {e}")
    exit(1)

all_rows = calendar_sheet.get_all_records()
if not all_rows:
    print("분석할 데이터가 시트에 없습니다.")
    exit()

last_row_idx = len(all_rows) + 1
last_row = all_rows[-1]

# 이미 최종 결과가 있으면 중단
if str(last_row.get("최종 인스타그램 캡션", "")).strip():
    print("이미 처리가 완료된 최신 행입니다.")
    exit()

# 브랜드 정의 및 콘텐츠 생성 프롬프트
system_prompt = """
당신은 한국 20~30대 여성들의 건강한 라이프스타일 형성을 돕는 웰니스 콘텐츠 전략가이자 리서처이다.

[브랜드 목표]
단순히 다이어트 정보를 전달하는 것이 아니라, 운동과 건강한 식습관을 통해 사람들이 지속 가능한 웰니스 라이프스타일을 만들도록 돕는 것이다.

[타깃]
- 다이어트를 반복하지만 계속 실패하는 여성
- 운동을 시작하고 싶지만 방법을 모르는 여성
- 폭식과 절식을 반복하는 여성
- 건강하게 예쁜 몸을 만들고 싶은 여성
- 자기관리를 시작하고 싶은 여성

[전달하고 싶은 감정]
- 생각보다 어렵지 않네?
- 나도 해볼 수 있겠는데?
- 이런 방법이 있었구나
- 같이 운동하고 싶다
- 건강하게 살아보고 싶다

[브랜드 톤]
전문가처럼 가르치는 사람이 아니라, 실제 경험을 공유하며 함께 성장하는 웰니스 가이드의 역할을 지향한다.
유행성 정보보다 실제 효과가 있는 건강 습관을 우선적으로 탐색하라.
모든 정보는 사용자가 즉시 실천할 수 있는 형태로 재가공하라.

[우선 탐색 분야]
1. 건강 식단
2. 운동
3. 여성 건강
4. 웰니스 라이프스타일
5. 웰니스 여행

[출력 형식]
결과는 반드시 아래 형식을 정확히 지켜 '||' 기호로 구분하여 한 줄로 답변하라.
형식: 추천 업로드 시간 || 콘텐츠 핵심 주제 || 최적 포맷(릴스/피드) || 시각 연출 가이드 || 최종 인스타그램 캡션
"""

user_input = f"""
아래 이번 주 데이터를 바탕으로 인스타그램 콘텐츠를 기획해줘.

- 내가 가진 소스 형태: {last_row.get('내가 가진 소스 형태')}
- 제작 가능 시간: {last_row.get('제작 가능 시간')}
- 이번 주 일상 메모: {last_row.get('이번 주 일상 메모')}
"""

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=2000,
    system=system_prompt,
    messages=[{"role": "user", "content": user_input}]
)

result = response.content[0].text.split("||")
if len(result) >= 5:
    calendar_sheet.update_cell(last_row_idx, 5, result[0].strip())
    calendar_sheet.update_cell(last_row_idx, 6, result[1].strip())
    calendar_sheet.update_cell(last_row_idx, 7, result[2].strip())
    calendar_sheet.update_cell(last_row_idx, 8, result[3].strip())
    calendar_sheet.update_cell(last_row_idx, 9, result[4].strip())
    print("🎉 구글 시트에 인스타 콘텐츠 자동 입력 완료!")
else:
    print("형식 오류 반환됨:", response.content[0].text)
