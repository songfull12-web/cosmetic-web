import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Global Cosmetic Reg-Checker", layout="wide")

@st.cache_data
def load_db():
    return pd.read_csv('regulations.csv')

db = load_db()

st.sidebar.header("🌐 규제 국가 설정")
selected_countries = st.sidebar.multiselect(
    "확인할 국가", 
    ["EU_Status", "US_MoCRA", "China_NMPA", "ASEAN_Status"], 
    default=["EU_Status", "US_MoCRA"]
)

st.title("🧪 화장품 전성분 글로벌 규제 검토")
raw_input = st.text_area("전성분 리스트 입력 (쉼표 ','로 구분)", height=150)

if st.button("🚀 규제 스크리닝 시작"):
    if raw_input:
        input_list = [i.strip() for i in raw_input.split(',')]
        results = []
        for ing in input_list:
            match = db[db['Ingredient'].str.contains(ing, case=False, na=False)]
            if not match.empty:
                res = match.iloc[0].to_dict()
                res['입력성분'] = ing
                res['판단'] = "⚠️ 규제대상"
            else:
                res = {'입력성분': ing, '판단': "✅ 특이사항 없음", 'Source': "N/A"}
                for col in ["EU_Status", "US_MoCRA", "China_NMPA", "ASEAN_Status"]:
                    if col not in res: res[col] = "-"
            results.append(res)
        
        res_df = pd.DataFrame(results)
        display_cols = ['입력성분', '판단'] + selected_countries + ['Source']
        final_df = res_df[display_cols]
        st.dataframe(final_df, use_container_width=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            final_df.to_excel(writer, index=False, sheet_name='Reg_Check')
        st.download_button("📥 엑셀로 저장", output.getvalue(), "Reg_Check.xlsx")
