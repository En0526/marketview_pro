# 選股策略（台股）

## 策略條件

1. **基本面**：連續 3 季（或以上）毛利率 > 30%，且每季持續成長  
2. **營收**：近三月營收年增**每個月**都要 > 20%  
3. **技術面**：日 K 線 5 日均線 > 20 日均線  

## 資料來源

- **FinMind**：綜合損益表（GrossProfit、CostOfGoodsSold）→ 計算毛利率  
- **yfinance**：股價歷史 → 計算 5MA、20MA  

## 使用方式

### 命令列

```bash
cd D:\marketview_En
python -m selecting.run_screener
```

### 作為模組

```python
from selecting.stock_screener import run_screener

results, warnings = run_screener(min_gross_margin=30, min_quarters=3)
for r in results:
    print(r["stock_id"], r["name"], r["gross_margin_quarters"])
if warnings:
    print("⚠", warnings)
```

## 環境變數

- `FINMIND_TOKEN`：FinMind API Token（必填）。免費 600 次/時。
- `FINMIND_TOKEN_2`：第二個金鑰（選填）。可設第二帳號金鑰，額度用盡時自動輪替；兩金鑰都用完會停止並回報已篩選檔數。

## 篩選標的

預設篩選約 70 檔台股上市櫃公司（`DEFAULT_STOCK_IDS`）。可於 `stock_screener.py` 擴充 `DEFAULT_STOCK_IDS` 或傳入自訂清單。
