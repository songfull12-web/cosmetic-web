import streamlit as st
import pandas as pd
import io
from PIL import Image
import pytesseract

# 1. 페이지 설정
st.set_page_config(page_title="Global Cosmetic AI Screener", layout="wide")

@st.cache_data
def load_db():
    try:
        # 깃허브의 regulations.csv를 읽어옵니다.
        df = pd.read_csv('regulations.csv')
        return df
    except:
        # 파일이 없을 때를 대비한 기본 구조
        return pd.DataFrame(columns=["Ingredient", "EU_Status", "US_MoCRA", "China_NMPA", "ASEAN_Status", "MiddleEast_Status", "Source"])

db = load_db()

# 2. 사이드바 - 규제 범위 설정
with st.sidebar:
    st.header("🌐 규제 범위 설정")
    # 중동, 아세안 등 모든 지역 포함
    all_regions = ["EU_Status", "US_MoCRA", "China_NMPA", "ASEAN_Status", "MiddleEast_Status"]
    selected_regions = st.multiselect("확인할 지역을 선택하세요", all_regions, default=all_regions)
    st.divider()
    st.caption("비스타릿 QC/RA 전용 자동화 시스템")

# 3. 메인 화면 - 파일 업로드 및 OCR
st.title("🧪 AI 화장품 전성분 글로벌 통합 스크리너")
st.info("PDF나 이미지를 올리면 AI가 성분을 분석하여 전 세계 규제를 1초 만에 확인합니다.")

uploaded_file = st.file_uploader("전성분 파일 업로드 (PDF 캡처, JPG, PNG)", type=["jpg", "jpeg", "png"])

ocr_text = ""
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="업로드된 이미지 분석 중...", width=500)
    
    with st.spinner('AI가 성분명을 읽고 있습니다...'):
        try:
            # 이미지에서 텍스트 추출 (영어+한국어)
            ocr_text = pytesseract.image_to_string(image, lang='eng+kor')
            st.success("✅ 성분 추출에 성공했습니다! 아래 리스트를 확인하세요.")
        except:
            st.error("OCR 엔진 연결 오류. 아래 칸에 직접 입력해주셔도 분석이 가능합니다.")

# 4. 성분 리스트 및 분석 실행
st.subheader("📋 분석 대상 성분 (추출 결과)")
# 추출된 텍스트를 쉼표 단위로 정렬하여 보여줌
final_input = st.text_area("AI가 읽은 내용입니다. 오타가 있다면 수정해 주세요.", value=ocr_text, height=200)

if st.button("🚀 전 세계 규제 즉시 스크리닝"):
    if final_input:
        # 데이터 전처리 (줄바꿈 및 불필요한 기호 제거)
        processed_input = final_input.replace('\n', ',').replace(':', ',').replace(';', ',')
        input_list = [i.strip() for i in processed_input.split(',') if len(i.strip()) > 1]
        
        analysis_results = []
        for ing in input_list:
            # DB 검색 (대소문자 무시)
            match = db[db['Ingredient'].str.contains(ing, case=False, na=False)]
            
            if not match.empty:
                res = match.iloc[0].to_dict()
                res['입력성분'] = ing
                res['검토결과'] = "⚠️ 규제대상(한도확인)"
            else:
                res = {'입력성분': ing, '검토결과': "✅ 특이사항 없음(DB미등록)", 'Source': "N/A"}
                for reg in all_regions:
                    res[reg] = "-"
            
            analysis_results.append(res)
        
        # 결과 표시
        res_df = pd.DataFrame(analysis_results)
        display_cols = ['입력성분', '검토결과'] + selected_regions + ['Source']
        st.divider()
        st.subheader("🔍 글로벌 규제 대조표")
        st.dataframe(res_df[display_cols], use_container_width=True)

        # 엑셀 다운로드
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            res_df[display_cols].to_excel(writer, index=False, sheet_name='Reg_Report')
        st.download_button("📥 분석 결과 엑셀 저장", output.getvalue(), "Regulatory_Report.xlsx")
    else:
        st.warning("분석할 성분이 없습니다. 파일을 올리거나 직접 입력해 주세요.")
