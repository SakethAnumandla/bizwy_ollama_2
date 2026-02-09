import asyncio
from typing import List, Optional
from duckduckgo_search import DDGS
from app.config import settings
from app.core import logging
from app.models.schemas import SearchResult

logger = logging.logger

class SearchService:
    def __init__(self):
        self.provider = settings.SEARCH_PROVIDER.lower() if settings.SEARCH_PROVIDER else "none"
        self.max_results = settings.MAX_SEARCH_RESULTS

    async def search(self, query: str) -> List[SearchResult]:
        """
        Search for a query using the configured provider.
        """
        logger.info(f"Searching for '{query}' using {self.provider}")
        
        try:
            if self.provider == "duckduckgo":
                return await self._search_duckduckgo(query)
            elif self.provider == "serpapi":
                return await self._search_serpapi(query)
            elif self.provider == "googlesearch":
                return await self._search_googlesearch(query)
            else:
                # Default fallback
                logger.warning(f"Unknown search provider '{self.provider}', falling back to Google Search (python)")
                return await self._search_googlesearch(query)
        except Exception as e:
            logger.error(f"Search failed: {str(e)}", exc_info=True)
            return []

    async def _search_duckduckgo(self, query: str) -> List[SearchResult]:
        """
        Search using DuckDuckGo (HTML Scraper enforced)
        """
        # The library is unstable/broken in this environment.
        # Force fallback to HTML scraping which we verified works.
        return await self._search_duckduckgo_html_fallback(query)

    async def _search_duckduckgo_lib(self, query: str) -> List[SearchResult]:
        """
        Search using DuckDuckGo (Library - deprecated/backup)
        """
        results = []
        try:
            # DDGS is synchronous, so run in executor
            loop = asyncio.get_event_loop()
            ddgs = DDGS()
            # Run the synchronous generator in a thread pool
            ddg_results = await loop.run_in_executor(None, lambda: list(ddgs.text(query, max_results=self.max_results)))
            
            for idx, r in enumerate(ddg_results):
                results.append(SearchResult(
                    title=r.get('title', ''),
                    url=r.get('href', ''),
                    snippet=r.get('body', ''),
                    source="duckduckgo",
                    position=idx + 1
                ))
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            
        return results

    async def _search_duckduckgo_html_fallback(self, query: str) -> List[SearchResult]:
        """
        Fallback: Scrape DuckDuckGo HTML directly (Synchronous implementation run in thread pool)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self._search_duckduckgo_html_sync(query))

    def _search_duckduckgo_html_sync(self, query: str) -> List[SearchResult]:
        import httpx
        from bs4 import BeautifulSoup
        import urllib.parse
        
        results = []
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            # Use html.duckduckgo.com for simpler HTML scraping
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            logger.info(f"DDG Scraper: Requesting {url}")
            
            # Use synchronous client with timeout
            with httpx.Client(headers=headers, follow_redirects=True, timeout=30.0) as client:
                response = client.get(url)
                logger.info(f"DDG Scraper: Response Status {response.status_code}")
                
                if response.status_code != 200:
                    logger.error(f"DDG fallback failed with status {response.status_code}")
                    return []
                
                soup = BeautifulSoup(response.text, "html.parser")
                results_elems = soup.select(".result")
                logger.info(f"DDG Scraper: Found {len(results_elems)} result elements")
                
                # Parse results
                # DDG HTML structure: div.result -> h2.result__title -> a.result__a
                for idx, result in enumerate(results_elems):
                    if idx >= self.max_results:
                        break
                        
                    title_elem = result.select_one(".result__title a")
                    snippet_elem = result.select_one(".result__snippet")
                    
                    if title_elem:
                        # logical_url is often better than href which might be a redirect
                        link = title_elem.get('href', '')
                        # Simple decoding if needed, but often clean in HTML version
                        if "duckduckgo.com/l/?uddg=" in link:
                            try:
                                link = urllib.parse.unquote(link.split('uddg=')[1].split('&')[0])
                            except:
                                pass

                        results.append(SearchResult(
                            title=title_elem.get_text(strip=True),
                            url=link,
                            snippet=snippet_elem.get_text(strip=True) if snippet_elem else "",
                            source="duckduckgo_html",
                            position=idx + 1
                        ))
                        
            logger.info(f"DDG Scraper: Returning {len(results)} results")
        except Exception as e:
            logger.error(f"DuckDuckGo fallback search error: {e}", exc_info=True)
            
        return results

    async def _search_googlesearch(self, query: str) -> List[SearchResult]:
        """
        Search using googlesearch-python library
        """
        try:
            from googlesearch import search
        except ImportError:
            logger.error("googlesearch-python not installed. Please install it or use another provider.")
            return []
        
        results = []
        try:
            loop = asyncio.get_event_loop()
            # advanced=True returns objects with title, url, description
            search_results = await loop.run_in_executor(None, lambda: list(search(query, num_results=self.max_results, advanced=True)))
            
            for idx, r in enumerate(search_results):
                results.append(SearchResult(
                    title=r.title,
                    url=r.url,
                    snippet=r.description,
                    source="google",
                    position=idx + 1
                ))
        except Exception as e:
             logger.error(f"Google search error: {e}")

        return results

    async def _search_serpapi(self, query: str) -> List[SearchResult]:
        """
        Search using SerpAPI (Google/Bing)
        """
        # Placeholder for SerpAPI implementation
        # Requires 'google-search-results' package and API key
        logger.warning("SerpAPI implementation pending, returning empty list")
        return []

search_service = SearchService()
