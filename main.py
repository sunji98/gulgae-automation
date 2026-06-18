import os
import json
import anthropic
import gspread
from google.oauth2.service_account import Credentials

# 깃허브 금고(Secrets)에서 값 가져오기
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
GOOGLE_SERVICE_ACCOUNT = os.environ.get("GOOGLE_SERVICE_ACCOUNT")

# 서비스 계정 정보 로드
try:
    service_account_info = json.loads(GOOGLE_SERVICE_ACCOUNT)
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    gc = gspread.authorize(creds)
except Exception as e:
    print(f"구글 인증 데이터 파싱 실패: {e}")
    exit(1)

client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

# 구글 시트 열기
try:
    doc = gc.open("웰니스_콘텐츠_마스터_캘린더")
    calendar_sheet = doc.worksheet("마스터_캘린더")
except Exception as e:
    print(f"구글 시트를 열 수 없습니다. 이메일 공유를 확인하세요: {e}")
    exit(1)

all_rows = calendar_sheet.get_all_records()
if not all_rows:
    print("분석할 데이터가 시트에 없습니다.")
    exit()

last_row_idx = len(all_rows) + 1
last_row = all_rows[-1]

# 이미 최종 결과가 있으면 중단
if str(last_row.get("最终 인스타그램 캡션", "")).strip() or str(last_row.get("최종 인스타그램 캡션", "")).strip():
    print("이미 처리가 완료된 최신 행입니다.")
    exit()

# 웰니스 슬로우핏 브랜드 페르소나 주입
system_prompt = """
너는 2030 한국 여성들을 타깃으로 하는 프리미엄 웰니스 브랜드 'gulgae.slowfit'의 수석 브랜드 디렉터이다.
사용자의 인풋 데이터를 바탕으로 타깃의 결핍을 채워주는 교집합 주제를 도출하고, 인스타그램 최적 포맷(릴스 vs 피드 게시물)을 판별하라.
결과는 반드시 아래의 형식을 정확히 지켜 답변해야 하며, 각 항목은 '||' 기호로 구분하라.
형식: 추천 업로드 시간 || 콘텐츠 핵심 주제 || 최적 포맷 || 시각 연출 가이드 || 최종 인스타그램 캡션
"""

user_input = f"""
- 내가 가진 소스: {last_row.get('내가 가진 소스 형태')}
- 제작 가능 시간: {last_row.get('제작 가능 시간')}
- 이번 주 일상 메모: {last_row.get('이번 주 일상 메모')}
"""

response = client.messages.create(
    model="claude-3-5-sonnet",
    max_tokens=2000,
    system=system_prompt,
    messages=[{"role": "user", "content": user_input}]
)

result = response.content[0].text.split("||")

if len(result) >= 5:
    # 5번째 열부터 9번째 열까지 순서대로 업데이트
    calendar_sheet.update_cell(last_row_idx, 5, result[0].strip())
    calendar_sheet.update_cell(last_row_idx, 6, result[1].strip())
    calendar_sheet.update_cell(last_row_idx, 7, result[2].strip())
    calendar_sheet.update_cell(last_row_idx, 8, result[3].strip())
    calendar_sheet.update_cell(last_row_idx, 9, result[4].strip())
    print("🎉 구글 시트에 인스타 콘텐츠 자동 입력 완료!")
else:
    print("형식 오류 반환됨:", response.content[0].text)
