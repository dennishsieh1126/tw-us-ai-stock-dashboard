# TW / US AI Stock Web Dashboard

免費部署方式：GitHub + Streamlit Community Cloud。

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
- yfinance 台股資料可能延遲 15～20 分鐘，不是真正交易所即時報價。
- 網站每 2 秒自動刷新畫面，但資料源本身不一定每 2 秒更新。
