# -*- coding: utf-8 -*-
"""
TW / US AI Stock Dashboard - Streamlit Web Version
手機 / 電腦瀏覽器皆可開啟
免費部署：GitHub + Streamlit Community Cloud
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "watchlist_config.json"

DEFAULT_CONFIG = {
    "pages": {
        "台股": ["^TWII", "2330.TW", "0050.TW", "00631L.TW", "2317.TW", "2454.TW"],
        "美股": ["AAPL", "MSFT", "NVDA", "TSLA", "AMD", "SPY", "QQQ"],
        "ETF": ["0050.TW", "006208.TW", "00631L.TW", "SPY", "QQQ", "TQQQ"],
        "觀察": [],
        "空白": [],
    }
}

TW_ALIAS = {
    "大盤": "^TWII",
    "台股大盤": "^TWII",
    "加權": "^TWII",
    "加權指數": "^TWII",
    "台積電": "2330.TW",
    "鴻海": "2317.TW",
    "聯發科": "2454.TW",
    "廣達": "2382.TW",
    "緯創": "3231.TW",
    "聯電": "2303.TW",
    "0050": "0050.TW",
    "006208": "006208.TW",
    "00631L": "00631L.TW",
    "00632R": "00632R.TW",
    "正2": "00631L.TW",
    "反1": "00632R.TW",
    "台灣50": "0050.TW",
}

MARKETS = {
    "台股大盤": "^TWII",
    "台積電": "2330.TW",
    "0050": "0050.TW",
    "正2": "00631L.TW",
    "Nasdaq": "^IXIC",
    "S&P500": "^GSPC",
    "SOX": "^SOX",
    "QQQ": "QQQ",
}

st.set_page_config(
    page_title="TW / US AI Stock Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background: #07111f; color: #e5e7eb; }
    section[data-testid="stSidebar"] { background: #0b1220; }
    div[data-testid="stMetric"] {
        background: #101a2b;
        border: 1px solid #26364d;
        border-radius: 16px;
        padding: 14px;
    }
    .card {
        background: #101a2b;
        border: 1px solid #26364d;
        border-radius: 16px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .small { color: #93c5fd; font-size: 0.92rem; }
    .warn { color: #fbbf24; }
    h1, h2, h3 { color: #f8fafc; }
    </style>
    """,
    unsafe_allow_html=True,
)


def normalize_symbol(s: str) -> str:
    raw = str(s).strip()
    up = raw.upper().replace(" ", "")
    if not up:
        return ""
    if raw in TW_ALIAS:
        return TW_ALIAS[raw]
    if up in TW_ALIAS:
        return TW_ALIAS[up]
    if up.startswith("^"):
        return up
    if "." in up:
        return up
    if up.isdigit():
        return f"{up}.TW"
    if len(up) >= 5 and up[:4].isdigit() and (up.endswith("L") or up.endswith("R")):
        return f"{up}.TW"
    return up


def is_etf(symbol: str) -> bool:
    s = normalize_symbol(symbol).replace(".TW", "")
    return s.startswith("00") or s in {"SPY", "QQQ", "TQQQ", "SQQQ"}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return DEFAULT_CONFIG.copy()
    CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2), encoding="utf-8")
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict) -> None:
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        # Streamlit Cloud 檔案系統可能不適合長期保存使用者修改。
        pass


def safe_float(x) -> float:
    try:
        if pd.isna(x):
            return np.nan
        return float(x)
    except Exception:
        return np.nan


def fmt_num(x, d: int = 2) -> str:
    x = safe_float(x)
    if np.isnan(x):
        return "-"
    return f"{x:.{d}f}"


def fmt_pct(x) -> str:
    x = safe_float(x)
    if np.isnan(x):
        return "-"
    return f"{x:.2f}%"


def fmt_int(x) -> str:
    x = safe_float(x)
    if np.isnan(x):
        return "-"
    return f"{int(x):,}"


@st.cache_data(ttl=2, show_spinner=False)
def fetch_history(symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    symbol = normalize_symbol(symbol)
    try:
        df = yf.download(
            symbol,
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=False,
        )
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        return df.dropna(how="all")
    except Exception:
        return pd.DataFrame()


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col not in df.columns:
            df[col] = np.nan

    close = df["Close"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)

    df["MA5"] = close.rolling(5).mean()
    df["MA20"] = close.rolling(20).mean()
    df["MA60"] = close.rolling(60).mean()

    low9 = low.rolling(9).min()
    high9 = high.rolling(9).max()
    rsv = (close - low9) / (high9 - low9).replace(0, np.nan) * 100
    df["K"] = rsv.ewm(com=2, adjust=False).mean()
    df["D"] = df["K"].ewm(com=2, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_SIGNAL"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_HIST"] = df["MACD"] - df["MACD_SIGNAL"]
    return df


def get_snapshot(symbol: str) -> dict | None:
    df = add_indicators(fetch_history(symbol, "3mo", "1d"))
    if df.empty:
        return None
    last = df.iloc[-1]
    if len(df) >= 2:
        prev = df.iloc[-2]
        chg = safe_float(last["Close"]) - safe_float(prev["Close"])
        pct = (safe_float(last["Close"]) / safe_float(prev["Close"]) - 1) * 100 if safe_float(prev["Close"]) else np.nan
    else:
        chg, pct = np.nan, np.nan

    if len(df) >= 31:
        today_vol = safe_float(last["Volume"])
        avg30 = safe_float(df["Volume"].iloc[-31:-1].mean())
        vol_dir = "增" if today_vol > avg30 else "減"
    else:
        vol_dir = "-"

    return {
        "symbol": normalize_symbol(symbol),
        "price": safe_float(last["Close"]),
        "change": chg,
        "pct": pct,
        "volume": safe_float(last["Volume"]),
        "vol_dir": vol_dir,
        "K": safe_float(last.get("K")),
        "D": safe_float(last.get("D")),
        "RSI": safe_float(last.get("RSI")),
        "MACD_HIST": safe_float(last.get("MACD_HIST")),
        "df": df,
    }


def simple_status(snap: dict) -> str:
    score = 0
    if snap["vol_dir"] == "增":
        score += 1
    if not np.isnan(snap["K"]) and not np.isnan(snap["D"]) and snap["K"] > snap["D"]:
        score += 1
    if not np.isnan(snap["pct"]) and snap["pct"] > 0:
        score += 1
    if not np.isnan(snap["RSI"]) and snap["RSI"] > 70:
        return "過熱"
    if score >= 2:
        return "偏多"
    if score == 1:
        return "觀察"
    return "偏弱"


def make_human_summary(symbol: str, snap: dict | None) -> list[str]:
    if not snap:
        return ["資料不足，暫時無法判斷。"]
    bullets = []
    pct, k, d, rsi, vol = snap["pct"], snap["K"], snap["D"], snap["RSI"], snap["vol_dir"]
    if not np.isnan(pct):
        if pct > 1:
            bullets.append("今日價格偏強，短線買盤較積極。")
        elif pct < -1:
            bullets.append("今日價格偏弱，短線賣壓較明顯。")
        else:
            bullets.append("今日價格變動不大，偏向震盪整理。")
    if vol == "增":
        bullets.append("成交量高於近30日均量，代表市場關注度提高。")
    elif vol == "減":
        bullets.append("成交量低於近30日均量，代表追價力道較保守。")
    if not np.isnan(k) and not np.isnan(d):
        bullets.append("KD 目前偏多，短線動能較有利。" if k > d else "KD 目前偏弱，短線動能仍需觀察。")
    if not np.isnan(rsi):
        if rsi > 70:
            bullets.append("RSI 高於70，短線有過熱風險。")
        elif rsi < 30:
            bullets.append("RSI 低於30，短線有超跌反彈機會。")
        else:
            bullets.append("RSI 位於中性區，尚未明顯過熱或過冷。")
    if snap["MACD_HIST"] == snap["MACD_HIST"]:
        bullets.append("MACD 柱狀體偏正，趨勢仍有支撐。" if snap["MACD_HIST"] > 0 else "MACD 柱狀體偏負，趨勢尚未完全轉強。")
    return bullets[:6]


def make_price_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    plot_df = df.tail(160).copy()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df["Close"], mode="lines", name="Close", line=dict(width=2)))
    for ma in ["MA5", "MA20", "MA60"]:
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df[ma], mode="lines", name=ma, line=dict(width=1.4)))
    fig.update_layout(
        title=f"{symbol} 價格 / 均線",
        template="plotly_dark",
        height=430,
        margin=dict(l=10, r=10, t=45, b=10),
        legend=dict(orientation="h"),
    )
    return fig


def make_indicator_chart(df: pd.DataFrame) -> go.Figure:
    plot_df = df.tail(160).copy()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df["K"], mode="lines", name="K"))
    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df["D"], mode="lines", name="D"))
    fig.add_hline(y=80, line_dash="dash")
    fig.add_hline(y=20, line_dash="dash")
    fig.update_layout(template="plotly_dark", height=300, margin=dict(l=10, r=10, t=30, b=10), title="KD")
    return fig


def make_macd_chart(df: pd.DataFrame) -> go.Figure:
    plot_df = df.tail(160).copy()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=plot_df.index, y=plot_df["MACD_HIST"], name="MACD Hist"))
    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df["MACD"], mode="lines", name="MACD"))
    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df["MACD_SIGNAL"], mode="lines", name="Signal"))
    fig.update_layout(template="plotly_dark", height=300, margin=dict(l=10, r=10, t=30, b=10), title="MACD")
    return fig


def make_volume_chart(df: pd.DataFrame) -> go.Figure:
    plot_df = df.tail(160).copy()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=plot_df.index, y=plot_df["Volume"], name="Volume"))
    fig.update_layout(template="plotly_dark", height=270, margin=dict(l=10, r=10, t=30, b=10), title="成交量")
    return fig


def build_snapshot_table(symbols: list[str]) -> pd.DataFrame:
    rows = []
    for sym in symbols:
        sym = normalize_symbol(sym)
        snap = get_snapshot(sym)
        if not snap:
            rows.append({"標的": sym, "價格": "-", "漲跌%": "-", "成交量": "-", "30日量": "-", "KD": "-", "RSI": "-", "狀態": "-"})
            continue
        rows.append(
            {
                "標的": sym,
                "價格": fmt_num(snap["price"]),
                "漲跌%": fmt_pct(snap["pct"]),
                "成交量": fmt_int(snap["volume"]),
                "30日量": snap["vol_dir"],
                "KD": f'{fmt_num(snap["K"], 1)}/{fmt_num(snap["D"], 1)}',
                "RSI": fmt_num(snap["RSI"], 1),
                "狀態": simple_status(snap),
            }
        )
    return pd.DataFrame(rows)


def strategy_text(symbols: list[str]) -> str:
    rows = []
    for sym in symbols:
        snap = get_snapshot(sym)
        if not snap:
            continue
        score = 0
        if snap["vol_dir"] == "增":
            score += 2
        if not np.isnan(snap["K"]) and not np.isnan(snap["D"]) and snap["K"] > snap["D"]:
            score += 2
        if not np.isnan(snap["pct"]) and snap["pct"] > 0:
            score += 1
        if not np.isnan(snap["RSI"]) and 45 <= snap["RSI"] <= 75:
            score += 1
        rows.append((score, normalize_symbol(sym), snap))
    rows.sort(reverse=True, key=lambda x: x[0])
    stocks = [(s, snap, sc) for sc, s, snap in rows if not is_etf(s)][:5]
    etfs = [(s, snap, sc) for sc, s, snap in rows if is_etf(s)][:5]

    lines = ["這不是買進建議，只是根據量價與技術指標篩出較值得觀察的標的。", ""]
    lines.append("個股觀察：")
    if not stocks:
        lines.append("• 暫無足夠資料。")
    for s, snap, sc in stocks:
        lines.append(f"• {s}｜分數 {sc}｜現價 {fmt_num(snap['price'])}｜停損參考 {fmt_num(snap['price']*0.985)}｜停利參考 {fmt_num(snap['price']*1.025)}")
    lines.append("")
    lines.append("ETF觀察：")
    if not etfs:
        lines.append("• 暫無足夠資料。")
    for s, snap, sc in etfs:
        lines.append(f"• {s}｜分數 {sc}｜現價 {fmt_num(snap['price'])}｜停損參考 {fmt_num(snap['price']*0.985)}｜停利參考 {fmt_num(snap['price']*1.025)}")
    lines.extend(["", "放棄條件：", "• 開盤急殺且無承接。", "• 成交量明顯縮小。", "• KD轉弱且跌破重要均線。", "• 正2類標的若大盤連續破底，不宜硬凹。"])
    return "\n".join(lines)


if "cfg" not in st.session_state:
    st.session_state.cfg = load_config()
if "current_symbol" not in st.session_state:
    st.session_state.current_symbol = "^TWII"

cfg = st.session_state.cfg

st.title("TW / US AI Stock Dashboard")
st.markdown("<div class='small'>LIVE DARK · 手機可開 · 數字局部2秒刷新 · 台股 / 美股 / ETF · 圖像化解讀</div>", unsafe_allow_html=True)
st.caption("頁面本身不整頁刷新；只有大盤、自選股與即時數字區塊會局部更新。")

with st.sidebar:
    st.header("自選股設定")
    pages = list(cfg.get("pages", DEFAULT_CONFIG["pages"]).keys())
    page = st.selectbox("選擇頁面", pages, index=0)
    new_symbol = st.text_input("新增標的", placeholder="2330 / 0050 / 台積電 / AAPL")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("新增", use_container_width=True):
            sym = normalize_symbol(new_symbol)
            if sym and sym not in cfg["pages"][page]:
                cfg["pages"][page].append(sym)
                save_config(cfg)
                st.rerun()
    with c2:
        if st.button("清除快取", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    current_list = cfg["pages"].get(page, [])
    remove_symbol = st.selectbox("刪除標的", [""] + current_list)
    if st.button("刪除選取", use_container_width=True) and remove_symbol:
        cfg["pages"][page] = [x for x in current_list if x != remove_symbol]
        save_config(cfg)
        st.rerun()

    selected_symbol = st.selectbox("目前查看", ["^TWII"] + current_list + ["AAPL", "MSFT", "NVDA", "QQQ"], index=0)
    if selected_symbol:
        st.session_state.current_symbol = normalize_symbol(selected_symbol)


# 只刷新數字區塊，不刷新整個頁面。
# st.fragment 會讓這個區塊每 2 秒局部重跑，圖表與頁面框架不會整頁跳動。
@st.fragment(run_every=2)
def live_number_panel(page_name: str, selected_symbol: str):
    st.subheader("大盤即時追蹤")
    st.caption(f"數字更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}｜注意：yfinance 台股常有 15～20 分鐘延遲。")

    market_df = build_snapshot_table(list(MARKETS.values()))
    market_df.insert(0, "市場", list(MARKETS.keys()))
    st.dataframe(market_df, use_container_width=True, hide_index=True)

    st.subheader(f"{page_name} 自選股")
    watch_df = build_snapshot_table(cfg["pages"].get(page_name, []))
    st.dataframe(watch_df, use_container_width=True, hide_index=True)

    snap_live = get_snapshot(selected_symbol)
    st.subheader(f"即時數字：{selected_symbol}")
    if not snap_live:
        st.warning("目前抓不到資料，可能是代號錯誤、資料源暫時無回應，或市場資料尚未更新。")
        return

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("價格", fmt_num(snap_live["price"]), fmt_num(snap_live["change"]))
    kpi2.metric("漲跌%", fmt_pct(snap_live["pct"]))
    kpi3.metric("成交量", fmt_int(snap_live["volume"]), snap_live["vol_dir"])
    kpi4.metric("狀態", simple_status(snap_live))

    kpi5, kpi6, kpi7, kpi8 = st.columns(4)
    kpi5.metric("KD", f'{fmt_num(snap_live["K"], 1)}/{fmt_num(snap_live["D"], 1)}')
    kpi6.metric("RSI", fmt_num(snap_live["RSI"], 1))
    kpi7.metric("MACD Hist", fmt_num(snap_live["MACD_HIST"], 3))
    kpi8.metric("30日量", snap_live["vol_dir"])

    st.markdown("### 人類可讀解讀")
    for item in make_human_summary(selected_symbol, snap_live):
        st.markdown(f"- {item}")


symbol = st.session_state.current_symbol
live_number_panel(page, symbol)

st.subheader(f"圖表區：{symbol}")
st.caption("圖表不每 2 秒重畫，避免手機畫面閃爍與看不到內容。切換標的或按清除快取後會重新載入圖表。")
df1y = add_indicators(fetch_history(symbol, "1y", "1d"))
if df1y.empty:
    st.warning("目前抓不到圖表資料。")
else:
    st.plotly_chart(make_price_chart(df1y, symbol), use_container_width=True)
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(make_indicator_chart(df1y), use_container_width=True)
    with col_b:
        st.plotly_chart(make_macd_chart(df1y), use_container_width=True)
    st.plotly_chart(make_volume_chart(df1y), use_container_width=True)

@st.fragment(run_every=10)
def strategy_panel():
    st.subheader("本機策略解讀")
    all_symbols = []
    for arr in cfg["pages"].values():
        all_symbols.extend(arr)
    all_symbols = list(dict.fromkeys(all_symbols))
    st.text(strategy_text(all_symbols))

strategy_panel()

st.markdown("---")
st.caption("資料來源：Yahoo Finance via yfinance。此網站僅供研究與看盤輔助，不構成投資建議。")
