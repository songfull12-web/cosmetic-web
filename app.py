import streamlit as st
import pandas as pd
import io
import pdfplumber
import re

st.set_page_config(page_title="비스타릿 RA 통합 분석기 V12", layout="wide")

@st.cache_data
def load_db():
    try:
        # DB 로드 및 검색용 키워드 생성 (공백/기호 제거)
        df = pd.read_csv('regulations.csv')
        df['Search_Key'] = df['Ingredient'].astype(str).str.upper().str.replace(r'[^A-Z0-9]', '', regex=True)
        return df
    except:
        return pd.DataFrame(columns=["Ingredient", "EU_Status", "ASEAN_Status", "MiddleEast_Status", "Search_Key"])

db = load_db()

st.title("🛡️ 비스타릿 RA 통합 분석 시스템 v12.0")
st.info("성분 리스트를 전체 복구했습니다. 금지 성분이 있다면 상단에 빨간색으로 표시됩니다.")

uploaded_file = st.file_uploader("B.O.M(PDF/Excel) 업로드", type=["pdf", "xlsx"])

raw_text = ""
if uploaded_file:
    try:
        if uploaded_file.name.endswith('.pdf'):
            with pdfplumber.open(uploaded_file) as pdf:
                raw_text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
        elif uploaded_file.name.endswith('.xlsx'):
            df_ex = pd.read_excel(uploaded_file).fillna('')
            raw_text = "\n".join([" | ".join(map(str, row)) for row in df_ex.values])
        st.success(f"✅ '{uploaded_file.name}' 분석 준비 완료")
    except Exception as e:
        st.error(f"파일 읽기 실패: {e}")

# 🔍 실무자 보정 영역 (여기에 텍스트가 떠야 함)
st.subheader("📋 전체 데이터 확인")
edit_text = st.text_area("분석된 원본 텍스트입니다. 줄바꿈이 성분 단위로 되어있는지 확인만 해주세요.", value=raw_text, height=250)

if st.button("🚨 전성분 규제 정밀 스크리닝 시작"):
    if edit_text:
        lines = [l.strip() for l in edit_text.split('\n') if len(l.strip()) > 5]
        all_results = []
        ban_count = 0
        
        for line in lines:
            # 1. CAS 및 함량만 미리 추출
            cas = ", ".join(re.findall(r'\d{2,7}-\d{2}-\d', line))
            # 2. 검색용 성분 키워드 정제 (알파벳만 추출)
            clean_line = re.sub(r'[^a-zA-Z]', '', line).upper()
            
            # 3. DB 대조 (단어 포함 여부로 아주 넓게 검색)
            # DB의 Search_Key가 현재 줄(clean_line)에 포함되어 있는지 확인
            matches = db[db['Search_Key'].apply(lambda x: len(x) > 4 and x in clean_line)]
            
            if not matches.empty:
                for _, row in matches.iterrows():
                    res = row.to_dict()
                    res['입력데이터'] = line[:100]
                    res['CAS'] = cas
                    res['검토결과'] = "❌ 금지/제한 성분 주의"
                    all_results.append(res)
                    ban_count += 1
            else:
                # 금지 성분이 아니더라도 리스트에는 남겨둠 (그래야 70개가 다 나옴)
                all_results.append({
                    '입력데이터': line[:100],
                    'CAS': cas,
                    '검토결과': "✅ 일반 성분",
                    'Ingredient': "정보 없음",
                    'EU_Status': "-", 'ASEAN_Status': "-", 'MiddleEast_Status': "-"
                })

        final_df = pd.DataFrame(all_results)
        
        # 결과 표시
        st.divider()
        if ban_count > 0:
            st.error(f"⚠️ 총 {ban_count}건의 규제 의심 성분이 발견되었습니다!")
        else:
            st.success("✅ 규제 DB와 일치하는 성분이 없습니다.")
        
        st.dataframe(final_df, use_container_width=True)

        # 엑셀 보고서 생성
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            final_df.to_excel(writer, index=False, sheet_name='Regulatory_Check')
        st.download_button("📥 전성분 검토 보고서 다운로드", output.getvalue(), "Regulatory_Check.xlsx")
