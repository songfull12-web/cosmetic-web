import streamlit as st
import pandas as pd
import io
import pdfplumber
import re

st.set_page_config(page_title="비스타릿 RA 통합 최종본", layout="wide")

@st.cache_data
def load_db():
    try:
        df = pd.read_csv('regulations.csv')
        # 검색용 키워드: 특수문자 제거 후 순수 알파벳만 남겨서 대조 (오타/공백 방어)
        df['Search_Key'] = df['Ingredient'].astype(str).str.upper().str.replace(r'[^A-Z]', '', regex=True)
        return df
    except:
        return pd.DataFrame(columns=["Ingredient", "EU_Status", "Source", "Search_Key"])

db = load_db()

st.title("🛡️ 비스타릿 RA 통합 분석 시스템 v16.0")
st.error("주의: 성분명이 함량/CAS와 찢어져 있어도 AI가 강제로 재조립하여 규제를 검토합니다.")

uploaded_file = st.file_uploader("B.O.M 파일 업로드", type=["pdf", "xlsx"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.pdf'):
            with pdfplumber.open(uploaded_file) as pdf:
                # 텍스트 추출 시 표 구조를 무시하고 모든 글자를 한 줄로 이어 붙임 (재조립을 위해)
                raw_text = " ".join([p.extract_text() for p in pdf.pages if p.extract_text()])
        else:
            df_ex = pd.read_excel(uploaded_file).fillna('')
            raw_text = " ".join(df_ex.astype(str).values.flatten())

        # 🧠 [지능형 재조립] CAS 번호를 기준으로 성분을 쪼개기
        # 보통 성분명 뒤에 CAS가 붙으므로, CAS 번호를 구분자로 사용합니다.
        items = re.split(r'(\d{2,7}-\d{2}-\d)', raw_text)
        
        reconstructed = []
        for i in range(1, len(items), 2):
            # CAS 번호 앞의 텍스트(성분명)와 CAS 번호를 한 쌍으로 묶음
            name_part = items[i-1][-100:].strip() # 앞부분 100자 정도만 성분명으로 간주
            cas_part = items[i]
            reconstructed.append(f"{name_part} [CAS: {cas_part}]")

        st.success(f"✅ 성분 및 CAS 번호 기반 {len(reconstructed)}개 원료 세트 복구 완료")
        
        edit_text = st.text_area("AI가 재조립한 성분 리스트입니다.", value="\n".join(reconstructed), height=250)
        
        if st.button("🚀 EU 규제 및 글로벌 스크리닝 실행"):
            final_lines = edit_text.split('\n')
            results = []
            
            for line in final_lines:
                clean_target = re.sub(r'[^A-Z]', '', line.upper())
                
                # 역방향 매칭: DB의 금지 성분이 이 텍스트 안에 포함되어 있는가?
                # 검색 키워드 길이를 조절하여 정확도 향상
                hits = db[db['Search_Key'].apply(lambda x: len(str(x)) > 5 and str(x) in clean_target)]
                
                if not hits.empty:
                    for _, row in hits.iterrows():
                        res = row.to_dict()
                        res['BOM_Raw'] = line
                        res['Status'] = "❌ PROHIBITED (규제대상)"
                        results.append(res)
                else:
                    results.append({
                        'BOM_Raw': line, 'Status': "✅ Pass", 'Ingredient': "N/A",
                        'EU_Status': "-", 'ASEAN_Status': "-", 'MiddleEast_Status': "-", 'Source': "-"
                    })

            res_df = pd.DataFrame(results).sort_values(by='Status', ascending=False)
            st.dataframe(res_df, use_container_width=True)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                res_df.to_excel(writer, index=False, sheet_name='Result')
            st.download_button("📥 엑셀 보고서 다운로드", output.getvalue(), "Regulatory_Report_V16.xlsx")

    except Exception as e:
        st.error(f"오류 발생: {e}")
