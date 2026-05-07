import streamlit as st
import pandas as pd
import io

# 1. 페이지 설정
st.set_page_config(page_title="글로벌 화장품 규제 통합 스크리너", layout="wide")

@st.cache_data
def load_db():
    try:
        # 깃허브에 올린 최신 regulations.csv를 읽어옵니다.
        return pd.read_csv('regulations.csv')
    except:
        # 파일이 없거나 로드 실패 시 사용할 확장 샘플 데이터
        data = {
            "Ingredient": ["Salicylic Acid", "Phenoxyethanol", "Arbutin", "Titanium Dioxide"],
            "EU_Status": ["배합한도(2.0%)", "배합한도(1.0%)", "사용가능", "사용가능"],
            "US_MoCRA": ["사용가능", "사용가능", "사용가능", "사용가능"],
            "China_NMPA": ["배합한도(2.0%)", "배합한도(1.0%)", "배합한도(2.0%)", "사용가능"],
            "ASEAN_Status": ["배합한도(2.0%)", "배합한도(1.0%)", "사용가능", "사용가능"],
            "MiddleEast_Status": ["배합한도(2.0%)", "배합한도(1.0%)", "사용가능", "사용가능"],
            "Source": ["EU CosIng", "ASEAN Annex", "NMPA Inventory", "GSO Standard"]
        }
        return pd.DataFrame(data)

db = load_db()

# 2. 사이드바 - 국가 및 규제 지역 선택
with st.sidebar:
    st.header("🌐 규제 지역 설정")
    selected_countries = st.multiselect(
        "검토가 필요한 지역을 선택하세요", 
        ["EU_Status", "US_MoCRA", "China_NMPA", "ASEAN_Status", "MiddleEast_Status"], 
        default=["EU_Status", "ASEAN_Status", "MiddleEast_Status"]
    )
    st.divider()
    st.info("💡 중동(GSO), 아세안(ACD) 규제 데이터가 포함되었습니다.")

# 3. 메인 화면
st.title("🧪 글로벌 화장품 전성분 규제 검토 터미널")
st.markdown("---")

# 이미지 업로드 섹션
st.subheader("📸 전성분 이미지 업로드")
uploaded_file = st.file_uploader("제품 패키지 또는 전성분 표 이미지를 올려주세요", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(uploaded_file, caption="업로드 이미지", use_container_width=True)
    with col2:
        st.success("✅ 이미지가 정상적으로 업로드되었습니다.")
        st.info("이미지 분석(OCR)을 통해 추출된 텍스트를 아래 입력창에 붙여넣어 검토를 진행하세요.")

# 전성분 입력 섹션
st.subheader("✍️ 성분 리스트 검토")
raw_input = st.text_area(
    "검토할 전성분을 입력하세요 (쉼표 ',' 또는 줄바꿈으로 구분 가능)", 
    height=200,
    placeholder="예: Salicylic Acid, Water, Glycerin, Phenoxyethanol..."
)

if st.button("🚀 글로벌 규제 스크리닝 시작"):
    if raw_input:
        # 입력 데이터 정제 (쉼표 및 줄바꿈 대응)
        cleaned_input = raw_input.replace('\n', ',')
        input_list = [i.strip() for i in cleaned_input.split(',') if i.strip()]
        
        results = []
        for ing in input_list:
            # DB에서 성분 매칭 (대소문자 무시 및 부분 일치)
            match = db[db['Ingredient'].str.contains(ing, case=False, na=False)]
            
            if not match.empty:
                res = match.iloc[0].to_dict()
                res['입력성분'] = ing
                res['판단'] = "⚠️ 규제대상"
            else:
                res = {'입력성분': ing, '판단': "✅ 특이사항 없음", 'Source': "N/A"}
                for col in ["EU_Status", "US_MoCRA", "China_NMPA", "ASEAN_Status", "MiddleEast_Status"]:
                    if col not in res: res[col] = "-"
            
            results.append(res)

        # 결과 데이터프레임 생성 및 표시
        res_df = pd.DataFrame(results)
        display_cols = ['입력성분', '판단'] + selected_countries + ['Source']
        
        # 선택된 컬럼이 실제 데이터에 있는지 확인 후 필터링
        actual_cols = [c for c in display_cols if c in res_df.columns]
        final_df = res_df[actual_cols]

        st.divider()
        st.subheader("📋 국가별 규제 검토 결과")
        st.dataframe(final_df, use_container_width=True)

        # 4. 엑셀 다운로드 (보고용)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            final_df.to_excel(writer, index=False, sheet_name='Regulatory_Check')
        
        st.download_button(
            label="📥 검토 결과 엑셀로 다운로드",
            data=output.getvalue(),
            file_name="Global_Regulatory_Report.xlsx",
            mime="application/vnd.ms-excel"
        )
    else:
        st.warning("분석할 성분 리스트를 입력해 주세요.")

st.markdown("---")
st.caption("본 툴은 비스타릿 QC/RA 업무 지원을 위해 설계되었습니다. 실제 수출 시에는 최신 법령(Official Gazette)을 최종 확인하시기 바랍니다.")
