import streamlit as st
import pandas as pd
import io
import pdfplumber
import re

st.set_page_config(page_title="비스타릿 RA 통합 분석 시스템", layout="wide")

# 규제 DB 로드
@st.cache_data
def load_db():
    try:
        df = pd.read_csv('regulations.csv')
        df['Ingredient'] = df['Ingredient'].astype(str).str.strip()
        return df
    except:
        return pd.DataFrame(columns=["Ingredient", "EU_Status", "ASEAN_Status", "MiddleEast_Status", "Source"])

db = load_db()

st.title("🧪 RA 지능형 통합 분석기 v10.0")
st.info("PDF/Excel의 복잡한 양식에서 성분명, CAS, 함량을 똑똑하게 분류합니다.")

uploaded_file = st.file_uploader("B.O.M 파일 업로드 (PDF, XLSX, JPG, PNG)", type=["pdf", "xlsx", "jpg", "png"])

raw_text = ""
if uploaded_file:
    with st.spinner('파일의 모든 데이터를 안전하게 읽고 있습니다...'):
        try:
            if uploaded_file.name.endswith('.pdf'):
                with pdfplumber.open(uploaded_file) as pdf:
                    # PDF의 줄바꿈과 표 구조를 최대한 살려서 추출
                    raw_text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
            elif uploaded_file.name.endswith('.xlsx'):
                df_ex = pd.read_excel(uploaded_file).fillna('')
                # 엑셀 에러 방지용 강제 문자열 변환
                raw_text = "\n".join([" | ".join(map(str, row)) for row in df_ex.values])
            st.success(f"✅ '{uploaded_file.name}' 분석 성공!")
        except Exception as e:
            st.error(f"⚠️ 파일 읽기 오류: {e}")

# 🧠 핵심 로직: 성분명, CAS, 함량 분리 필터
def refined_parser(text):
    # 1. CAS 번호 패턴 추출 (00-00-0)
    cas_list = re.findall(r'\d{2,7}-\d{2}-\d', text)
    # 2. 함량(%) 패턴 추출 및 제거
    percentages = re.findall(r'\d+\.?\d*\s?%', text)
    # 3. 노이즈 제거 (숫자, 특수기호, CAS번호 등 삭제하여 INCI만 남김)
    name_cleaned = re.sub(r'\d{2,7}-\d{2}-\d', '', text) # CAS 제거
    name_cleaned = re.sub(r'\d+\.?\d*\s?%', '', name_cleaned) # 함량 제거
    # 한글 및 영문 성분명 이외의 잡다한 기호 정리
    name_cleaned = re.sub(r'[^a-zA-Z가-힣\s\-\,]', '', name_cleaned).strip()
    
    # 성분명이 여러 개 섞인 경우(복합원료) 첫 번째 핵심 명칭 반환
    main_name = name_cleaned.split(',')[0].strip() if ',' in name_cleaned else name_cleaned
    return main_name, ", ".join(cas_list), ", ".join(percentages)

st.subheader("📋 추출 데이터 보정")
edit_text = st.text_area("AI가 추출한 원시 데이터입니다. 성분별로 줄을 나눠주시면 더 정확합니다.", value=raw_text, height=250)

if st.button("🚀 글로벌 규제 통합 스크리닝 시작"):
    if edit_text:
        lines = [l.strip() for l in edit_text.split('\n') if len(l.strip()) > 5]
        results = []
        
        for line in lines:
            ing_name, cas, content = refined_parser(line)
            if not ing_name or len(ing_name) < 3: continue
            
            # DB 대조 (부분 일치 검색 강화)
            match = db[db['Ingredient'].str.contains(re.escape(ing_name[:15]), case=False, na=False)]
            
            if not match.empty:
                res = match.iloc[0].to_dict()
                res['입력성분(INCI)'] = ing_name
                res['CAS No.'] = cas
                res['함량'] = content
                res['판단'] = "⚠️ 규제대상"
            else:
                res = {'입력성분(INCI)': ing_name, 'CAS No.': cas, '함량': content, '판단': "✅ 특이사항 없음"}
                for col in ["EU_Status", "ASEAN_Status", "MiddleEast_Status"]: res[col] = "-"
            
            results.append(res)

        # 결과 테이블 출력
        st.divider()
        st.subheader("🔍 국가별 규제 대조 결과")
        final_df = pd.DataFrame(results)
        st.dataframe(final_df, use_container_width=True)

        # 엑셀 다운로드
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            final_df.to_excel(writer, index=False, sheet_name='Report')
        st.download_button("📥 결과 보고서(Excel) 다운로드", output.getvalue(), "Regulatory_Report.xlsx")
