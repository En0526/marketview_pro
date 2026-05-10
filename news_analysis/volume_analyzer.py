"""
聲量分析模組 - 分析前24小時公司新聞出現頻率
"""
import copy
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
from collections import Counter
from news_analysis.news_fetcher import NewsFetcher
from news_analysis.persistent_news_cache import load_entry, load_entry_saved_at, save_entry
from config import Config

# 與盤前模組一致：1 小時內不重複爬新聞聲量（refresh=True 時仍會強制重抓）
VOLUME_SUMMARY_CACHE_SEC = 3600


class VolumeAnalyzer:
    """聲量分析器"""
    
    def __init__(self):
        self.news_fetcher = NewsFetcher()
        self._volume_summary_cache: Optional[Dict] = None
        self._volume_summary_cache_time: float = 0.0
    
    def get_top_companies_by_volume(self, hours: int = 24, top_n: int = 20) -> List[Dict]:
        """
        獲取前24小時新聞聲量最高的公司
        
        Args:
            hours: 時間範圍（小時）
            top_n: 返回前N名
            
        Returns:
            公司聲量列表，按頻率排序
        """
        try:
            keywords = ['台股', '股票', '股市']
            result = self.news_fetcher.get_news_volume_with_news(keywords, hours, max_news_per_company=30)
            volume_dict = result['volume']
            news_by_symbol = result.get('news_by_symbol', {})
            
            company_names = {}
            company_names.update(Config.US_INDICES)
            company_names.update(Config.US_STOCKS)
            company_names.update(Config.TW_MARKETS)
            company_names.update(Config.INTERNATIONAL_MARKETS)
            
            volume_list = []
            for symbol, count in sorted(volume_dict.items(), key=lambda x: x[1], reverse=True)[:top_n]:
                volume_list.append({
                    'symbol': symbol,
                    'name': company_names.get(symbol, symbol),
                    'count': count,
                    'rank': len(volume_list) + 1,
                    'news': news_by_symbol.get(symbol, []),
                })
            
            return volume_list
        except Exception as e:
            print(f"Error in get_top_companies_by_volume: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_volume_summary(self, refresh: bool = False) -> Dict:
        """
        獲取聲量總覽
        
        Args:
            refresh: True 時略過快取並重新抓取
        
        Returns:
            聲量分析結果
        """
        now_ts = time.time()
        if (
            not refresh
            and self._volume_summary_cache is not None
            and (now_ts - self._volume_summary_cache_time) < VOLUME_SUMMARY_CACHE_SEC
        ):
            out = copy.deepcopy(self._volume_summary_cache)
            out["from_cache"] = True
            return out

        if not refresh:
            disk = load_entry("volume_summary")
            if disk and isinstance(disk, dict):
                t0 = load_entry_saved_at("volume_summary")
                if t0 is not None:
                    self._volume_summary_cache = copy.deepcopy(disk)
                    self._volume_summary_cache_time = t0
                    out = copy.deepcopy(disk)
                    out["from_cache"] = True
                    return out

        try:
            top_companies = self.get_top_companies_by_volume(hours=24, top_n=15)
        except Exception as e:
            print(f"Error in get_top_companies_by_volume: {str(e)}")
            top_companies = []

        result = {
            "top_companies": top_companies,
            "period": "24小時",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_companies": len(top_companies),
            "from_cache": False,
        }
        self._volume_summary_cache = copy.deepcopy(result)
        self._volume_summary_cache_time = now_ts
        to_disk = {k: v for k, v in result.items() if k != "from_cache"}
        save_entry("volume_summary", to_disk)
        return result

