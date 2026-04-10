"""
Deribit 加密貨幣報價（公開 API，無需 key）
BTC/ETH/SOL 用 Deribit 永續 ticker；其餘用 yfinance（有 24h 漲跌）
"""
from typing import Dict, Optional
from datetime import datetime, timezone

import requests
import yfinance as yf

DERIBIT_API = "https://www.deribit.com/api/v2"

# Config 鍵（如 BTC-USD）-> Deribit 永續合約名稱（有則用 ticker 取得 24h 數據）
TICKER_INSTRUMENTS = {
    "BTC-USD": "BTC-PERPETUAL",
    "ETH-USD": "ETH-PERPETUAL",
    "SOL-USD": "SOL-PERPETUAL",
}


def _get_ticker(instrument_name: str) -> Optional[Dict]:
    """取得永續合約 ticker（24h 數據）。"""
    try:
        r = requests.post(
            f"{DERIBIT_API}/public/ticker",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "public/ticker",
                "params": {"instrument_name": instrument_name},
            },
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if "result" not in data:
            return None
        res = data["result"]
        last = res.get("last_price") or res.get("index_price")
        if last is None:
            return None
        stats = res.get("stats") or {}
        pct = stats.get("price_change")
        if pct is None:
            pct = 0
        prev = last / (1 + pct / 100) if pct else last
        return {
            "current_price": round(float(last), 2),
            "previous_close": round(float(prev), 2),
            "change": round(float(last) - float(prev), 2),
            "change_percent": round(float(pct), 2),
            "volume": int(float(stats.get("volume", 0) or 0)),
            "high": round(float(stats.get("high", last)), 2),
            "low": round(float(stats.get("low", last)), 2),
            "open": round(float(prev), 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "history": [],
        }
    except Exception as e:
        print(f"Deribit ticker {instrument_name}: {e}")
        return None


def _get_yf_crypto(symbol: str) -> Optional[Dict]:
    """yfinance 取得加密貨幣（含 24h 漲跌）。優先使用 info 的 regularMarketChangePercent，較可靠。"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        hist = ticker.history(period="2d", interval="1d")
        current = None
        prev = None
        change = 0.0
        pct = 0.0
        h = 0.0
        lo = 0.0
        vol = 0
        open_price = None

        # 優先從 info 取得 24h 漲跌（Yahoo 對加密貨幣有提供）
        info_pct = info.get("regularMarketChangePercent")
        info_change = info.get("regularMarketChange")
        info_price = info.get("regularMarketPrice") or info.get("currentPrice")
        info_open = info.get("regularMarketOpen") or info.get("open")
        if info_price is not None:
            current = float(info_price)
            if info_pct is not None:
                pct = float(info_pct)
                prev = current / (1 + pct / 100) if pct != 0 else current
                change = current - prev
            elif info_change is not None:
                change = float(info_change)
                prev = current - change
                pct = (change / prev * 100) if prev else 0
            elif info_open is not None:
                prev = float(info_open)
                change = current - prev
                pct = (change / prev * 100) if prev else 0
        if h == 0 and info.get("dayHigh"):
            h = float(info["dayHigh"])
        if lo == 0 and info.get("dayLow"):
            lo = float(info["dayLow"])
        if vol == 0:
            vol = int(info.get("regularMarketVolume") or info.get("volume") or 0)
        if open_price is None and info_open is not None:
            open_price = float(info_open)

        # 若 info 無完整資料，用 history 補齊
        if hist is not None and not hist.empty and "Close" in hist.columns:
            if current is None:
                current = float(hist["Close"].iloc[-1])
            if prev is None:
                prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else current
                change = current - prev
                pct = (change / prev * 100) if prev else 0
            if h == 0 and "High" in hist.columns:
                h = float(hist["High"].iloc[-1])
            if lo == 0 and "Low" in hist.columns:
                lo = float(hist["Low"].iloc[-1])
            if vol == 0 and "Volume" in hist.columns:
                vol = int(hist["Volume"].iloc[-1])
            if open_price is None:
                open_price = float(hist["Open"].iloc[-1]) if "Open" in hist.columns else prev

        if current is None:
            return None
        if prev is None:
            prev = current
        if open_price is None:
            open_price = prev
        if h == 0:
            h = current
        if lo == 0:
            lo = current

        return {
            "current_price": round(current, 2),
            "previous_close": round(prev, 2),
            "change": round(change, 2),
            "change_percent": round(pct, 2),
            "volume": vol,
            "high": round(float(h), 2),
            "low": round(float(lo), 2),
            "open": round(float(open_price), 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "history": [],
        }
    except Exception as e:
        print(f"yfinance crypto {symbol}: {e}")
        return None


def get_single_crypto(config_key: str) -> Optional[Dict]:
    """取得單一加密貨幣報價。config_key 如 BTC-USD。BTC/ETH/SOL 用 Deribit ticker，其餘用 yfinance（有漲跌）。"""
    inst = TICKER_INSTRUMENTS.get(config_key)
    if inst:
        out = _get_ticker(inst)
        if out:
            return out
    return _get_yf_crypto(config_key)


def get_multiple_crypto(symbols_display: Dict[str, str]) -> Dict[str, Dict]:
    """
    symbols_display: Config.CRYPTO 格式 { 'BTC-USD': '比特幣', ... }
    回傳 { 'BTC-USD': { ...market_data, symbol, name, display_name }, ... }
    """
    if not symbols_display:
        return {}
    out = {}
    for config_key, display_name in symbols_display.items():
        if config_key == "USDT-USD":
            continue  # 穩定幣跳過
        data = get_single_crypto(config_key)
        if data:
            data["symbol"] = config_key
            data["name"] = display_name
            data["display_name"] = display_name
            out[config_key] = data
    return out
