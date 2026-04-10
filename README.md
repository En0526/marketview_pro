# MarketView En - 完整功能網站（本機版）

這個版本是和我本人使用的版本一樣、具備完整功能的網站。  
只要照以下步驟下載並啟動，就可以在本機觀看與使用。

與 `trading_system` 功能相同，**全部資料來源為 Yahoo Finance (yfinance)**，無需 Finnhub / Binance / Twelve Data API key。

---

一個智能交易系統，具備擇時功能和策略自動匹配能力。

## 功能特色

- 📊 **市場監控**: 即時顯示美股、台股及主要國際市場盤勢
- ⏰ **擇時功能**: 智能判斷最佳交易時機
- 🎯 **策略匹配**: 自動選擇最適合當前市場環境的交易策略
- 🌐 **Web 介面**: 一目了然的市場數據展示

## 專案結構

```
trading_system/
├── app.py                 # Flask 主應用
├── config.py             # 配置文件
├── market_data/          # 市場數據模組
│   ├── __init__.py
│   ├── data_fetcher.py   # 數據獲取
│   └── market_analyzer.py # 市場分析
├── timing/               # 擇時模組
│   ├── __init__.py
│   └── timing_selector.py
├── strategy/             # 策略模組
│   ├── __init__.py
│   └── strategy_matcher.py
├── templates/            # HTML 模板
│   └── index.html
├── static/               # 靜態資源
│   ├── css/
│   └── js/
└── requirements.txt      # 依賴套件
```

## 安裝與使用

### 1. 下載專案

```bash
git clone https://github.com/En0526/marketview_pro.git
cd marketview_pro
```

### 2. 安裝依賴

```bash
pip install -r requirements.txt
```

### 3. 運行應用

```bash
python app.py
```

### 4. 訪問網站

打開瀏覽器訪問: http://localhost:5000

## 快速開始

### 1. 安裝依賴套件

```bash
pip install -r requirements.txt
```

### 2. 啟動應用程式

```bash
python app.py
```

### 3. 訪問網站

打開瀏覽器訪問: `http://localhost:5000`

## 詳細說明

請參考 [`使用說明.md`](使用說明.md) 了解每個 Python 檔案的詳細功能和使用方法。

## 開發計劃

- [x] 基礎環境設置
- [x] 市場數據獲取
- [x] Web 介面
- [x] 擇時功能實現
- [x] 策略匹配算法
- [ ] 回測系統
- [ ] 風險管理模組
- [ ] 更多技術指標
- [ ] 歷史數據分析

## 技術棧

- **後端**: Python, Flask
- **數據**: yfinance, pandas
- **前端**: HTML, CSS, JavaScript
- **圖表**: Chart.js

## License

MIT

