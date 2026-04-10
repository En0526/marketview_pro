"""
快速檢查 2449 是否符合策略1 各項條件
用法：cd D:\\marketview_En && python -m selecting.check_2449
"""
import sys
import os
from pathlib import Path

try:
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from selecting.stock_screener import (
    get_gross_margin_quarterly,
    check_gross_margin_criteria,
    get_revenue_yoy_last_3m,
    check_revenue_yoy_criteria,
    get_ma_condition,
    get_stock_name,
)

STOCK_ID = "2449"

def main():
    print(f"=== 檢查 {STOCK_ID} ({get_stock_name(STOCK_ID)}) ===\n")

    # 1. 毛利率
    df = get_gross_margin_quarterly(STOCK_ID, quarters=6)
    if df is None or df.empty:
        print("❌ 毛利率：無財報資料")
    else:
        print("毛利率（近6季）:")
        for _, row in df.iterrows():
            print(f"  {row['date']}: {row['gross_margin_pct']}%")
        passed = check_gross_margin_criteria(df, min_pct=30, min_quarters=3)
        last3 = df.tail(3)["gross_margin_pct"].tolist()
        print(f"  近3季: {last3}")
        print(f"  條件(>30%且持續成長): {'✓ 通過' if passed else '❌ 未通過'}\n")

    # 2. 營收年增（每個月都要 > 20%）
    result = get_revenue_yoy_last_3m(STOCK_ID)
    if result is None:
        print("❌ 營收年增：無月營收資料或不足6個月")
    else:
        yoy_list, _ = result
        passed = all(y > 20 for y in yoy_list)
        print(f"近三月營收年成長率(逐月): {' / '.join(f'{y}%' for y in yoy_list)}")
        print(f"  條件(每個月>20%): {'✓ 通過' if passed else '❌ 未通過'}\n")

    # 3. 5MA > 20MA
    ma_ok = get_ma_condition(STOCK_ID)
    print(f"5MA > 20MA: {'✓ 通過' if ma_ok else '❌ 未通過'}\n")

    # 4. 單檔執行結果
    from selecting.stock_screener import run_screener
    results, warnings = run_screener(stock_ids=[STOCK_ID])
    if warnings:
        for w in warnings:
            print(f"⚠ {w}")
    print(f"run_screener(stock_ids=['{STOCK_ID}']): {len(results)} 檔")
    if results:
        print(f"  {results[0]}")
    else:
        print("  （未通過）")

if __name__ == "__main__":
    main()
