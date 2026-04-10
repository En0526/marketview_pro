"""
檢查 FinMind TaiwanStockInfo 連線
執行：cd D:\\marketview_En && python -m selecting.check_finmind
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

def main():
    token = os.environ.get("FINMIND_TOKEN", "").strip()
    print(f"FINMIND_TOKEN 已設定: {'是' if token else '否'}")
    if not token:
        print("\n請在 D:\\marketview_En\\.env 設定 FINMIND_TOKEN")
        print("到 https://finmindtrade.com/ 登入後取得 API 金鑰")
        return

    from selecting.stock_screener import check_finmind_api_status
    print("\n正在檢查 FinMind API 狀態...")
    ok, err_msg = check_finmind_api_status()
    if ok:
        print("✓ FinMind API 正常，可取得資料")
    else:
        print(f"✗ {err_msg}")
        if "402" in (err_msg or ""):
            print("\n402 = API 用量已達上限，請稍後再試或至 finmindtrade.com 升級方案")

if __name__ == "__main__":
    main()
