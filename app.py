import streamlit as st
import pandas as pd
import io
from PIL import Image
import pytesseract  # 글자 인식 엔진

st.set_page_config(page_title="Global Cosmetic AI Screener", layout="wide")

# 1. 데이터 로드
@st.cache_data
def load_db():
    try:
        return pd.read_csv('regulations.csv')
    except:
        return pd.DataFrame({"Ingredient": [], "EU_Status": [], "ASEAN_Status": [], "MiddleEast_Status": [], "Source": []})

db = load_db()

# 2. 메인 화면
st.title("🧪 AI 화장품 전성분 자동 스크리너")
st.info("이미지나 PDF 캡처본을 올리면 AI가 성분을 자동으로 읽어 규제를 검토합니다.")

# 3. 파일 업로드 및 자동 인식
uploaded_file = st.file_uploader("전성분 사진 또는 PDF 캡처 업로드", type=["jpg", "jpeg", "png"])

extracted_text = ""

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="인식 중인 이미지...", width=400)
    
    with st.spinner('AI가 성분을 읽고 있습니다... 잠시만 기다려 주세요.'):
        # [핵심] 이미지에서 글자 추출 (한국어/영어 지원)
        # ※ 테서렉트 설치 환경에 따라 lang 설정이 필요할 수 있습니다.
        try:
            extracted_text = pytesseract.image_to_string(image, lang='kor+eng')
            st.success("✅ 글자 추출 완료!")
        except:
            st.error("OCR 엔진 설정이 필요합니다. 아래 직접 입력을 이용해 주세요.")

# 4. 검토 구역 (자동으로 채워지거나 직접 수정 가능)
st.subheader("✍️ 검토 성분 리스트")
final_input = st.text_area(
    "AI가 추출한 성분입니다. 수정이 필요하면 직접 고쳐주세요.", 
    value=extracted_text, 
    height=200
)

# 5. 분석 실행
if st.button("🚀 규제 스크리닝 시작"):
    if final_input:
        # 전처리: 줄바꿈을 쉼표로 바꾸고 공백 제거
        items = final_input.replace('\n', ',').split(',')
        input_list = [i.strip() for i in items if i.strip()]
        
        results = []
        for ing in input_list:
            match = db[db['Ingredient'].str.contains(ing, case=False, na=False)]
            if not match.empty:
                res = match.iloc[0].to_dict()
                res['입력성분'] = ing
                res['판단'] = "⚠️ 규제대상"
            else:
                res = {'입력성분': ing, '판단': "✅ 특이사항 없음", 'Source': "N/A"}
            results.append(res)

        st.dataframe(pd.DataFrame(results), use_container_width=True)
    else:
        st.warning("분석할 성분이 없습니다.")
