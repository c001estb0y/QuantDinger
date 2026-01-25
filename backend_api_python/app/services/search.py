"""
Search service.
Integrates Google Custom Search (CSE), Bing Search API, and DuckDuckGo (free fallback).
Configuration is provided via environment variables (see env.example) through config_loader.
"""
import requests
import json
import time
from typing import List, Dict, Any, Optional
from app.utils.logger import get_logger
from app.utils.config_loader import load_addon_config

logger = get_logger(__name__)

# Track Google API quota status
_google_quota_exhausted = False
_google_quota_reset_time = 0


class SearchService:
    """Search service with automatic fallback."""
    
    def __init__(self):
        self._config = {}
        self._load_config()

    def _load_config(self):
        """Load config (re-read env-config on each call for local hot-reload)."""
        config = load_addon_config()
        self._config = config.get('search', {})
        self.provider = self._config.get('provider', 'google')
        self.max_results = int(self._config.get('max_results', 10))

    def search(self, query: str, num_results: int = None, date_restrict: str = None) -> List[Dict[str, Any]]:
        """
        Execute a web search with automatic fallback.
        
        Args:
            query: Search query
            num_results: Override default max results
            date_restrict: Time restriction like 'd7' (past 7 days), Google only
            
        Returns:
            List of search results
        """
        global _google_quota_exhausted, _google_quota_reset_time
        
        # 重新加载配置以支持热更新
        self._load_config()
        
        limit = num_results if num_results else self.max_results
        
        # Check if Google quota has reset (after midnight UTC typically)
        if _google_quota_exhausted and time.time() > _google_quota_reset_time:
            _google_quota_exhausted = False
            logger.info("Google API quota reset, re-enabling Google search")
        
        results = []
        
        if self.provider == 'bing':
            results = self._search_bing(query, limit)
        elif self.provider == 'duckduckgo':
            results = self._search_duckduckgo(query, limit)
        else:
            # Google with fallback
            if not _google_quota_exhausted:
                results = self._search_google(query, limit, date_restrict)
            
            # If Google failed or returned empty, try fallbacks
            if not results:
                logger.info("Google search failed or empty, trying fallback search engines...")
                # Try Bing first if configured
                results = self._search_bing(query, limit)
                
                # If Bing also failed, try DuckDuckGo (free, no API key needed)
                if not results:
                    results = self._search_duckduckgo(query, limit)
        
        return results

    def _search_google(self, query: str, num_results: int, date_restrict: str = None) -> List[Dict[str, Any]]:
        """Google Custom Search (CSE)."""
        global _google_quota_exhausted, _google_quota_reset_time
        
        api_key = self._config.get('google', {}).get('api_key')
        cx = self._config.get('google', {}).get('cx')
        
        if not api_key or not cx:
            logger.warning("Google Search is not configured (missing api_key or cx).")
            return []
            
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': api_key,
            'cx': cx,
            'q': query,
            'num': min(num_results, 10),  # Google API 限制每次最多10条
            'gl': 'cn' if any(c in query for c in ['A股', '利好', '利空', '财报']) else None # 针对中文内容优化地区
        }
        
        # 添加时间限制参数
        if date_restrict:
            params['dateRestrict'] = date_restrict
        
        try:
            response = requests.get(url, params=params, timeout=10)
            
            # Check for quota exceeded (429)
            if response.status_code == 429:
                logger.warning("Google Search API quota exceeded (429). Switching to fallback search engines.")
                _google_quota_exhausted = True
                # Set reset time to next day midnight UTC
                import datetime
                tomorrow = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
                _google_quota_reset_time = tomorrow.timestamp()
                return []
            
            response.raise_for_status()
            data = response.json()
            
            results = []
            if 'items' in data:
                for item in data['items']:
                    logger.debug(f"Search Item: {item.get('title')} - {item.get('link')}")
                    results.append({
                        'title': item.get('title'),
                        'link': item.get('link'),
                        'snippet': item.get('snippet'),
                        'source': 'Google',
                        'published': item.get('pagemap', {}).get('metatags', [{}])[0].get('article:published_time', '')
                    })
            else:
                logger.warning(f"Google Search returned no 'items'. Full response: {json.dumps(data, ensure_ascii=False)}")

            return results
            
        except requests.exceptions.HTTPError as e:
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                logger.warning("Google Search API quota exceeded. Switching to fallback.")
                _google_quota_exhausted = True
                import datetime
                tomorrow = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
                _google_quota_reset_time = tomorrow.timestamp()
            else:
                logger.error(f"Google search failed: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"Response: {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Google search failed: {e}")
            return []

    def _search_bing(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Bing search."""
        api_key = self._config.get('bing', {}).get('api_key')
        
        if not api_key:
            logger.warning("Bing Search is not configured (missing api_key).")
            return []
            
        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": api_key}
        params = {
            "q": query,
            "count": num_results,
            "textDecorations": True,
            "textFormat": "HTML"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            if 'webPages' in data and 'value' in data['webPages']:
                for item in data['webPages']['value']:
                    results.append({
                        'title': item.get('name'),
                        'link': item.get('url'),
                        'snippet': item.get('snippet'),
                        'source': 'Bing',
                        'published': item.get('datePublished', '')
                    })
            return results
            
        except Exception as e:
            logger.error(f"Bing search failed: {e}")
            return []

    def _search_duckduckgo(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """
        DuckDuckGo search (free, no API key required).
        Uses the DuckDuckGo HTML search endpoint.
        """
        try:
            # Use DuckDuckGo Instant Answer API
            url = "https://api.duckduckgo.com/"
            params = {
                'q': query,
                'format': 'json',
                'no_html': 1,
                'skip_disambig': 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            
            # Get results from RelatedTopics
            related_topics = data.get('RelatedTopics', [])
            for topic in related_topics[:num_results]:
                if isinstance(topic, dict):
                    if 'FirstURL' in topic:
                        results.append({
                            'title': topic.get('Text', '')[:100],
                            'link': topic.get('FirstURL', ''),
                            'snippet': topic.get('Text', ''),
                            'source': 'DuckDuckGo',
                            'published': ''
                        })
                    # Handle nested topics
                    elif 'Topics' in topic:
                        for sub_topic in topic['Topics']:
                            if len(results) >= num_results:
                                break
                            if 'FirstURL' in sub_topic:
                                results.append({
                                    'title': sub_topic.get('Text', '')[:100],
                                    'link': sub_topic.get('FirstURL', ''),
                                    'snippet': sub_topic.get('Text', ''),
                                    'source': 'DuckDuckGo',
                                    'published': ''
                                })
            
            # Also check AbstractURL and AbstractText
            if data.get('AbstractURL') and len(results) < num_results:
                results.insert(0, {
                    'title': data.get('Heading', query),
                    'link': data.get('AbstractURL', ''),
                    'snippet': data.get('AbstractText', ''),
                    'source': 'DuckDuckGo',
                    'published': ''
                })
            
            # If no results from Instant Answer, try HTML scraping as fallback
            if not results:
                results = self._search_duckduckgo_html(query, num_results)
            
            if results:
                logger.info(f"DuckDuckGo search returned {len(results)} results")
            
            return results[:num_results]
            
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            # Try HTML fallback
            return self._search_duckduckgo_html(query, num_results)

    def _search_duckduckgo_html(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """
        DuckDuckGo HTML search fallback.
        Scrapes the lite HTML version for better results.
        """
        try:
            url = "https://lite.duckduckgo.com/lite/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            data = {'q': query}
            
            response = requests.post(url, headers=headers, data=data, timeout=10)
            response.raise_for_status()
            
            results = []
            
            # Simple HTML parsing without BeautifulSoup
            html = response.text
            
            # Find all result links (they have class="result-link")
            import re
            
            # Pattern to find result entries
            link_pattern = r'<a[^>]*class="result-link"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
            snippet_pattern = r'<td[^>]*class="result-snippet"[^>]*>([^<]*)</td>'
            
            links = re.findall(link_pattern, html)
            snippets = re.findall(snippet_pattern, html)
            
            for i, (link, title) in enumerate(links[:num_results]):
                snippet = snippets[i] if i < len(snippets) else ''
                if link and title:
                    results.append({
                        'title': title.strip(),
                        'link': link,
                        'snippet': snippet.strip(),
                        'source': 'DuckDuckGo',
                        'published': ''
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"DuckDuckGo HTML search failed: {e}")
            return []
