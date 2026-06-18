import os
import anthropic
import gspread

# 1. 깃허브 금고(Secrets)에서 안전하게 열쇠 꺼내오기
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# 2. 우회 발급받은 구글 API 키로 시트 인증하기
gc = gspread.api_key(GOOGLE_API_KEY)
client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

# 3. 구글 시트 열기 및 마지막 행 데이터 읽기
doc = gc.open("웰니스_콘텐츠_마스터_캘린더")
calendar_sheet = doc.worksheet("마스터_캘린더")

all_rows = calendar_sheet.get_all_records()
if not all_rows:
    print("분석할 새 데이터가 시트에 없습니다.")
    exit()

last_row_idx = len(all_rows) + 1  # 실제 구글 시트의 행 번호
last_row = all_rows[-1]

# 중복 실행 방지 (이미 최종 캡션이 채워져 있다면 패스)
if last_row.get("최종 인스타그램 캡션"):
    print("이미 처리가 완료된 최신 행입니다.")
    exit()

# 4. 고도화된 웰니스 전용 프롬프트 지침
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

# 5. 클로드 API 호출
response = client.messages.create(
    model="claude-3-5-sonnet",
    max_tokens=2000,
    system=system_prompt,
    messages=[{"role": "user", "content": user_input}]
)

# 6. 결과를 파싱하여 구글 시트 우측 칸에 자동으로 채워넣기
result = response.content[0].text.split("||")

if len(result) >= 5:
    calendar_sheet.update_cell(last_row_idx, 5, result[0].strip()) # 추천 시간
    calendar_sheet.update_cell(last_row_idx, 6, result[1].strip()) # 주제
    calendar_sheet.update_cell(last_row_idx, 7, result[2].strip()) # 포맷
    calendar_sheet.update_cell(last_row_idx, 8, result[3].strip()) # 연출 가이드
    calendar_sheet.update_cell(last_row_idx, 9, result[4].strip()) # 최종 캡션
    print("구글 시트에 성공적으로 인스타 콘텐츠를 업데이트했습니다!")
else:
    print("클로드 답변 형식이 올바르지 않습니다:", response.content[0].text)
