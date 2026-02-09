import httpx
from bs4 import BeautifulSoup, Comment
from typing import Optional, List
from app.models.schemas import ProductContent
from app.core import logging

logger = logging.logger

class ScraperService:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.timeout = httpx.Timeout(10.0, connect=5.0)

    async def extract_content(self, url: str) -> Optional[ProductContent]:
        """
        Fetch and extract relevant content from a URL.
        """
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Check content type
                content_type = response.headers.get("content-type", "").lower()
                if "text/html" not in content_type:
                    logger.warning(f"Skipping non-HTML content from {url}: {content_type}")
                    return None

                return self._parse_html(url, response.text)
        except Exception as e:
            logger.warning(f"Failed to scrape {url}: {str(e)}")
            return None

    def _parse_html(self, url: str, html: str) -> ProductContent:
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
            element.decompose()
            
        # Remove comments
        for element in soup(text=lambda text: isinstance(text, Comment)):
            element.extract()

        # Extract title
        title = soup.title.string.strip() if soup.title else ""
        if not title:
            h1 = soup.find("h1")
            title = h1.get_text().strip() if h1 else ""

        # Extract meta description
        description = ""
        meta_desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if meta_desc:
            description = meta_desc.get("content", "").strip()

        # Extract main text content
        # Heuristic: Find container with most text properties
        # Simple fallback: Get all text
        text_content = soup.get_text(separator="\n", strip=True)
        
        # Limit text length to avoid token limits (approx 2000 words)
        text_content = text_content[:15000]

        # Extract images (simple heuristic)
        images = []
        for img in soup.find_all("img", src=True):
            src = img["src"]
            if src.startswith("http") and ("logo" not in src.lower()) and ("icon" not in src.lower()):
                images.append(src)
                if len(images) >= 5:
                    break

        return ProductContent(
            url=url,
            title=title,
            description=description,
            text_content=text_content,
            images=images
        )

scraper_service = ScraperService()
