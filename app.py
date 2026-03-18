import streamlit as st
import plotly.graph_objects as go
from screener import get_market_environment, run_screening

st.set_page_config(
    page_title="S&P 500 AI 스크리너",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 기관 트레이딩 알고리즘 기반 S&P 500 AI 스크리너")
st.caption("SMA200 · QQE 골든크로스 · 거래량 수급 · RSI 다이버전스 4중 필터링")
st.divider()

with st.sidebar:
    st.header("⚙️ 설정")
    min_score   = st.slider("최소 조건 만족 수", 2, 4, 2)
    max_results = st.number_input("최대 표시 종목 수", 10, 100, 30, step=5)
    st.divider()
    st.markdown("""
    **조건 설명**
    - ✅ >SMA200 : 현재가 > 200일 이평
    - ✅ QQE 골크 : 3일내 골든크로스
    - ✅ 수급 1.5× : 거래량 평균 1.5배↑
    - ✅ RSI 다이버 : 하락 다이버전스
    """)
    st.warning("⚠️ 투자 참고용입니다. 손실 책임은 본인에게 있습니다.")

if st.button("🚀 시장 스캔 시작", use_container_width=True):

    # STEP 1 시장 분석
    with st.spinner("🌎 시장 환경 분석 중..."):
        market = get_market_environment()

    st.subheader("📊 STEP 1 — 전체 시장 환경")
    c1, c2, c3 = st.columns(3)
    c1.metric("S&P 500", f"{market['close']:,.2f}")
    c2.metric("시장 추세", market['trend'])
    c3.metric("공포·탐욕 지수", f"{market['fng_score']}점 ({market['fng_rating']})")
    st.info(f"💡 AI 전략: {market['strategy']}")

    # 지수 차트
    hist = market['history']
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='S&P 500', line=dict(color='#00e5ff', width=2)))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA20'],  name='SMA20',  line=dict(color='#ffd166', width=1, dash='dot')))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA50'],  name='SMA50',  line=dict(color='#ff6b35', width=1, dash='dot')))
    fig.update_layout(title="S&P 500 최근 60일", height=350)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # STEP 2 스크리닝
    st.subheader("🔎 STEP 2 — 종목 스크리닝")
    progress_bar = st.progress(0, text="분석 준비 중...")

    def update_progress(pct, msg):
        progress_bar.progress(pct, text=msg)

    results_df = run_screening(progress_callback=update_progress)
    progress_bar.progress(1.0, text="✅ 스캔 완료!")

    if not results_df.empty:
        filtered = results_df[results_df['만족 수'] >= min_score].head(max_results)

        c1, c2, c3 = st.columns(3)
        c1.metric("전체 결과", f"{len(results_df)}개")
        c2.metric("4/4 특급", f"{len(results_df[results_df['만족 수']==4])}개")
        c3.metric("3/4 우수", f"{len(results_df[results_df['만족 수']==3])}개")

        display_df = filtered.copy()
        for col in ['>SMA200','QQE 골든크로스','수급(1.5×)','RSI 다이버전스']:
            display_df[col] = display_df[col].apply(lambda v: '⭕' if v else '❌')

        st.dataframe(display_df, use_container_width=True, height=500)

        csv = filtered.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 CSV 다운로드", csv, "screening.csv", "text/csv", use_container_width=True)
    else:
        st.warning("조건 2개 이상 만족 종목이 없습니다.")
```

---

**📄 파일 ③ — `requirements.txt`**
```
streamlit
yfinance
pandas_ta
requests
lxml
plotly
pandas
```

---

## ✅ STEP 3 — 실행 (5분)

**1. 명령 프롬프트(cmd) 열기**

시작 메뉴에서 `cmd` 검색 → 명령 프롬프트 실행

**2. sp500 폴더로 이동**
```
cd Desktop\sp500
```

**3. 패키지 설치 (최초 1회만)**
```
pip install streamlit yfinance pandas_ta requests lxml plotly
```
> ⏳ 설치에 2~3분 걸려요. 기다리시면 됩니다.

**4. 앱 실행!**
```
streamlit run app.py
```

**5. 브라우저가 자동으로 열리면서 홈페이지가 뜹니다! 🎉**
```
http://localhost:8501