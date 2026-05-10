"""
AI 速覽：以 LLM 統整新聞聲量前三名與盤前新聞爬蟲結果。
Gemini：優先 google-genai（Google AI Studio）；無套件時備援 REST generateContent。
未設定 GEMINI_API_KEY 時改用 OpenAI 相容 Chat Completions。
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pytz
import requests

from config import Config
from market_data.data_fetcher import MarketDataFetcher
from news_analysis.premarket_analyzer import PremarketAnalyzer
from news_analysis.volume_analyzer import VolumeAnalyzer

_CACHE: Dict[str, Any] = {}
_CACHE_TTL_SEC = 600
# AI 速覽「新聞聲量」列舉與送進 LLM 的名數（與前端標題「前三名」一致）
DIGEST_VOLUME_TOP_N = 3


def get_taipei_session_mode() -> Tuple[str, str]:
    """台北時間時段，供盤前／盤後摘要權重。"""
    now = datetime.now(pytz.timezone("Asia/Taipei"))
    minutes = now.hour * 60 + now.minute
    # 14:00～翌日 02:00
    if minutes >= 14 * 60 or minutes < 2 * 60:
        return (
            "evening",
            "目前時段（台北 14:00～翌日 02:00）：請分別以「美股盤前」「台股盤後」為小標，各用 2～4 條一句話bullet統整下方新聞要點。",
        )
    if 6 * 60 <= minutes < 14 * 60:
        return (
            "morning",
            "目前時段（台北 06:00～14:00）：請分別以「台股盤前」「美股盤後」為小標，各用 2～4 條一句話bullet統整下方新聞要點。",
        )
    return (
        "off_hours",
        "目前為凌晨（台北 02:00～06:00）：請簡短合併台股與美股相關要點，2～3 條即可。",
    )


def _pick_tw_us_labels(session: str) -> Tuple[str, str, str, str]:
    """若 session 為 morning/evening，回傳 (台標, 美標)；off 則泛用。"""
    if session == "evening":
        return "台股盤後", "美股盤前", "taiwan", "us"
    if session == "morning":
        return "台股盤前", "美股盤後", "taiwan", "us"
    return "台股相關", "美股相關", "taiwan", "us"


def _fmt_change(pct: Optional[float]) -> str:
    if pct is None:
        return "－"
    if pct > 0:
        return f"+{pct:.2f}%"
    return f"{pct:.2f}%"


def _fetch_symbol_change_pct(data_fetcher: MarketDataFetcher, symbol: str) -> Optional[float]:
    try:
        row = data_fetcher.get_market_data(symbol, period="2d", interval="1d")
        if row and "change_percent" in row:
            return float(row["change_percent"])
    except Exception:
        pass
    return None


def _truncate(s: str, n: int) -> str:
    s = (s or "").strip()
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def _compact_volume_for_prompt(top5: List[Dict]) -> str:
    lines: List[str] = []
    for c in top5:
        sym = c.get("symbol", "")
        name = c.get("name", sym)
        news = c.get("news") or []
        titles = [_truncate(n.get("title", ""), 160) for n in news[:10]]
        lines.append(f"- {name} ({sym}): " + " | ".join(titles) if titles else f"- {name} ({sym}): (無標題)")
    return "\n".join(lines)


def _compact_premarket_for_prompt(tw: Dict, us: Dict) -> str:
    parts = []
    for label, blob in ("台股爬蟲", tw), ("美股爬蟲", us):
        news = blob.get("news") or []
        parts.append(f"【{label}】type={blob.get('type', '')} count={len(news)}")
        for n in news[:18]:
            t = _truncate(n.get("title", ""), 200)
            parts.append(f"  - {t}")
    return "\n".join(parts)


def _call_gemini_via_rest(
    api_key: str,
    model: str,
    system: str,
    user: str,
    timeout: int = 90,
) -> str:
    """Generative Language API REST（無 google-genai 套件時備援）。"""
    m = model.strip()
    if m.startswith("models/"):
        m = m[len("models/") :]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": 0.3,
            "responseMimeType": "application/json",
        },
    }
    r = requests.post(url, params={"key": api_key}, json=body, timeout=timeout)
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        err = ""
        try:
            err = (r.json().get("error") or {}).get("message", "") or r.text
        except Exception:
            err = r.text or str(e)
        raise ValueError(f"Gemini API 錯誤：{err}") from e
    data = r.json()
    cands = data.get("candidates") or []
    if not cands:
        pf = data.get("promptFeedback") or {}
        br = pf.get("blockReason") or pf.get("block_reason")
        if br:
            raise ValueError(f"Gemini 阻擋輸出（{br}），請縮短素材或調整內容後重試")
        raise ValueError("Gemini 回傳無 candidates（可能為配額／模型名稱錯誤，請確認 GEMINI_MODEL）")
    parts = (cands[0].get("content") or {}).get("parts") or []
    texts = [str(p.get("text", "")) for p in parts if p.get("text")]
    content = "".join(texts).strip()
    if not content:
        raise ValueError("Gemini 回傳空內容")
    return content


def _call_gemini(
    api_key: str,
    model: str,
    system: str,
    user: str,
    timeout: int = 90,
) -> str:
    """Google AI Studio：優先使用官方 google-genai SDK（與官方快速入門一致）。"""
    try:
        from google import genai
        from google.genai import errors as genai_errors
        from google.genai import types as genai_types
    except ImportError:
        return _call_gemini_via_rest(api_key, model, system, user, timeout)

    m = model.strip()
    if m.startswith("models/"):
        m = m[len("models/") :]

    client = genai.Client(
        api_key=api_key,
        http_options=genai_types.HttpOptions(timeout=max(1, timeout) * 1000),
    )
    try:
        response = client.models.generate_content(
            model=m,
            contents=user,
            config=genai_types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.3,
                response_mime_type="application/json",
            ),
        )
    except genai_errors.APIError as e:
        raise ValueError(f"Gemini API 錯誤：{e.message or e}") from e

    cands = response.candidates or []
    if not cands:
        pf = response.prompt_feedback
        br = getattr(pf, "block_reason", None) if pf else None
        if br:
            raise ValueError(f"Gemini 阻擋輸出（{br}），請縮短素材或調整內容後重試")
        raise ValueError("Gemini 回傳無 candidates（可能為配額／模型名稱錯誤，請確認 GEMINI_MODEL）")

    text = (response.text or "").strip()
    if not text:
        raise ValueError("Gemini 回傳空內容")
    return text


def _call_openai_compat(
    api_key: str,
    base_url: str,
    model: str,
    system: str,
    user: str,
    timeout: int = 90,
) -> str:
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {
        "model": model,
        "temperature": 0.3,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    r = requests.post(url, headers=headers, json=body, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    choices = data.get("choices") or []
    if not choices:
        raise ValueError("LLM 回傳無 choices")
    msg = choices[0].get("message") or {}
    content = msg.get("content") or ""
    if not content:
        raise ValueError("LLM 回傳空內容")
    return content


def _parse_json_from_llm(text: str) -> Dict[str, Any]:
    text = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.I)
    if m:
        text = m.group(1).strip()
    return json.loads(text)


def build_digest(
    force_refresh: bool = False,
    volume_analyzer: Optional[VolumeAnalyzer] = None,
    premarket_analyzer: Optional[PremarketAnalyzer] = None,
    data_fetcher: Optional[MarketDataFetcher] = None,
) -> Dict[str, Any]:
    gemini_key = (getattr(Config, "GEMINI_API_KEY", None) or "").strip()
    gemini_model = (getattr(Config, "GEMINI_MODEL", None) or "gemini-2.5-flash").strip()
    openai_key = (getattr(Config, "OPENAI_API_KEY", None) or "").strip()
    openai_base = (getattr(Config, "OPENAI_BASE_URL", None) or "https://api.openai.com/v1").strip()
    openai_model = (getattr(Config, "OPENAI_MODEL", None) or "gpt-4o-mini").strip()

    if gemini_key:
        llm_provider = "gemini"
        model = gemini_model
    elif openai_key:
        llm_provider = "openai"
        model = openai_model
    else:
        llm_provider = ""
        model = ""

    session_code, session_hint = get_taipei_session_mode()
    tw_label, us_label, _, _ = _pick_tw_us_labels(session_code)

    now_iso = datetime.now(pytz.timezone("Asia/Taipei")).isoformat()

    if not llm_provider:
        return {
            "enabled": False,
            "message": "未設定 GEMINI_API_KEY（Google AI Studio）或 OPENAI_API_KEY，無法生成 AI 速覽。建議於 .env 設定 GEMINI_API_KEY 後重啟。",
            "provider": None,
            "session": session_code,
            "session_hint_tw": session_hint,
            "tw_panel_label": tw_label,
            "us_panel_label": us_label,
            "timestamp": now_iso,
            "top5": [],
            "premarket_bullets": {"tw": [], "us": []},
        }

    volume_analyzer = volume_analyzer or VolumeAnalyzer()
    premarket_analyzer = premarket_analyzer or PremarketAnalyzer()
    data_fetcher = data_fetcher or MarketDataFetcher()

    vol_summary = volume_analyzer.get_volume_summary(refresh=force_refresh)
    top5_full = (vol_summary.get("top_companies") or [])[:DIGEST_VOLUME_TOP_N]
    n_top = len(top5_full)
    cache_key = json.dumps(
        {
            "p": llm_provider,
            "m": model,
            "s": session_code,
            "syms": [c.get("symbol") for c in top5_full],
        },
        sort_keys=True,
    )
    if not force_refresh and cache_key in _CACHE:
        ent = _CACHE[cache_key]
        if time.time() - ent["t"] < _CACHE_TTL_SEC:
            out = dict(ent["data"])
            out["cached"] = True
            return out

    tw_data = premarket_analyzer.get_taiwan_premarket_news(force_refresh=force_refresh)
    us_data = premarket_analyzer.get_us_premarket_news(force_refresh=force_refresh)

    top5_out: List[Dict[str, Any]] = []
    for c in top5_full:
        sym = c.get("symbol", "")
        pct = _fetch_symbol_change_pct(data_fetcher, sym)
        top5_out.append(
            {
                "rank": c.get("rank"),
                "symbol": sym,
                "name": c.get("name", sym),
                "news_count": c.get("count", 0),
                "prior_session_change_pct": pct,
                "prior_session_change_label": _fmt_change(pct),
            }
        )

    system = f"""你是台美股市場新聞編輯。僅根據使用者提供的爬蟲標題，用繁體中文輸出 JSON（不要虛構未出現過的具體數字／法說內容）。
必須嚴格輸出一個 JSON 物件，不要有其他說明文字。鍵名如下：
{{
  "top3_news_line": [],
  "premarket": {{ "tw": ["bullet1", ...], "us": ["bullet1", ...] }}
}}
top3_news_line 必須為長度 {n_top} 的陣列（與聲量排名順序一一對應；若長度為 0 則輸出 []）。
premarket 的 tw、us 各 2～4 則一句話；off_hours 時段仍填入 tw、us 兩組即可。"""
    user = f"""時段說明：{session_hint}

【新聞聲量前三名（每檔後為相關新聞標題，請為該檔寫一句重點；目前共 {n_top} 檔）】
{_compact_volume_for_prompt(top5_full) if n_top else "（本時段無聲量排名資料）"}

【盤前／盤後新聞爬蟲摘要素材】
{_compact_premarket_for_prompt(tw_data, us_data)}
"""

    try:
        if llm_provider == "gemini":
            raw = _call_gemini(gemini_key, gemini_model, system, user)
        else:
            raw = _call_openai_compat(openai_key, openai_base, openai_model, system, user)
        parsed = _parse_json_from_llm(raw)
    except Exception as e:
        for row in top5_out:
            row["ai_news_line"] = f"（AI 摘要失敗：{e}）"
        err_out = {
            "enabled": True,
            "provider": llm_provider,
            "message": str(e),
            "session": session_code,
            "session_hint_tw": session_hint,
            "tw_panel_label": tw_label,
            "us_panel_label": us_label,
            "timestamp": now_iso,
            "model": model,
            "top5": top5_out,
            "premarket_bullets": {"tw": [], "us": []},
            "cached": False,
            "llm_error": True,
        }
        err_out["cached"] = False
        return err_out

    lines = parsed.get("top3_news_line") or parsed.get("top5_news_line") or []
    pm = parsed.get("premarket") or {}

    for i, row in enumerate(top5_out):
        if i < len(lines) and lines[i]:
            row["ai_news_line"] = str(lines[i]).strip()
        else:
            row["ai_news_line"] = "（無摘要）"

    tw_bullets = [str(x).strip() for x in (pm.get("tw") or []) if str(x).strip()]
    us_bullets = [str(x).strip() for x in (pm.get("us") or []) if str(x).strip()]

    out = {
        "enabled": True,
        "provider": llm_provider,
        "message": None,
        "session": session_code,
        "session_hint_tw": session_hint,
        "tw_panel_label": tw_label,
        "us_panel_label": us_label,
        "timestamp": now_iso,
        "model": model,
        "top5": top5_out,
        "premarket_bullets": {"tw": tw_bullets, "us": us_bullets},
        "cached": False,
        "llm_error": False,
    }
    _CACHE[cache_key] = {"t": time.time(), "data": out}
    return out
