# TW AI DayTrader Pro

手機可開的 Streamlit 股票看盤網站。

## 這一版更新
- 標的名稱改成中文顯示，例如：台積電 (2330)、鴻海 (2317)。
- 當沖推薦只篩選台股，不會推薦美股。
- 新增台股當沖排行榜 Top 10。
- 保留數字區塊每 2 秒局部更新，不會整頁刷新。
- 圖表區不會每 2 秒重畫，避免手機畫面一直跳動。

## 本機執行
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud 設定
- Repository: tw-us-ai-stock-dashboard
- Branch: main
- Main file path: app.py

## 注意
- yfinance 台股資料常有 15～20 分鐘延遲，不是真正交易所即時報價。
- 當沖排行是技術指標排序，不是買賣建議。
