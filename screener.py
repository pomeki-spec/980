import io, requests, warnings
import yfinance as yf
import pandas as pd
import pandas_ta as ta

warnings.filterwarnings('ignore')

def get_market_environment():
    idx_df = yf.download("^GSPC", period="1y", progress=False)
    if isinstance(idx_df.columns, pd.MultiIndex):
        idx_df.columns = [col[0] for col in idx_df.columns]

    idx_df['SMA20'] = ta.sma(idx_df['Close'], length=20)
    idx_df['SMA50'] = ta.sma(idx_df['Close'], length=50)

    curr_close = float(idx_df['Close'].iloc[-1])
    sma20      = float(idx_df['SMA20'].iloc[-1])
    sma50      = float(idx_df['SMA50'].iloc[-1])

    if curr_close > sma20 and curr_close > sma50:
        trend = "상승장"
    elif curr_close < sma20 and curr_close < sma50:
        trend = "하락장"
    else:
        trend = "혼조장"

    fng_score, fng_rating = 50, "Neutral"
    try:
        url  = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        data = requests.get(url, headers={'User-Agent':'Mozilla/5.0'}, timeout=5).json()
        fng_score  = round(data['fear_and_greed']['score'])
        fng_rating = data['fear_and_greed']['rating'].title()
    except:
        vix_df = yf.download("^VIX", period="1d", progress=False)
        if isinstance(vix_df.columns, pd.MultiIndex):
            vix_df.columns = [col[0] for col in vix_df.columns]
        vix = float(vix_df['Close'].iloc[-1])
        fng_score = max(0, min(100, round(100 - (vix * 2.5))))
        if vix >= 30:   fng_rating = "Extreme Fear"
        elif vix >= 22: fng_rating = "Fear"
        elif vix >= 15: fng_rating = "Neutral"
        else:           fng_rating = "Greed"

    if trend == "상승장":
        if "Fear" in fng_rating:
            strategy = "🟢 적극 매수 — 대세 상승 속 눌림목 구간. 비중 확대 권장."
        elif "Greed" in fng_rating:
            strategy = "🟡 분할 매수 — 상승장이나 과열 상태. 추격 매수 자제."
        else:
            strategy = "🟢 정상 매수 — 안정적 상승장. 3~4점 종목 위주 공략."
    elif trend == "하락장":
        if "Extreme Fear" in fng_rating:
            strategy = "🟡 반등 노림 — 투매 출현. 단기 반등만 노리세요."
        else:
            strategy = "🔴 관망 권장 — 하락 추세. 현금 비중 최대화."
    else:
        strategy = "🟡 선별 매수 — 혼조장. 4/4 특급 종목 소액만 접근."

    return {
        "close": curr_close, "sma20": sma20, "sma50": sma50,
        "trend": trend, "fng_score": fng_score, "fng_rating": fng_rating,
        "strategy": strategy,
        "history": idx_df[['Close','SMA20','SMA50']].tail(60),
    }

def run_screening(progress_callback=None):
    url     = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    tables  = pd.read_html(io.StringIO(requests.get(url, headers={'User-Agent':'Mozilla/5.0'}).text))
    tickers = [str(t).replace('.', '-') for t in tables[0]['Symbol'].tolist() if pd.notna(t)]

    data    = yf.download(tickers, period="1y", interval="1d", progress=False, group_by="ticker")
    results = []

    for i, ticker in enumerate(tickers):
        if progress_callback:
            progress_callback(i / len(tickers), f"분석 중: {ticker} ({i+1}/{len(tickers)})")
        try:
            df = data[ticker].dropna()
            if len(df) < 200: continue

            df['SMA200']    = ta.sma(df['Close'],  length=200)
            df['RSI']       = ta.rsi(df['Close'],  length=14)
            df['Vol_SMA20'] = ta.sma(df['Volume'], length=20)

            qqe_df = ta.qqe(df['Close'], length=14, smooth=5, factor=4.236)
            if qqe_df is None or qqe_df.empty: continue

            fast_col = [c for c in qqe_df.columns if 'RSIMA' in c][0]
            slow_col = [c for c in qqe_df.columns if c.startswith('QQE_') and 'RSIMA' not in c][0]
            df['QQE_Fast'] = qqe_df[fast_col]
            df['QQE_Slow'] = qqe_df[slow_col]
            df = df.dropna()
            if len(df) < 40: continue

            curr_close = float(df['Close'].iloc[-1])
            cond_sma   = curr_close > float(df['SMA200'].iloc[-1])
            cond_vol   = float(df['Volume'].iloc[-1]) >= float(df['Vol_SMA20'].iloc[-1]) * 1.5

            cross    = (df['QQE_Fast'] > df['QQE_Slow']) & (df['QQE_Fast'].shift(1) <= df['QQE_Slow'].shift(1))
            cond_qqe = bool(cross.iloc[-3:].any() and float(df['QQE_Fast'].iloc[-1]) > float(df['QQE_Slow'].iloc[-1]))

            r = df.iloc[-10:]; p = df.iloc[-40:-10]
            ri = r['Close'].idxmin(); pi = p['Close'].idxmin()
            cond_div = bool(df.loc[ri,'Close'] < df.loc[pi,'Close'] and df.loc[ri,'RSI'] > df.loc[pi,'RSI'])

            score = int(cond_sma) + int(cond_vol) + int(cond_qqe) + int(cond_div)
            if score >= 2:
                results.append({
                    'Ticker': ticker, '만족 수': score,
                    '>SMA200': cond_sma, 'QQE 골든크로스': cond_qqe,
                    '수급(1.5×)': cond_vol, 'RSI 다이버전스': cond_div,
                    'Close ($)': round(curr_close, 2),
                })
        except:
            continue

    df_out = pd.DataFrame(results)
    if not df_out.empty:
        df_out = df_out.sort_values('만족 수', ascending=False).reset_index(drop=True)
    return df_out