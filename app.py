import streamlit as st
import pandas as pd
import io
import pdfplumber
import re

st.set_page_config(page_title="비스타릿 RA 정밀 분석 v15", layout="wide")

@st.cache_data
def load_db():
    try:
        # DB 로드 및 검색 최적화
        df = pd.read_csv('regulations.csv')
        # 검색용 키워드: 모든 공백과 특수문자를 제거한 순수 알파벳+숫자 (대조 정확도 극대화)
        df['Search_Key'] = df['Ingredient'].astype(str).str.upper().str.replace(r'[^A-Z0-9]', '', regex=True)
        return df
    except:
        return pd.DataFrame(columns=["Ingredient", "EU_Status", "US_MoCRA", "ASEAN_Status", "MiddleEast_Status", "Source", "Search_Key"])

db = load_db()

st.title("🛡️ 비스타릿 RA 정밀 분석기 v15.0")
st.error("주의: EU 금지 성분(Annex II) 및 글로벌 규제를 우선적으로 강제 매칭합니다.")

uploaded_file = st.file_uploader("B.O.M(PDF/Excel) 업로드", type=["pdf", "xlsx"])

if uploaded_file:
    try:
        # 1. 원본 데이터 추출 (노이즈 방어)
        if uploaded_file.name.endswith('.pdf'):
            with pdfplumber.open(uploaded_file) as pdf:
                raw_text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
        else:
            df_ex = pd.read_excel(uploaded_file).fillna('')
            raw_text = "\n".join([" | ".join(map(str, row)) for row in df_ex.values])
        
        # 2. 강력한 필터링: RA 실무 노이즈(TOTAL, 주소 등) 제거
        lines = [l.strip() for l in raw_text.split('\n') if len(l.strip()) > 5]
        cleaned_lines = [l for l in lines if not any(x in l.upper() for x in ['TOTAL', 'SIGNED', 'ADDRESS', 'TEL', 'FAX', 'CUSTOMER', 'PRODUCT'])]
        
        st.success(f"✅ 성분 데이터 {len(cleaned_lines)}건 정제 완료")
        
        # 3. 보정 영역
        edit_text = st.text_area("AI가 분석한 리스트입니다. 누락된 성분이 있다면 직접 추가하세요.", value="\n".join(cleaned_lines), height=250)
        
        if st.button("🚨 EU 및 글로벌 규제 정밀 스크리닝"):
            final_list = [l.strip() for l in edit_text.split('\n') if l.strip()]
            results = []
            
            for line in final_list:
                # 검색용 키워드 정제
                clean_target = re.sub(r'[^A-Z0-9]', '', line.upper())
                cas_list = re.findall(r'\d{2,7}-\d{2}-\d', line)
                
                # 🔍 정밀 역방향 매칭 (DB의 금지 성분이 현재 줄에 포함되어 있는지)
                # 단어의 길이가 5자 이상인 핵심 키워드만 매칭
                hits = db[db['Search_Key'].apply(lambda x: len(str(x)) > 4 and str(x) in clean_target)]
                
                if not hits.empty:
                    for _, row in hits.iterrows():
                        res = row.to_dict()
                        res['BOM_Input'] = line
                        res['Detected_CAS'] = ", ".join(cas_list)
                        res['Status'] = "❌ PROHIBITED/RESTRICTED"
                        results.append(res)
                else:
                    results.append({
                        'BOM_Input': line, 'Detected_CAS': ", ".join(cas_list), 'Status': "✅ Pass",
                        'Ingredient': "Check Required", 'EU_Status': "-", 'ASEAN_Status': "-", 'MiddleEast_Status': "-", 'Source': "-"
                    })
            
            res_df = pd.DataFrame(results)
            st.divider()
            
            # 4. 결과 출력 (금지 성분이 무조건 위로)
            st.subheader("🔍 Regulation Match Results (Source Included)")
            res_df = res_df.sort_values(by='Status', ascending=False)
            st.dataframe(res_df[['BOM_Input', 'Detected_CAS', 'Status', 'EU_Status', 'ASEAN_Status', 'MiddleEast_Status', 'Source']], use_container_width=True)
            
            # 5. 엑셀 다운로드
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                res_df.to_excel(writer, index=False, sheet_name='Regulatory_Check')
            st.download_button("📥 최종 보고서 다운로드", output.getvalue(), "Vstarlit_RA_V15_Final.xlsx")
            
    except Exception as e:
        st.error(f"시스템 오류: {e}")
