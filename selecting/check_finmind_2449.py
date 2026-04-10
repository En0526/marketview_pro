"""
檢查 FinMind 對 2449 的資料回傳
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

try:
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from selecting.stock_screener import _finmind_request

STOCK_ID = "2449"
end = datetime.now()
start = end - timedelta(days=400)

print("=== FinMind 2449 財報 (TaiwanStockFinancialStatements) ===")
rows = _finmind_request(
    "TaiwanStockFinancialStatements",
    data_id=STOCK_ID,
    start_date=start.strftime("%Y-%m-%d"),
    end_date=end.strftime("%Y-%m-%d"),
)
print(f"筆數: {len(rows)}")
if rows:
    types = set(r.get("type") for r in rows)
    print(f"type 種類: {types}")
    gp = [r for r in rows if r.get("type") == "GrossProfit"]
    cogs = [r for r in rows if r.get("type") == "CostOfGoodsSold"]
    print(f"GrossProfit 筆數: {len(gp)}, CostOfGoodsSold 筆數: {len(cogs)}")
    if gp:
        print("GrossProfit 範例:", gp[:3])

print("\n=== FinMind 2449 月營收 (TaiwanStockMonthRevenue) ===")
rows2 = _finmind_request(
    "TaiwanStockMonthRevenue",
    data_id=STOCK_ID,
    start_date=start.strftime("%Y-%m-%d"),
    end_date=end.strftime("%Y-%m-%d"),
)
print(f"筆數: {len(rows2)}")
if rows2:
    print("最近幾筆:", rows2[:5])

# 對比：2330 台積電
print("\n=== 對比 2330 台積電 財報 ===")
rows2330 = _finmind_request(
    "TaiwanStockFinancialStatements",
    data_id="2330",
    start_date=start.strftime("%Y-%m-%d"),
    end_date=end.strftime("%Y-%m-%d"),
)
print(f"2330 財報筆數: {len(rows2330)}")
