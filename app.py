import streamlit as st
import pandas as pd
import io
import pdfplumber
import re

st.set_page_config(page_title="비스타릿 RA 지능형 스크리너", layout="wide")

@st.cache_data
def load_db():
    try:
        df = pd.read_csv('regulations.csv')
        df['Ingredient'] = df['Ingredient'].astype(str).str.strip()
        return df
    except:
        return pd.DataFrame(columns=["Ingredient", "EU_Status", "ASEAN_Status", "MiddleEast_Status"])

db = load_db()

st.title("📑 RA 지능형 성분 분석기 v8.0")
st.info("복합 성분 및 다중 CAS 번호가 포함된 다양한 양식의 B.O.M을 센스 있게 분석합니다.")

uploaded_file = st.file_uploader("B.O.M(PDF/Excel) 업로드", type=["pdf", "xlsx", "jpg", "png"])

raw_text = ""
if uploaded_file:
    with st.spinner('문서를 지능적으로 분석 중...'):
        if uploaded_file.name.endswith('.pdf'):
            with pdfplumber.open(uploaded_file) as pdf:
                raw_text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
        elif uploaded_file.name.endswith('.xlsx'):
            df_ex = pd.read_excel(uploaded_file)
            raw_text = df_ex.astype(str).apply(lambda x: ' | '.join(x), axis=1).str.cat(sep='\n')
    st.success("✅ 파일 분석 완료!")

# 🧠 지능형 성분 추출 함수 (복합성분/다중CAS 대응)
def smart_parser(text):
    # 1. 함량(%) 및 불필요 기호 제거
    cleaned = re.sub(r'\d+\.?\d*\s?%', '', text) 
    # 2. CAS 번호 패턴(00-00-0) 추출만 하고 성분명 검색에서는 제외
    cas_numbers = re.findall(r'\d{2,7}-\d{2}-\d', cleaned)
    # 3. 영문 INCI 네임 위주로 추출 (대문자, 공백, 특수문자 포함된 긴 명칭)
    # 한글과 영문이 섞인 경우 영문 위주로 필터링
    name_only = re.sub(r'[^a-zA-Z\s\-\,]', '', cleaned).strip()
    return name_only, cas_numbers

st.subheader("📋 분석된 원료 그룹")
edit_text = st.text_area("텍스트가 엉망이라면 성분 단위로 줄을 나눠주세요.", value=raw_text, height=250)

if st.button("🚀 지능형 규제 스크리닝 시작"):
    if edit_text:
        lines = [l.strip() for l in edit_text.split('\n') if len(l.strip()) > 5]
        results = []
        
        for line in lines:
            ing_name, cas_list = smart_parser(line)
            if not ing_name: continue
            
            # DB 검색 시 성분명의 앞부분 핵심 키워드 활용
            search_keywords = [k.strip() for k in ing_name.split(',') if len(k.strip()) > 3]
            
            found = False
            for kw in search_keywords:
                match = db[db['Ingredient'].str.contains(re.escape(kw), case=False, na=False)]
                if not match.empty:
                    res = match.iloc[0].to_dict()
                    res['추출된 성분명'] = ing_name
                    res['포함된 CAS'] = ", ".join(cas_list)
                    res['판단'] = "⚠️ 규제대상"
                    results.append(res)
                    found = True
                    break
            
            if not found:
                results.append({
                    '추출된 성분명': ing_name,
                    '포함된 CAS': ", ".join(cas_list),
                    '판단': "✅ 특이사항 없음",
                    'EU_Status': "-", 'ASEAN_Status': "-", 'MiddleEast_Status': "-", 'Source': "N/A"
                })

        st.dataframe(pd.DataFrame(results), use_container_width=True)
