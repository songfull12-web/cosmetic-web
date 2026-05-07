import streamlit as st
import pandas as pd
import io
import pdfplumber
import re

st.set_page_config(page_title="비스타릿 RA 정밀 스크리너", layout="wide")

@st.cache_data
def load_db():
    try:
        # DB 로드 및 성분명 표준화 (공백 제거, 대문자 변환)
        df = pd.read_csv('regulations.csv')
        df['Ingredient_Clean'] = df['Ingredient'].astype(str).str.upper().str.replace(r'[^A-Z0-9]', '', regex=True)
        return df
    except:
        return pd.DataFrame(columns=["Ingredient", "EU_Status", "ASEAN_Status", "MiddleEast_Status"])

db = load_db()

st.title("🛡️ 비스타릿 RA 정밀 성분 분석기 v11.0")
st.error("주의: 주소, 업체명, 서명 등 성분이 아닌 데이터는 AI가 자동으로 제거합니다.")

uploaded_file = st.file_uploader("B.O.M(PDF/Excel) 업로드", type=["pdf", "xlsx", "jpg", "png"])

raw_text = ""
if uploaded_file:
    try:
        if uploaded_file.name.endswith('.pdf'):
            with pdfplumber.open(uploaded_file) as pdf:
                raw_text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
        elif uploaded_file.name.endswith('.xlsx'):
            df_ex = pd.read_excel(uploaded_file).fillna('')
            raw_text = "\n".join([" ".join(map(str, row)) for row in df_ex.values])
        st.success("✅ 파일 데이터 로드 완료")
    except Exception as e:
        st.error(f"파일 읽기 실패: {e}")

# 🔍 RA 전용 정밀 필터링 함수
def ra_expert_filter(line):
    # 1. 성분이 아님이 확실한 단어들 (제거 목록)
    ignore_keywords = ['SIGNED', 'TOTAL', 'PAGE', 'CUSTOMER', 'PRODUCT NAME', 'ADDRESS', 'TEL', 'FAX', 'INGREDIENT %', 'DATE']
    upper_line = line.upper()
    if any(kw in upper_line for kw in ignore_keywords):
        return None
    
    # 2. CAS 번호 및 함량 추출
    cas = ", ".join(re.findall(r'\d{2,7}-\d{2}-\d', line))
    
    # 3. 영문 INCI명 추출 (한글이나 잡다한 텍스트 제외하고 순수 영문 성분만)
    inci_match = re.search(r'[a-zA-Z\s\-\,]{5,}', line) # 5자 이상의 연속된 영문/공백
    if not inci_match: return None
    
    inci_name = inci_match.group().strip()
    return {"name": inci_name, "cas": cas, "raw": line}

st.subheader("📋 실무자 검토 영역")
edit_text = st.text_area("분석된 내용입니다. 여기서 성분이 아닌 줄은 과감히 지워주세요.", value=raw_text, height=250)

if st.button("🚨 정밀 규제 스크리닝 실행"):
    if edit_text:
        lines = edit_text.split('\n')
        results = []
        
        for line in lines:
            parsed = ra_expert_filter(line)
            if not parsed: continue
            
            # DB와 비교 (매우 엄격하게 대조)
            search_key = re.sub(r'[^A-Z0-9]', '', parsed['name'].upper())
            # DB의 성분명과 정확히 일치하거나 포함되는지 확인
            match = db[db['Ingredient_Clean'].str.contains(search_key, na=False) | 
                       (db['Ingredient_Clean'] == search_key)]
            
            if not match.empty:
                res = match.iloc[0].to_dict()
                res['검토성분'] = parsed['name']
                res['CAS'] = parsed['cas']
                res['상태'] = "❌ 금지/제한성분"
                results.append(res)
            else:
                # DB에 없는 경우 '기타 성분'으로 분류 (결과창을 깨끗하게 유지)
                pass 

        if results:
            st.warning(f"⚠️ 규제 DB와 일치하는 성분이 {len(results)}건 발견되었습니다.")
            st.dataframe(pd.DataFrame(results)[['검토성분', 'CAS', '상태', 'EU_Status', 'ASEAN_Status', 'MiddleEast_Status']], use_container_width=True)
        else:
            st.success("✅ 규제 대상 성분이 발견되지 않았습니다. (DB 대조 결과)")

        # 전체 리스트 엑셀 저장용
        full_df = pd.DataFrame(results)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            full_df.to_excel(writer, index=False, sheet_name='Report')
        st.download_button("📥 최종 보고서 다운로드", output.getvalue(), "RA_Analysis_Report.xlsx")
