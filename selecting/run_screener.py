"""
命令列執行選股策略
用法：cd D:\\marketview_En && python -m selecting.run_screener
"""
import sys
import os
from pathlib import Path

# SSL 憑證（與 app.py 一致，避免 requests 連線 FinMind 時 SSL 錯誤）
try:
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
except ImportError:
    pass

# 專案根目錄
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from selecting.stock_screener import run_screener

if __name__ == "__main__":
    print("策略1：毛利率連續3季>30%且成長 + 近三月營收年增每個月>20% + 5MA>20MA")
    print("篩選中（上市櫃數千檔，約 3–5 分鐘）...")
    results, warnings = run_screener()
    if warnings:
        for w in warnings:
            print(f"⚠ {w}")
    print(f"\n符合條件：{len(results)} 檔")
    for r in results:
        margins = " → ".join(f"{m}%" for m in (r.get("gross_margin_quarters") or []))
        yoy_months = r.get("revenue_yoy_months")
        yoy_str = ("  營收年增(逐月): " + " / ".join(f"{m}%" for m in yoy_months)) if yoy_months else ""
        print(f"  {r['stock_id']} {r['name']}  近3季毛利率: {margins}{yoy_str}")
    if not results:
        print("（無符合標的，可檢查 FinMind 連線或調整條件）")
