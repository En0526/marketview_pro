# MarketView En - 完整功能網站（本機版）

**本專案核心賣點：AI 盤勢摘要** — 首頁「新聞聲量 · 盤前 · **AI 速覽**」區塊**串接 LLM API**，把即時／當日的**新聞聲量、台美股盤前脈絡與主要指標簡報**自動打成**一篇可快速閱讀的每日盤勢／市場摘要**；在多數資料看板之上，這裡是直接幫你做「統整判讀」的**最重點功能**。  
（後端：`news_analysis/ai_digest.py`；API 金鑰見下方說明。）

與作者日常使用的版本相同：**在本機跑滿資料抓取與運算**，不受雲端 IP 限制，**台股／國際報價、新聞與盤前等區塊可正常發揮**。

- **本機完整版（本 repo）**：clone 後 `python app.py`，開 `http://localhost:5000`。
- **雲端示意版（免安裝試用）**：[https://trading-system-kkhs.onrender.com/](https://trading-system-kkhs.onrender.com/) — 功能受雲端與資料源限制較多，僅供快速體驗介面。

資料以 **Yahoo Finance (yfinance)** 等為主，無需 Finnhub / Binance / Twelve Data API key 即可跑通主要流程。

### AI 速覽（LLM）環境設定（想用「AI 盤勢摘要」必設其一）

優先：**`GEMINI_API_KEY`**（可選 `GEMINI_MODEL`，預設 `gemini-2.5-flash`）；若未設定 Gemini，則可走 **OpenAI 相容**：`OPENAI_API_KEY`、`OPENAI_BASE_URL`（選填）、`OPENAI_MODEL`。建議將變數寫入專案根目錄 **`.env`**（可參考 `.env.example`）。

---

## 首頁「看盤」各區塊（一頁整合）

以下首列為**本站最重點**；其餘為行情、法人與研究輔助。

| 區塊 | 你做得到的事 |
|------|----------------|
| **新聞聲量 · 盤前 · AI 速覽**（核心） | 24h 新聞關鍵詞聲量、可展開連結；**台股／美股盤前**分區更新；**串接 LLM**（Gemini／OpenAI 相容）自動產出**每日盤勢／要點摘要** — **最快掌握重大資訊的入口** |
| **美股市場** | 主要指數與個股報價、財報行事曆；一鍵更新 |
| **台股市場** | 台股報價、60 天內財報行事曆；與大盤同步掌握 |
| **國際 · ETF · 金屬 · 加密 · 比率** | 國際指數；美股／台股 ETF（如 VOO、QQQ、0050）；COMEX 重金屬；加密 24h；**重要比率**可點進看走勢圖 |
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

- **★ AI 盤勢摘要（最重點）**：**LLM API** 整合；輸入當批新聞聲量、盤前與市場快照，輸出**結構化的每日／當波段速讀結論**，與「只列資料」截然不同，是本專案**首要差異化能力**
- **市場監控**：美股、台股、國際與商品同一視窗，更新時間與按鈕分區清楚
- **擇時／情境**：配合盤前、新聲量、總經與法說時間軸，快速對照當日環境（亦為 AI 摘要的輸入脈絡）
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
├── news_analysis/         # 新聞／盤前、`ai_digest.py`（AI 盤勢摘要）
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
- **AI／摘要**: Gemini API / OpenAI 相容 Chat（盤勢與新聞統整，`ai_digest.py`）
- **前端**: HTML, CSS, JavaScript  
- **圖表**: Chart.js  

## License

MIT
