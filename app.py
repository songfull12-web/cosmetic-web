import streamlit as st
import pandas as pd
import io
import pdfplumber
from PIL import Image
import pytesseract

st.set_page_config(page_title="Global Cosmetic AI Screener", layout="wide")

# 데이터베이스 로드
@st.cache_data
def load_db():
    try:
        return pd.read_csv('regulations.csv')
    except:
        return pd.DataFrame(columns=["Ingredient", "EU_Status", "US_MoCRA", "China_NMPA", "ASEAN_Status", "MiddleEast_Status", "Source"])

db = load_db()

st.title("🧪 AI 화장품 전성분 통합 분석기 (PDF/Excel 지원)")
st.info("원본 PDF나 엑셀 파일을 그대로 업로드하세요. AI가 내부 텍스트를 직접 추출합니다.")

# 파일 업로드 (PDF, XLSX, 이미지 모두 지원)
uploaded_file = st.file_uploader("파일 업로드 (PDF, XLSX, JPG, PNG)", type=["pdf", "xlsx", "jpg", "jpeg", "png"])

extracted_text = ""

if uploaded_file is not None:
    file_ext = uploaded_file.name.split('.')[-1].lower()
    
    with st.spinner('파일 분석 중...'):
        try:
            # 1. PDF 직접 읽기 (텍스트 추출)
            if file_ext == 'pdf':
                with pdfplumber.open(uploaded_file) as pdf:
                    pages_text = [page.extract_text() for page in pdf.pages if page.extract_text()]
                    extracted_text = "\n".join(pages_text)
            
            # 2. 엑셀 직접 읽기
            elif file_ext == 'xlsx':
                df_excel = pd.read_excel(uploaded_file)
                # 모든 셀의 데이터를 문자열로 합침
                extracted_text = df_excel.astype(str).apply(lambda x: ' '.join(x), axis=1).str.cat(sep='\n')
            
            # 3. 이미지 (OCR)
            else:
                image = Image.open(uploaded_file)
                extracted_text = pytesseract.image_to_string(image, lang='eng+kor')
            
            if extracted_text:
                st.success(f"✅ '{uploaded_file.name}'에서 성분 데이터를 추출했습니다.")
            else:
                st.warning("파일에서 텍스트를 찾지 못했습니다. 스캔된 PDF라면 캡처 후 이미지로 올려주세요.")
        except Exception as e:
            st.error(f"분석 오류: {e}")

# 추출 결과 확인 및 수정
st.subheader("📋 추출된 성분 리스트")
final_input = st.text_area("분석된 내용입니다. 성분명이 쉼표(,)로 구분되도록 확인해 주세요.", value=extracted_text, height=250)

if st.button("🚀 글로벌 규제 스크리닝 시작"):
    if final_input:
        # 전처리
        raw_list = final_input.replace('\n', ',').replace(':', ',').split(',')
        input_list = [i.strip() for i in raw_list if len(i.strip()) > 1]
        
        results = []
        for ing in input_list:
            match = db[db['Ingredient'].str.contains(ing, case=False, na=False)]
            if not match.empty:
                res = match.iloc[0].to_dict()
                res['입력성분'] = ing
                res['검토결과'] = "⚠️ 규제대상"
            else:
                res = {'입력성분': ing, '검토결과': "✅ 특이사항 없음", 'Source': "N/A"}
            results.append(res)
        
        st.divider()
        st.subheader("🔍 규제 대조 결과")
        st.dataframe(pd.DataFrame(results), use_container_width=True)
    else:
        st.warning("분석할 데이터가 없습니다.")
