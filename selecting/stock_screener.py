"""
選股策略1：毛利率連續三月>30%且成長 + 近三月營收年成長率>20% + 日K線 5MA>20MA
資料來源：FinMind（財報、月營收）、yfinance（股價）
"""
import os
# SSL 憑證（獨立執行時避免 requests 連線 FinMind SSL 錯誤）
try:
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
except ImportError:
    pass

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
import requests
import pandas as pd
import yfinance as yf

FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"

# 雙金鑰額度用盡時設為 True，run_screener 會停止並回報
_finmind_quota_exhausted = False


def _get_finmind_tokens() -> List[str]:
    """取得所有 FinMind 金鑰（FINMIND_TOKEN, FINMIND_TOKEN_2）"""
    tokens = []
    try:
        from config import Config
        for key in ("FINMIND_TOKEN", "FINMIND_TOKEN_2"):
            t = getattr(Config, key, "") or os.environ.get(key, "")
            if t and isinstance(t, str) and t.strip():
                tokens.append(t.strip())
    except Exception:
        pass
    if not tokens:
        t = os.environ.get("FINMIND_TOKEN", "").strip()
        if t:
            tokens.append(t)
        t2 = os.environ.get("FINMIND_TOKEN_2", "").strip()
        if t2:
            tokens.append(t2)
    return tokens


def _get_finmind_token() -> str:
    """回傳第一個金鑰（相容舊程式碼）"""
    tokens = _get_finmind_tokens()
    return tokens[0] if tokens else ""

# 排除產業關鍵字（金融、傳產），只保留科技股；電機機械、電器電纜、鋼鐵、汽車已納入
EXCLUDE_INDUSTRY_KEYWORDS = [
    "金融", "保險", "銀行", "證券", "金控",
    "水泥", "食品", "塑膠", "紡織",
    "化學", "玻璃", "造紙", "橡膠",
    "建材", "營造", "營建", "航運", "觀光", "百貨", "貿易",
    "油電",
]

# 台股上市櫃代碼（精選，可擴充；不含指數、ETF、權證）
# 上市：1xxx-2xxx，上櫃：3xxx-6xxx
DEFAULT_STOCK_IDS = [
    "1101", "1102", "1216", "1301", "1303", "1326", "1402", "1476", "2002", "2049",
    "2105", "2201", "2206", "2301", "2303", "2308", "2317", "2324", "2330", "2344",
    "2345", "2353", "2354", "2356", "2357", "2377", "2379", "2382", "2383", "2395",
    "2408", "2409", "2412", "2413", "2439", "2449", "2454", "2474", "2492", "2801",
    "2880", "2881", "2882", "2886", "2890", "2891", "2892", "2912", "3008", "3017",
    "3034", "3037", "3044", "3189", "3231", "3443", "3661", "3711", "4919", "4938",
    "5871", "5876", "6182", "6239", "6415", "6446", "6669", "6670", "6770", "8016",
    "8046", "8150", "8261", "9910",
]


def _finmind_request(dataset: str, data_id: str = "", start_date: str = "", end_date: str = "") -> List[Dict]:
    """呼叫 FinMind API，雙金鑰輪替；全部 402 時設額度用盡並回傳 []"""
    global _finmind_quota_exhausted
    params_base = {"dataset": dataset}
    if data_id:
        params_base["data_id"] = data_id
    if start_date:
        params_base["start_date"] = start_date
    if end_date:
        params_base["end_date"] = end_date

    tokens = _get_finmind_tokens()
    if not tokens:
        return []

    for token in tokens:
        params = dict(params_base)
        if token:
            params["token"] = token
        headers = {"Authorization": f"Bearer {token}"} if token else None
        try:
            r = requests.get(FINMIND_URL, params=params, headers=headers, timeout=60)
            if r.status_code == 200:
                return r.json().get("data", [])
            if r.status_code == 402:
                continue  # 此金鑰額度用完，嘗試下一個
        except Exception as e:
            continue
    _finmind_quota_exhausted = True
    return []


def check_finmind_api_status() -> Tuple[bool, Optional[str]]:
    """
    檢查 FinMind API 是否可用（爬得到選股所需的財報、月營收）。
    回傳 (是否正常, 錯誤訊息)。
    若回傳 402 表示用量已達上限。
    """
    try:
        # 選股需要財報與月營收，直接檢查這兩個 dataset（2330 為測試用）
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
        token = _get_finmind_token()
        headers = {"Authorization": f"Bearer {token}"} if token else None
        params_base = {"token": token} if token else {}

        for dataset, data_id in [
            ("TaiwanStockFinancialStatements", "2330"),
            ("TaiwanStockMonthRevenue", "2330"),
        ]:
            params = {**params_base, "dataset": dataset, "data_id": data_id, "start_date": start, "end_date": end}
            r = requests.get(FINMIND_URL, params=params, headers=headers, timeout=30)
            if r.status_code == 402:
                return False, "FinMind API 用量已達上限 (402)。請稍後再試，或至 finmindtrade.com 升級方案。"
            if r.status_code != 200:
                return False, f"FinMind API 連線異常 (HTTP {r.status_code})。請檢查網路或稍後再試。"
            data = r.json()
            if not data.get("data"):
                return False, "FinMind 未回傳財報/營收資料。請確認 FINMIND_TOKEN 是否有效，或稍後再試。"
        return True, None
    except Exception as e:
        return False, f"FinMind 連線錯誤：{str(e)}"


def _reset_quota_exhausted_flag() -> None:
    global _finmind_quota_exhausted
    _finmind_quota_exhausted = False


def _is_tech_stock(industry: str) -> bool:
    """產業是否為科技股（排除金融、傳產）"""
    if not industry or not isinstance(industry, str):
        return True
    industry = industry.strip()
    for kw in EXCLUDE_INDUSTRY_KEYWORDS:
        if kw in industry:
            return False
    return True


def get_taiwan_stock_list(tech_only: bool = True) -> List[str]:
    """從 FinMind TaiwanStockInfo 取得台股清單；tech_only=True 時排除金融、傳產，只保留科技股"""
    rows = _finmind_request("TaiwanStockInfo")
    if rows:
        ids = []
        for r in rows:
            sid = r.get("stock_id")
            if not sid or not isinstance(sid, str) or not sid.isdigit() or len(sid) != 4 or sid.startswith("00"):
                continue
            if tech_only and not _is_tech_stock(r.get("industry_category", "")):
                continue
            ids.append(sid)
        if ids:
            return sorted(set(ids))
    # Fallback：TaiwanStockInfo 未取得時，科技股用較精簡範圍（約 1200 檔）
    print("策略1：TaiwanStockInfo 未取得，使用 fallback（2300-2499、3000-3999）。請確認 FINMIND_TOKEN。")
    if tech_only:
        return [str(i) for i in range(2300, 2500)] + [str(i) for i in range(3000, 4000)]
    return [str(i) for i in range(1000, 3000)] + [str(i) for i in range(3000, 7000)]


def get_revenue_yoy_last_3m(stock_id: str) -> Optional[float]:
    """計算近三月營收年成長率（%）。近三月=最近3個有資料月份；年增=(今年合計-去年同三月合計)/去年*100"""
    end = datetime.now()
    start = end - timedelta(days=400)
    rows = _finmind_request("TaiwanStockMonthRevenue", data_id=stock_id, start_date=start.strftime("%Y-%m-%d"), end_date=end.strftime("%Y-%m-%d"))
    if not rows:
        return None
    df = pd.DataFrame(rows)
    if "revenue" not in df.columns or "revenue_year" not in df.columns or "revenue_month" not in df.columns:
        return None
    df = df.sort_values(["revenue_year", "revenue_month"], ascending=[False, False]).drop_duplicates(subset=["revenue_year", "revenue_month"], keep="first")
    if len(df) < 6:
        return None
    recent = df.head(3)
    this_year = int(recent["revenue_year"].iloc[0])
    months_used = recent["revenue_month"].tolist()
    this_sum = recent["revenue"].sum()
    last_year_df = df[(df["revenue_year"] == this_year - 1) & (df["revenue_month"].isin(months_used))]
    if len(last_year_df) < 3:
        return None
    last_sum = last_year_df["revenue"].sum()
    if last_sum <= 0:
        return None
    return round((this_sum - last_sum) / last_sum * 100, 2)


def check_revenue_yoy_criteria(stock_id: str, min_yoy: float = 20) -> Tuple[bool, Optional[float]]:
    """檢查近三月營收年成長率是否 > min_yoy%，回傳 (是否通過, 成長率)"""
    yoy = get_revenue_yoy_last_3m(stock_id)
    if yoy is None:
        return False, None
    return yoy > min_yoy, yoy


def get_gross_margin_quarterly(stock_id: str, quarters: int = 6) -> Optional[pd.DataFrame]:
    """
    取得台股近 N 季毛利率（季報）
    毛利率 = GrossProfit / (GrossProfit + CostOfGoodsSold) * 100
    """
    end = datetime.now()
    start = end - timedelta(days=quarters * 95)
    start_date = start.strftime("%Y-%m-%d")
    end_date = end.strftime("%Y-%m-%d")
    rows = _finmind_request(
        "TaiwanStockFinancialStatements",
        data_id=stock_id,
        start_date=start_date,
        end_date=end_date,
    )
    if not rows:
        return None
    df = pd.DataFrame(rows)
    gp = df[df["type"] == "GrossProfit"][["date", "value"]].rename(columns={"value": "GrossProfit"})
    cogs = df[df["type"] == "CostOfGoodsSold"][["date", "value"]].rename(columns={"value": "CostOfGoodsSold"})
    merged = gp.merge(cogs, on="date", how="inner")
    if merged.empty:
        return None
    # 營收 = 毛利 + 營業成本
    merged["Revenue"] = merged["GrossProfit"] + merged["CostOfGoodsSold"]
    merged["gross_margin_pct"] = (merged["GrossProfit"] / merged["Revenue"].replace(0, float("nan")) * 100).round(2)
    merged = merged.sort_values("date").reset_index(drop=True)
    return merged.tail(quarters)


def check_gross_margin_criteria(df: pd.DataFrame, min_pct: float = 30, min_quarters: int = 3) -> bool:
    """
    檢查：連續 min_quarters 季毛利率 > min_pct，且連三月持續成長
    """
    if df is None or len(df) < min_quarters:
        return False
    recent = df.tail(min_quarters)
    # 1. 每季毛利率都 > 30%
    if (recent["gross_margin_pct"] <= min_pct).any():
        return False
    # 2. 毛利率持續成長（每季比前一季高）
    margins = recent["gross_margin_pct"].tolist()
    for i in range(1, len(margins)):
        if margins[i] <= margins[i - 1]:
            return False
    return True


def get_ma_condition(stock_id: str) -> bool:
    """
    檢查日K線 5MA > 20MA（最近一筆收盤）
    yfinance 台股代碼格式：2330.TW
    """
    symbol = f"{stock_id}.TW"
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2mo", interval="1d")
        if hist is None or len(hist) < 20:
            return False
        hist = hist.sort_index()
        hist["ma5"] = hist["Close"].rolling(5).mean()
        hist["ma20"] = hist["Close"].rolling(20).mean()
        last = hist.iloc[-1]
        ma5 = last.get("ma5")
        ma20 = last.get("ma20")
        if pd.isna(ma5) or pd.isna(ma20):
            return False
        return float(ma5) > float(ma20)
    except Exception as e:
        print(f"yfinance {symbol}: {e}")
        return False


def get_stock_name(stock_id: str) -> str:
    """取得股票名稱（yfinance）"""
    try:
        ticker = yf.Ticker(f"{stock_id}.TW")
        info = ticker.info or {}
        return info.get("shortName") or info.get("longName") or stock_id
    except Exception:
        return stock_id


def _check_single_stock(
    stock_id: str,
    min_gross_margin: float,
    min_quarters: int,
    min_revenue_yoy: float,
) -> Optional[Dict]:
    """檢查單一股票是否符合策略1，符合則回傳結果 dict，否則 None"""
    df = get_gross_margin_quarterly(stock_id, quarters=min_quarters + 2)
    if not check_gross_margin_criteria(df, min_pct=min_gross_margin, min_quarters=min_quarters):
        return None
    passed, yoy = check_revenue_yoy_criteria(stock_id, min_yoy=min_revenue_yoy)
    if not passed:
        return None
    if not get_ma_condition(stock_id):
        return None
    name = get_stock_name(stock_id)
    last_margins = df.tail(min_quarters)["gross_margin_pct"].tolist()
    return {
        "stock_id": stock_id,
        "name": name,
        "gross_margin_quarters": last_margins,
        "latest_gross_margin": last_margins[-1] if last_margins else None,
        "revenue_yoy_pct": yoy,
    }


def run_screener(
    stock_ids: Optional[List[str]] = None,
    min_gross_margin: float = 30,
    min_quarters: int = 3,
    min_revenue_yoy: float = 20,
    use_full_universe: bool = True,
    max_workers: int = 6,
    tech_only: bool = True,
    batch_size: int = 80,
) -> Tuple[List[Dict], List[str]]:
    """
    執行選股策略1，支援雙金鑰輪替。
    當兩金鑰額度都用完時停止，回報已篩選檔數並輸出既有結果。
    回傳 (篩選結果, 警告訊息)。
    """
    global _finmind_quota_exhausted
    _reset_quota_exhausted_flag()
    warnings: List[str] = []

    ok, err_msg = check_finmind_api_status()
    if not ok and err_msg:
        warnings.append(err_msg)
        print(f"策略1：{err_msg}")

    if stock_ids is not None:
        ids = stock_ids
    elif use_full_universe:
        ids = get_taiwan_stock_list(tech_only=tech_only)
        scope = "科技股" if tech_only else "上市櫃"
        print(f"策略1：待篩選候選池 {len(ids)} 檔（{scope}，雙金鑰輪替，每批 {batch_size} 檔）")
    else:
        ids = DEFAULT_STOCK_IDS

    results: List[Dict] = []
    screened_count = 0

    for batch_start in range(0, len(ids), batch_size):
        if _finmind_quota_exhausted:
            msg = f"FinMind 雙金鑰額度已用盡。共篩選 {screened_count} 檔，符合條件 {len(results)} 檔。"
            warnings.append(msg)
            print(f"策略1：{msg}")
            break

        batch_ids = ids[batch_start : batch_start + batch_size]
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _check_single_stock,
                    sid,
                    min_gross_margin,
                    min_quarters,
                    min_revenue_yoy,
                ): sid
                for sid in batch_ids
            }
            for future in as_completed(futures):
                if _finmind_quota_exhausted:
                    break
                screened_count += 1
                if screened_count % 100 == 0:
                    print(f"策略1：已篩選 {screened_count}/{len(ids)} 檔...")
                r = future.result()
                if r is not None:
                    results.append(r)

    results.sort(key=lambda x: x["stock_id"])
    print(f"策略1：篩選完成，共篩 {screened_count} 檔，符合條件 {len(results)} 檔")
    return results, warnings
