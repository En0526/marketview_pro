"""
三大法人買賣超資料（證交所 BFI82U 三大法人買賣金額統計表）
資料來源：https://www.twse.com.tw/zh/trading/foreign/bfi82u.html

若證交所連線失敗（SSL、阻擋或無資料），可改用手動下載：
至上述網頁選擇日期後點「CSV 下載」，將檔案存到 institutional_csv 資料夾，檔名 YYYYMMDD.csv
"""
import requests
import csv
import time
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from io import StringIO

# 關閉 SSL 警告（部分環境對 twse.com.tw 憑證會報錯）
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass

SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.twse.com.tw/zh/trading/foreign/bfi82u.html',
    'Accept': 'text/csv,application/csv,text/plain,*/*',
    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
})
BFI82U_URL = 'https://www.twse.com.tw/rwd/zh/fund/BFI82U'

# 專案根目錄（此檔在 market_data/ 下）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTITUTIONAL_CSV_DIR = os.path.join(_PROJECT_ROOT, 'institutional_csv')

# 緩存：當日內不重複拉整段區間
_ytd_cache: Optional[Dict] = None
_ytd_cache_date: Optional[str] = None
# 最後一次連線錯誤（用於無資料時顯示可能原因）
_last_fetch_error: Optional[str] = None


def _parse_int(s: str) -> int:
    """將「1,234」或「-123」轉成整數（單位：元）。"""
    if not s or not isinstance(s, str):
        return 0
    s = s.strip().replace(',', '').replace('"', '').replace('=', '')
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return 0


def _decode_csv_bytes(content: bytes) -> str:
    """證交所 CSV 常見為 Big5/CP950；依序嘗試解碼，最後以 UTF-8 忽略錯字保底。"""
    for encoding in ('cp950', 'big5', 'utf-8-sig', 'utf-8'):
        try:
            return content.decode(encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return content.decode('utf-8', errors='ignore')


def _extract_report_date(text: str) -> Optional[str]:
    """從 BFI82U CSV 標題列抓報表日期，回傳 YYYYMMDD；抓不到則回傳 None。"""
    import re
    for line in (text or '').split('\n')[:5]:
        line = line.strip().replace('"', '')
        # 常見：115年04月21日 三大法人買賣金額統計表
        m = re.search(r'(\d{3})年(\d{1,2})月(\d{1,2})日', line)
        if m:
            y = int(m.group(1)) + 1911
            return f'{y}{int(m.group(2)):02d}{int(m.group(3)):02d}'
        m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', line)
        if m:
            return f'{int(m.group(1)):04d}{int(m.group(2)):02d}{int(m.group(3)):02d}'
    return None


def _has_local_bfi82u_csv(date_str: str) -> bool:
    """檢查指定日期是否已有本地 CSV（支援 YYYYMMDD.csv 與 BFI82U_YYYYMMDD.csv）。"""
    return any(
        os.path.isfile(os.path.join(INSTITUTIONAL_CSV_DIR, name))
        for name in (f'{date_str}.csv', f'BFI82U_{date_str}.csv')
    )


def _trading_days(start: datetime, end: datetime) -> List[datetime]:
    """產生 start~end 之間的交易日（簡單以週一～五為交易日，不排除國定假日）。"""
    out = []
    d = start.date()
    end_date = end.date()
    while d <= end_date:
        if d.weekday() < 5:  # 0=Mon .. 4=Fri
            out.append(datetime.combine(d, datetime.min.time()))
        d += timedelta(days=1)
    return out


def _parse_bfi82u_csv(text: str, date_str: str) -> Optional[Dict[str, int]]:
    """解析 BFI82U CSV 內容（API 或本地檔），回傳該日外資與三大法人合計買賣超（元）。"""
    if not text or 'html' in text.lower()[:200]:
        return None
    text = text.lstrip('\ufeff')
    lines = [line for line in text.split('\n') if line.strip()]
    if len(lines) < 3:
        return None
    header_idx = None
    for i, line in enumerate(lines):
        if '類別' in line or '買賣超' in line or '證券名稱' in line:
            header_idx = i
            break
        if '買' in line and '賣' in line and ('買進' in line or '賣出' in line or '金額' in line) and ',' in line:
            row_pre = next(csv.reader(StringIO(line)))
            if len(row_pre) >= 4:
                header_idx = i
                break
    if header_idx is None:
        return None
    reader = csv.reader(StringIO('\n'.join(lines[header_idx:])))
    header = next(reader)
    col_idx = None
    for j, h in enumerate(header):
        h = (h or '').strip()
        if '買賣超' in h:
            col_idx = j
            break
        if '買' in h and '賣' in h and j >= 2:
            col_idx = j
            break
    if col_idx is None:
        return None
    foreign_net = None
    trust_net = None
    dealer_net = 0
    total_net = None
    components = []
    category_col = 0
    for row in reader:
        if len(row) <= max(category_col, col_idx):
            continue
        label = (row[category_col] or '').strip().replace(' ', '')
        value = _parse_int(row[col_idx]) if col_idx < len(row) else 0
        if ('外資' in label and ('陸資' in label or '及' in label or '與' in label)) or '外資及陸資' in label or '外資與陸資' in label:
            foreign_net = value
            components.append(value)
        elif '投信' in label and '自營' not in label:
            trust_net = value
            components.append(value)
        elif '自營' in label or '證券自營商' in label or '外資自營商' in label:
            dealer_net = (dealer_net or 0) + value
            components.append(value)
        elif '合計' in label or '總計' in label or '總和' in label or ('合' in label and '計' in label):
            total_net = value
    if total_net is None and components:
        total_net = sum(components)
    if foreign_net is None:
        foreign_net = 0
    if trust_net is None:
        trust_net = 0
    if dealer_net is None:
        dealer_net = 0
    if total_net is None:
        total_net = foreign_net + trust_net + dealer_net
    return {
        'date': date_str,
        'foreign_net': foreign_net,
        'trust_net': trust_net,
        'dealer_net': dealer_net,
        'total_net': total_net,
    }


def fetch_bfi82u_day(date: datetime) -> Optional[Dict[str, int]]:
    """
    取得單日 BFI82U 報表（證交所 API），回傳該日外資與三大法人合計買賣超（元）。
    若連線失敗或解析失敗會設定 _last_fetch_error 並回傳 None。
    """
    global _last_fetch_error
    date_str = date.strftime('%Y%m%d')
    try:
        r = SESSION.get(
            BFI82U_URL,
            params={'response': 'csv', 'dayDate': date_str},
            timeout=15,
            verify=False
        )
        r.raise_for_status()
        text = _decode_csv_bytes(r.content or b'')
    except Exception as e:
        _last_fetch_error = str(e)
        return None
    if not text or 'html' in text.lower()[:200]:
        _last_fetch_error = '證交所未回傳 CSV（可能為非交易日或網站阻擋）'
        return None
    report_date = _extract_report_date(text)
    if report_date and report_date != date_str:
        _last_fetch_error = f'證交所回傳日期為 {report_date}，非請求日期 {date_str}'
        return None
    parsed = _parse_bfi82u_csv(text, date_str)
    if parsed is None:
        _last_fetch_error = '證交所回傳內容無法解析（非預期 CSV 格式）'
        return None
    _last_fetch_error = None
    return parsed


def download_bfi82u_csv_day(date: datetime, overwrite: bool = False) -> Tuple[bool, str]:
    """
    從證交所公開 CSV 端點下載單日 BFI82U 檔案並存入 institutional_csv/YYYYMMDD.csv。
    回傳 (是否成功下載或已存在, 狀態訊息)。非交易日或無法解析時不落檔。
    """
    date_str = date.strftime('%Y%m%d')
    os.makedirs(INSTITUTIONAL_CSV_DIR, exist_ok=True)
    path = os.path.join(INSTITUTIONAL_CSV_DIR, f'{date_str}.csv')

    if os.path.isfile(path) and not overwrite:
        return True, 'exists'

    try:
        # 先拜訪一次頁面取得站台 cookie；若失敗不阻斷，後續 CSV endpoint 仍可能成功。
        try:
            SESSION.get('https://www.twse.com.tw/zh/trading/foreign/bfi82u.html', timeout=10, verify=False)
        except Exception:
            pass

        r = SESSION.get(
            BFI82U_URL,
            params={'response': 'csv', 'dayDate': date_str},
            timeout=15,
            verify=False,
        )
        r.raise_for_status()
        content = r.content or b''
    except Exception as e:
        return False, f'fetch_error: {e}'

    text = _decode_csv_bytes(content)
    if not text or 'html' in text.lower()[:200]:
        return False, 'not_csv'

    report_date = _extract_report_date(text)
    if report_date and report_date != date_str:
        return False, f'date_mismatch:{report_date}'

    parsed = _parse_bfi82u_csv(text, date_str)
    if parsed is None:
        return False, 'parse_failed'

    with open(path, 'wb') as f:
        f.write(content)
    return True, 'downloaded'


def download_bfi82u_csv_range(
    start: datetime,
    end: datetime,
    overwrite: bool = False,
    sleep_seconds: float = 0.35,
) -> Dict:
    """批次下載日期區間內的 BFI82U CSV（只掃週一至週五，非交易日會自動略過）。"""
    global _ytd_cache, _ytd_cache_date
    days = _trading_days(start, end)
    summary = {
        'start_date': start.strftime('%Y%m%d'),
        'end_date': end.strftime('%Y%m%d'),
        'downloaded': [],
        'existing': [],
        'skipped': [],
        'failed': [],
    }

    requested = 0
    for d in days:
        date_str = d.strftime('%Y%m%d')
        if _has_local_bfi82u_csv(date_str) and not overwrite:
            summary['existing'].append(date_str)
            continue
        if requested > 0:
            time.sleep(sleep_seconds)
        ok, status = download_bfi82u_csv_day(d, overwrite=overwrite)
        requested += 1
        if ok and status == 'downloaded':
            summary['downloaded'].append(date_str)
        elif ok and status == 'exists':
            summary['existing'].append(date_str)
        elif status in ('not_csv', 'parse_failed'):
            summary['skipped'].append({'date': date_str, 'reason': status})
        else:
            summary['failed'].append({'date': date_str, 'reason': status})

    if summary['downloaded']:
        _ytd_cache = None
        _ytd_cache_date = None
    summary['counts'] = {
        'downloaded': len(summary['downloaded']),
        'existing': len(summary['existing']),
        'skipped': len(summary['skipped']),
        'failed': len(summary['failed']),
    }
    return summary


def ensure_bfi82u_csv_current(end: Optional[datetime] = None) -> Dict:
    """
    載入三大法人圖表前同步到最新 CSV。
    每次開頁只從本地最新日期往後補，避免重複掃描整個年度造成等待太久。
    """
    end = end or datetime.now()
    dates_this_year = [d for d in list_uploaded_dates() if d.startswith(str(end.year))]
    if dates_this_year:
        latest = max(dates_this_year)
        start = datetime(int(latest[:4]), int(latest[4:6]), int(latest[6:8])) + timedelta(days=1)
    else:
        start = datetime(end.year, 1, 1)

    if start.date() > end.date():
        return {
            'start_date': start.strftime('%Y%m%d'),
            'end_date': end.strftime('%Y%m%d'),
            'downloaded': [],
            'existing': [],
            'skipped': [],
            'failed': [],
            'counts': {'downloaded': 0, 'existing': 0, 'skipped': 0, 'failed': 0},
        }
    return download_bfi82u_csv_range(start, end, overwrite=False)


def list_uploaded_dates() -> List[str]:
    """掃描 institutional_csv 資料夾，回傳已有 CSV 的日期列表（YYYYMMDD），已排序。"""
    import re
    if not os.path.isdir(INSTITUTIONAL_CSV_DIR):
        return []
    dates = []
    for name in os.listdir(INSTITUTIONAL_CSV_DIR):
        if not name.lower().endswith('.csv'):
            continue
        base = name[:-4]  # 去掉 .csv
        # 支援 YYYYMMDD 或 BFI82U_YYYYMMDD
        m = re.match(r'^(?:BFI82U_)?(\d{8})$', base)
        if m:
            dates.append(m.group(1))
    return sorted(set(dates))


def save_uploaded_csv(date_str: str, content: bytes) -> None:
    """將上傳的 CSV 存到 institutional_csv/YYYYMMDD.csv，並清除快取。"""
    global _ytd_cache, _ytd_cache_date
    os.makedirs(INSTITUTIONAL_CSV_DIR, exist_ok=True)
    path = os.path.join(INSTITUTIONAL_CSV_DIR, f'{date_str}.csv')
    with open(path, 'wb') as f:
        f.write(content)
    _ytd_cache = None
    _ytd_cache_date = None


def try_parse_date_from_filename(filename: str) -> Optional[str]:
    """從檔名嘗試解析日期，例如 BFI82U_day_20260102.csv、20260102.csv。回傳 YYYYMMDD。"""
    import re
    if not filename:
        return None
    base = os.path.splitext(filename)[0]
    m = re.search(r'(\d{8})', base)
    if m:
        s = m.group(1)
        y, mon, d = int(s[:4]), int(s[4:6]), int(s[6:8])
        if 1990 <= y <= 2030 and 1 <= mon <= 12 and 1 <= d <= 31:
            return s
    return None


def try_parse_date_from_csv(text: str) -> Optional[str]:
    """從 BFI82U CSV 內容嘗試解析日期，回傳 YYYYMMDD 或 None。"""
    import re
    # 常見：資料日期 20260102、或 115/01/02（民國）
    for line in text.split('\n')[:10]:
        line = line.strip()
        m = re.search(r'(\d{4})[/\-]?(\d{2})[/\-]?(\d{2})', line)
        if m:
            return m.group(1) + m.group(2) + m.group(3)
        m = re.search(r'(\d{3})/(\d{1,2})/(\d{1,2})', line)  # 民國 115/1/2
        if m:
            y = int(m.group(1)) + 1911
            return f'{y}{int(m.group(2)):02d}{int(m.group(3)):02d}'
    return None


def _load_bfi82u_from_file(date_str: str) -> Optional[Dict[str, int]]:
    """從 institutional_csv/ 讀取手動下載的 BFI82U CSV，檔名 YYYYMMDD.csv 或 BFI82U_YYYYMMDD.csv。證交所多為 Big5，先試 Big5 再試 UTF-8。"""
    for name in (f'{date_str}.csv', f'BFI82U_{date_str}.csv'):
        path = os.path.join(INSTITUTIONAL_CSV_DIR, name)
        if not os.path.isfile(path):
            continue
        text = None
        for encoding in ('cp950', 'big5', 'utf-8', 'utf-8-sig'):
            try:
                with open(path, 'r', encoding=encoding) as f:
                    text = f.read()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        if not text:
            continue
        parsed = _parse_bfi82u_csv(text, date_str)
        if parsed:
            return parsed
    return None


def get_institutional_net_ytd(force_refresh: bool = False) -> Dict:
    """
    從今年 1/1 起算到今日，取得每日三大法人買賣超，並計算當年累計值。
    回傳格式供前端畫「當年累計」柱狀圖：三大法人總和、外資。
    """
    global _ytd_cache, _ytd_cache_date
    now = datetime.now()
    auto_sync = ensure_bfi82u_csv_current(now)
    today_str = datetime.now().strftime('%Y-%m-%d')
    if not force_refresh and _ytd_cache is not None and _ytd_cache_date == today_str:
        _ytd_cache['auto_csv_sync'] = auto_sync
        return _ytd_cache

    year_start = datetime(now.year, 1, 1)
    end = now
    days = _trading_days(year_start, end)

    daily_list: List[Dict] = []
    cumulative_total = 0
    cumulative_foreign = 0
    cumulative_trust = 0
    cumulative_dealer = 0

    for i, d in enumerate(days):
        date_str = d.strftime('%Y%m%d')
        row = _load_bfi82u_from_file(date_str)
        if row is None:
            if i > 0:
                time.sleep(0.2)
            row = fetch_bfi82u_day(d)
        if row is None:
            continue
        f_net = row.get('foreign_net') or 0
        tr_net = row.get('trust_net') or 0
        dl_net = row.get('dealer_net') or 0
        t_net = row.get('total_net')
        if t_net is None:
            t_net = f_net + tr_net + dl_net
        cumulative_foreign += f_net
        cumulative_trust += tr_net
        cumulative_dealer += dl_net
        cumulative_total += t_net
        daily_list.append({
            'date': row['date'],
            'date_display': f"{row['date'][:4]}-{row['date'][4:6]}-{row['date'][6:8]}",
            'foreign_net': f_net,
            'trust_net': tr_net,
            'dealer_net': dl_net,
            'total_net': t_net,
            'cumulative_foreign': cumulative_foreign,
            'cumulative_trust': cumulative_trust,
            'cumulative_dealer': cumulative_dealer,
            'cumulative_total': cumulative_total,
        })

    labels = [x['date_display'] for x in daily_list]
    cum_total_millions = [round(x['cumulative_total'] / 1e6, 2) for x in daily_list]
    cum_foreign_millions = [round(x['cumulative_foreign'] / 1e6, 2) for x in daily_list]
    cum_trust_millions = [round(x['cumulative_trust'] / 1e6, 2) for x in daily_list]
    cum_dealer_millions = [round(x['cumulative_dealer'] / 1e6, 2) for x in daily_list]

    result = {
        'labels': labels,
        'cumulative_total_millions': cum_total_millions,
        'cumulative_foreign_millions': cum_foreign_millions,
        'cumulative_trust_millions': cum_trust_millions,
        'cumulative_dealer_millions': cum_dealer_millions,
        'daily': daily_list,
        'year': now.year,
        'auto_csv_sync': auto_sync,
    }
    if not daily_list:
        result['fetch_error'] = _last_fetch_error or '無法取得資料'
        result['csv_help'] = (
            '若為連線或 SSL 問題，可改用手動下載：至證交所 '
            '三大法人買賣金額統計表 選擇日期後點「CSV 下載」，'
            '將檔案存到 institutional_csv 資料夾，檔名 YYYYMMDD.csv 後按更新。'
        )
    _ytd_cache = result
    _ytd_cache_date = today_str
    return result
