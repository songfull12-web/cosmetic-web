import streamlit as st
import pandas as pd
import io
import pdfplumber
import re

st.set_page_config(page_title="비스타릿 RA 정밀 시스템", layout="wide")

@st.cache_data
def load_db():
    try:
        # DB 로드 및 검색 최적화 (공백/기호 제거한 순수 영문 키워드 생성)
        df = pd.read_csv('regulations.csv')
        df['Search_Key'] = df['Ingredient'].astype(str).str.upper().str.replace(r'[^A-Z0-9]', '', regex=True)
        return df
    except:
        st.error("regulations.csv 파일을 찾을 수 없습니다.")
        return pd.DataFrame(columns=["Ingredient", "EU_Status", "US_MoCRA", "China_NMPA", "ASEAN_Status", "MiddleEast_Status", "Source", "Search_Key"])

db = load_db()

st.title("🛡️ 비스타릿 RA 정밀 분석기 v14.0")
st.info("성분이 아닌 데이터(TOTAL, 주소 등)는 자동으로 삭제하며, 규제 성분을 최우선으로 검출합니다.")

uploaded_file = st.file_uploader("B.O.M 파일 업로드 (PDF/Excel)", type=["pdf", "xlsx"])

if uploaded_file:
    try:
        # 1. 파일 읽기 및 원시 텍스트 추출
        if uploaded_file.name.endswith('.pdf'):
            with pdfplumber.open(uploaded_file) as pdf:
                raw_text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
        else:
            df_ex = pd.read_excel(uploaded_file).fillna('')
            raw_text = "\n".join([" | ".join(map(str, row)) for row in df_ex.values])
        
        # 2. 강력한 노이즈 필터링 (RA 실무 맞춤형)
        lines = raw_text.split('\n')
        cleaned_lines = []
        for line in lines:
            upper_l = line.upper()
            # 'TOTAL', 'SIGNED', 'ADDRESS', 'TEL' 등이 포함된 행이나 너무 짧은 행은 무시
            if any(x in upper_l for x in ['TOTAL', 'SIGNED', 'ADDRESS', 'TEL', 'FAX', 'CUSTOMER', 'PRODUCT', 'MATERIAL']):
                continue
            if len(line.strip()) < 5:
                continue
            cleaned_lines.append(line.strip())
        
        st.success(f"✅ 성분 후보 {len(cleaned_lines)}건 정제 완료")
        
        # 3. 데이터 편집 및 보정 영역
        edit_text = st.text_area("AI가 정제한 리스트입니다. 성분명이 찢어져 있다면 한 줄로 합쳐주세요.", value="\n".join(cleaned_lines), height=250)
        
        if st.button("🚀 정밀 규제 스크리닝 (출처 포함)"):
            final_list = [l.strip() for l in edit_text.split('\n') if l.strip()]
            results = []
            
            for line in final_list:
                # 검색용 키워드 생성 (알파벳/숫자만)
                clean_target = re.sub(r'[^A-Z0-9]', '', line.upper())
                # CAS 번호 추출
                cas_list = re.findall(r'\d{2,7}-\d{2}-\d', line)
                
                # 🔍 정밀 매칭: DB의 금지 성분 키워드가 현재 줄에 포함되어 있는지 확인
                # (성분명이 뒤섞여 있어도 키워드 매칭으로 검출 가능)
                hits = db[db['Search_Key'].apply(lambda x: len(str(x)) > 4 and str(x) in clean_target)]
                
                if not hits.empty:
                    for _, row in hits.iterrows():
                        res = row.to_dict()
                        res['입력데이터'] = line
                        res['추출CAS'] = ", ".join(cas_list)
                        res['검토결과'] = "❌ 규제주의"
                        results.append(res)
                else:
                    results.append({
                        '입력데이터': line, '추출CAS': ", ".join(cas_list), '검토결과': "✅ 일반",
                        'Ingredient': "N/A", 'EU_Status': "-", 'ASEAN_Status': "-", 'MiddleEast_Status': "-", 'Source': "-"
                    })
            
            res_df = pd.DataFrame(results)
            st.divider()
            
            # 결과 표시 (금지 성분이 상단에 오도록 정렬)
            st.subheader("🔍 글로벌 규제 대조 결과")
            display_cols = ['입력데이터', '추출CAS', '검토결과', 'EU_Status', 'ASEAN_Status', 'MiddleEast_Status', 'Source']
            st.dataframe(res_df[display_cols].sort_values(by='검토결과', ascending=False), use_container_width=True)
            
            # 엑셀 보고서 생성
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                res_df.to_excel(writer, index=False, sheet_name='RA_Analysis')
            st.download_button("📥 최종 보고서(Excel) 다운로드", output.getvalue(), "Vstarlit_RA_Check.xlsx")
            
    except Exception as e:
        st.error(f"시스템 오류 발생: {e}")
