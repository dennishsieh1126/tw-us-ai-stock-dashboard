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



TW_NAME_MAP = {
    "^TWII": "台股加權指數",
    "2330.TW": "台積電",
    "2317.TW": "鴻海",
    "2454.TW": "聯發科",
    "2382.TW": "廣達",
    "3231.TW": "緯創",
    "2303.TW": "聯電",
    "2308.TW": "台達電",
    "2412.TW": "中華電",
    "2881.TW": "富邦金",
    "2882.TW": "國泰金",
    "2884.TW": "玉山金",
    "2891.TW": "中信金",
    "2892.TW": "第一金",
    "2603.TW": "長榮",
    "2609.TW": "陽明",
    "2615.TW": "萬海",
    "2002.TW": "中鋼",
    "1301.TW": "台塑",
    "1303.TW": "南亞",
    "3711.TW": "日月光投控",
    "2357.TW": "華碩",
    "2356.TW": "英業達",
    "2324.TW": "仁寶",
    "2376.TW": "技嘉",
    "2377.TW": "微星",
    "3017.TW": "奇鋐",
    "3661.TW": "世芯-KY",
    "3443.TW": "創意",
    "3034.TW": "聯詠",
    "3008.TW": "大立光",
    "8046.TW": "南電",
    "3037.TW": "欣興",
    "0050.TW": "元大台灣50",
    "006208.TW": "富邦台50",
    "00631L.TW": "元大台灣50正2",
    "00632R.TW": "元大台灣50反1",
}

US_NAME_MAP = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "TSLA": "Tesla",
    "AMD": "AMD",
    "SPY": "SPDR S&P 500 ETF",
    "QQQ": "Invesco QQQ",
    "TQQQ": "ProShares 三倍做多QQQ",
    "SQQQ": "ProShares 三倍做空QQQ",
    "^IXIC": "Nasdaq 指數",
    "^GSPC": "S&P 500 指數",
    "^SOX": "費半指數",
}

DAYTRADE_UNIVERSE = [
    "2330.TW", "2317.TW", "2454.TW", "2382.TW", "3231.TW", "2303.TW",
    "2308.TW", "2376.TW", "2377.TW", "3017.TW", "3661.TW", "3443.TW",
    "3034.TW", "3037.TW", "8046.TW", "2357.TW", "2356.TW", "2324.TW",
    "2603.TW", "2609.TW", "2615.TW", "2881.TW", "2882.TW", "2891.TW",
]


def display_symbol(symbol: str) -> str:
    s = normalize_symbol(symbol)
    name = TW_NAME_MAP.get(s) or US_NAME_MAP.get(s)
    if s.endswith(".TW"):
        code = s.replace(".TW", "")
        return f"{name} ({code})" if name else code
    if s == "^TWII":
        return name or "台股加權指數"
    return f"{name} ({s})" if name else s


def is_tw_symbol(symbol: str) -> bool:
    s = normalize_symbol(symbol)
    return s == "^TWII" or s.endswith(".TW")


def is_tw_stock(symbol: str) -> bool:
    s = normalize_symbol(symbol)
    code = s.replace(".TW", "")
    return s.endswith(".TW") and code.isdigit() and not code.startswith("00")

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

    today_vol = safe_float(last["Volume"])
    avg30 = safe_float(df["Volume"].iloc[-31:-1].mean()) if len(df) >= 31 else np.nan
    vol_ratio = today_vol / avg30 if avg30 and not np.isnan(avg30) else np.nan
    close_price = safe_float(last["Close"])
    range_pct = (safe_float(last["High"]) - safe_float(last["Low"])) / close_price * 100 if close_price else np.nan

    return {
        "symbol": normalize_symbol(symbol),
        "display": display_symbol(symbol),
        "price": close_price,
        "change": chg,
        "pct": pct,
        "volume": today_vol,
        "avg30_volume": avg30,
        "vol_ratio": vol_ratio,
        "range_pct": range_pct,
        "vol_dir": vol_dir,
        "K": safe_float(last.get("K")),
        "D": safe_float(last.get("D")),
        "RSI": safe_float(last.get("RSI")),
        "MACD_HIST": safe_float(last.get("MACD_HIST")),
        "MA5": safe_float(last.get("MA5")),
        "MA20": safe_float(last.get("MA20")),
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
        title=f"{display_symbol(symbol)} 價格 / 均線",
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
            rows.append({"標的": display_symbol(sym), "代號": sym, "價格": "-", "漲跌%": "-", "成交量": "-", "量比": "-", "KD": "-", "RSI": "-", "狀態": "-"})
            continue
        rows.append(
            {
                "標的": snap.get("display", display_symbol(sym)),
                "代號": sym,
                "價格": fmt_num(snap["price"]),
                "漲跌%": fmt_pct(snap["pct"]),
                "成交量": fmt_int(snap["volume"]),
                "量比": fmt_num(snap.get("vol_ratio"), 2),
                "KD": f'{fmt_num(snap["K"], 1)}/{fmt_num(snap["D"], 1)}',
                "RSI": fmt_num(snap["RSI"], 1),
                "狀態": simple_status(snap),
            }
        )
    return pd.DataFrame(rows)


def daytrade_score(snap: dict) -> tuple[int, list[str]]:
    score = 0
    reasons = []
    price = snap["price"]
    vol_ratio = snap.get("vol_ratio", np.nan)
    range_pct = snap.get("range_pct", np.nan)

    if not np.isnan(vol_ratio):
        if vol_ratio >= 2.0:
            score += 28; reasons.append("量比大於2，市場關注度高")
        elif vol_ratio >= 1.3:
            score += 18; reasons.append("量能較近30日均量放大")
        elif vol_ratio >= 1.0:
            score += 10; reasons.append("量能略高於均量")

    if not np.isnan(snap["pct"]):
        if 0.3 <= snap["pct"] <= 5.0:
            score += 18; reasons.append("漲幅落在可追蹤區間")
        elif -1.0 <= snap["pct"] < 0.3:
            score += 8; reasons.append("價格偏整理，可等待突破")
        elif snap["pct"] > 5.0:
            score += 5; reasons.append("漲幅偏大，追高風險增加")

    if not np.isnan(range_pct):
        if 1.0 <= range_pct <= 5.5:
            score += 18; reasons.append("日內波動足夠，較有當沖空間")
        elif range_pct > 5.5:
            score += 8; reasons.append("波動很大，需嚴格停損")

    if not np.isnan(snap["K"]) and not np.isnan(snap["D"]):
        if snap["K"] > snap["D"] and snap["K"] < 85:
            score += 16; reasons.append("KD偏多但尚未極端過熱")
        elif snap["K"] > snap["D"]:
            score += 8; reasons.append("KD偏多但短線偏熱")

    if not np.isnan(snap["RSI"]):
        if 45 <= snap["RSI"] <= 68:
            score += 14; reasons.append("RSI位於較健康的強勢區")
        elif 68 < snap["RSI"] <= 78:
            score += 6; reasons.append("RSI偏熱，適合等拉回")

    if price and not np.isnan(snap.get("MA5", np.nan)) and price > snap["MA5"]:
        score += 6; reasons.append("價格站上5日均線")
    if price and not np.isnan(snap.get("MA20", np.nan)) and price > snap["MA20"]:
        score += 4; reasons.append("價格站上20日均線")

    return min(score, 100), reasons[:4]


def daytrade_label(score: int) -> str:
    if score >= 85:
        return "★★★★★ 適合當沖觀察"
    if score >= 75:
        return "★★★★ 可列入觀察"
    if score >= 60:
        return "★★★ 僅觀察"
    return "★★ 不建議追"


def build_daytrade_rank(symbols: list[str]) -> pd.DataFrame:
    candidates = []
    # 使用者自選台股 + 內建熱門台股，避免美股進入當沖推薦。
    for sym in list(dict.fromkeys(symbols + DAYTRADE_UNIVERSE)):
        sym = normalize_symbol(sym)
        if not is_tw_stock(sym):
            continue
        snap = get_snapshot(sym)
        if not snap:
            continue
        score, reasons = daytrade_score(snap)
        candidates.append({
            "排名分數": score,
            "標的": snap.get("display", display_symbol(sym)),
            "代號": sym.replace(".TW", ""),
            "現價": fmt_num(snap["price"]),
            "漲跌%": fmt_pct(snap["pct"]),
            "量比": fmt_num(snap.get("vol_ratio"), 2),
            "日內振幅%": fmt_pct(snap.get("range_pct")),
            "KD": f'{fmt_num(snap["K"], 1)}/{fmt_num(snap["D"], 1)}',
            "RSI": fmt_num(snap["RSI"], 1),
            "評語": daytrade_label(score),
            "理由": "、".join(reasons) if reasons else "資料中性",
            "停損參考": fmt_num(snap["price"] * 0.985),
            "停利參考": fmt_num(snap["price"] * 1.025),
        })
    if not candidates:
        return pd.DataFrame()
    return pd.DataFrame(candidates).sort_values("排名分數", ascending=False).head(10).reset_index(drop=True)


def strategy_text(symbols: list[str]) -> str:
    rank = build_daytrade_rank(symbols)
    lines = ["【台股當沖觀察】", "以下只篩選台股，不會推薦美股。這不是買進建議，請搭配大盤、成交量與停損紀律。", ""]
    if rank.empty:
        return "\n".join(lines + ["目前沒有足夠的台股資料可排序。"])

    for i, row in rank.head(5).iterrows():
        lines.append(f"{i+1}. {row['標的']}｜分數 {row['排名分數']}｜{row['評語']}")
        lines.append(f"   現價 {row['現價']}｜漲跌 {row['漲跌%']}｜量比 {row['量比']}｜RSI {row['RSI']}")
        lines.append(f"   理由：{row['理由']}")
        lines.append(f"   參考區：停損 {row['停損參考']}；停利 {row['停利參考']}")
        lines.append("")

    lines.extend(["放棄條件：", "• 大盤急殺或台股加權指數翻黑。", "• 量比突然縮小，價格跌破開盤價。", "• KD轉弱且跌破5日均線。", "• 已漲超過5%但量能沒有延續，不追高。"])
    return "\n".join(lines)


if "cfg" not in st.session_state:
    st.session_state.cfg = load_config()
if "current_symbol" not in st.session_state:
    st.session_state.current_symbol = "^TWII"

cfg = st.session_state.cfg

st.title("TW AI DayTrader Pro")
st.markdown("<div class='small'>LIVE DARK · 手機可開 · 數字局部2秒刷新 · 中文標的 · 台股當沖排行</div>", unsafe_allow_html=True)
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

    selected_symbol = st.selectbox(
        "目前查看",
        ["^TWII"] + current_list + ["AAPL", "MSFT", "NVDA", "QQQ"],
        index=0,
        format_func=display_symbol,
    )
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
    st.subheader(f"即時數字：{display_symbol(selected_symbol)}")
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

st.subheader(f"圖表區：{display_symbol(symbol)}")
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
    st.subheader("台股當沖排行榜")
    all_symbols = []
    for arr in cfg["pages"].values():
        all_symbols.extend(arr)
    all_symbols = list(dict.fromkeys(all_symbols))
    rank = build_daytrade_rank(all_symbols)
    if rank.empty:
        st.warning("目前沒有足夠的台股資料可排序。")
    else:
        st.dataframe(rank, use_container_width=True, hide_index=True)
    st.subheader("本機策略解讀")
    st.text(strategy_text(all_symbols))

strategy_panel()

st.markdown("---")
st.caption("資料來源：Yahoo Finance via yfinance。此網站僅供研究與看盤輔助，不構成投資建議。")
