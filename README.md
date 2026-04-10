# MarketView En - 完整功能網站（本機版）

與作者日常使用的版本相同：**在本機跑滿資料抓取與運算**，不受雲端 IP 限制，**台股／國際報價、新聞與盤前等區塊可正常發揮**。

- **本機完整版（本 repo）**：clone 後 `python app.py`，開 `http://localhost:5000`。
- **雲端示意版（免安裝試用）**：[https://trading-system-kkhs.onrender.com/](https://trading-system-kkhs.onrender.com/) — 功能受雲端與資料源限制較多，僅供快速體驗介面。

資料以 **Yahoo Finance (yfinance)** 等為主，無需 Finnhub / Binance / Twelve Data API key 即可跑通主要流程。

---

## 首頁「看盤」各區塊（一頁整合）

| 區塊 | 你做得到的事 |
|------|----------------|
| **美股市場** | 主要指數與個股報價、財報行事曆；一鍵更新 |
| **台股市場** | 台股報價、60 天內財報行事曆；與大盤同步掌握 |
| **國際 · ETF · 金屬 · 加密 · 比率** | 國際指數；美股／台股 ETF（如 VOO、QQQ、0050）；COMEX 重金屬；加密 24h；**重要比率**可點進看走勢圖 |
| **新聞聲量 · 盤前** | 24h 新聞關鍵詞彙整聲量、可展開新聞連結；**台股／美股盤前**分區更新 |
| **三大法人** | 證交所 BFI82U 累計買賣超視覺化；**支援上傳 CSV** 補資料 |
| **Benchmark 試算** | 自訂起訖日，一次看多市場指數**期間漲跌幅** |
| **法人說明會 · 總經** | 法說時程整理、**CSV 上傳**；美國 **BLS 總經行事曆**連結與事記列表、可寫筆記 |

介面為 **可摺疊區塊 + 分區更新按鈕**，要專心看哪一塊就展開、按需重新整理，不必整頁重載。

---

## 「選股」分頁（台股）

- 獨立頁面：`/selecting`
- **策略篩選範例**：連續毛利率條件、近月營收年增、均線排列（5MA > 20MA）等，**後端多執行緒**掃描科技股池（詳見頁面說明）
- 適合：想從「看盤」切到「**可執行的篩選清單**」時使用

---

## 核心能力（精簡）

- **市場監控**：美股、台股、國際與商品同一視窗，更新時間與按鈕分區清楚
- **擇時／情境**：配合盤前、新聲量、總經與法說時間軸，快速對照當日環境
- **策略與選股**：首頁策略匹配 + 選股頁面條件篩選，兩條路線互補
- **Web 介面**：Chart.js 走勢、表格、上傳與筆記，**單一網址**完成研究流

---

## 專案結構（摘要）

```
marketview_pro/
├── app.py                 # Flask 主程式
├── config.py
├── market_data/           # 行情與資料擷取
├── timing/                # 擇時
├── strategy/              # 策略匹配
├── selecting/             # 選股篩選
├── news_analysis/         # 新聞／盤前等
├── economic_data/         # 總經相關
├── templates/             # index.html、selecting.html
├── static/
└── requirements.txt
```

---

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

瀏覽器開啟：**http://localhost:5000**（看盤）  
選股：**http://localhost:5000/selecting**

---

## 詳細說明

請參考 [`使用說明.md`](使用說明.md)、[`如何啟動系統.md`](如何啟動系統.md)。

## 技術棧

- **後端**: Python, Flask  
- **數據**: yfinance, pandas  
- **前端**: HTML, CSS, JavaScript  
- **圖表**: Chart.js  

## License

MIT
