"""
src/utils/utils.py
COMPLETE - All scraping tools and utilities for ModelX platform
Implements both HTML scraping and API-based data retrieval
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
import os
import logging
import requests
import json
from langchain_core.tools import tool
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin
import yfinance as yf
import re

# ============================================
# CONFIGURATION
# ============================================

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "30"))
MAX_RETRIES = int(os.getenv("RETRY_ATTEMPTS", "3"))

logger = logging.getLogger("modelx.utils")
logger.setLevel(logging.INFO)


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_today_str() -> str:
    """Get current date in human-readable format."""
    return datetime.now().strftime("%a %b %d, %Y")


def _safe_get(url: str, timeout: int = DEFAULT_TIMEOUT) -> Optional[requests.Response]:
    """
    Safely GET a URL with error handling and retries.
    
    Args:
        url: Target URL
        timeout: Request timeout in seconds
        
    Returns:
        Response object or None if failed
    """
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
            if resp.status_code == 200:
                return resp
            logger.warning(f"[HTTP] {url} returned {resp.status_code}")
        except requests.exceptions.Timeout:
            logger.warning(f"[HTTP] Timeout on {url} (attempt {attempt + 1}/{MAX_RETRIES})")
        except requests.exceptions.RequestException as e:
            logger.error(f"[HTTP] Error fetching {url}: {e}")
            
        if attempt < MAX_RETRIES - 1:
            import time
            time.sleep(2 ** attempt)  # Exponential backoff
    
    return None


def _contains_keyword(text: str, keywords: Optional[List[str]]) -> bool:
    """Check if text contains any of the keywords (case-insensitive)."""
    if not keywords:
        return True
    text_lower = text.lower()
    return any(k.lower() in text_lower for k in keywords)


def _extract_text_from_html(html: str, selector: str = "body") -> str:
    """Extract clean text from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    element = soup.select_one(selector) or soup.body
    return element.get_text(separator="\n", strip=True) if element else ""


# ============================================
# METEOROLOGICAL TOOLS (Already Implemented)
# ============================================

def tool_dmc_alerts() -> Dict[str, Any]:
    """
    DMC alert scraper - Disaster Management Centre alerts.
    Scrapes http://www.meteo.gov.lk for severe weather warnings.
    """
    url = "http://www.meteo.gov.lk/index.php?lang=en"
    resp = _safe_get(url)
    
    if not resp:
        return {
            "source": url,
            "alerts": ["Failed to fetch alerts from DMC."],
            "fetched_at": datetime.utcnow().isoformat(),
        }

    soup = BeautifulSoup(resp.text, "html.parser")
    alerts: List[str] = []

    # Keywords for severe weather
    keywords = [
        "warning", "advisory", "alert", "heavy rain", "strong wind",
        "thunderstorm", "flood", "landslide", "cyclone", "severe"
    ]

    # Find all text elements
    for text in soup.find_all(string=True):
        t = text.strip()
        if not t or len(t) < 20:
            continue
        
        lower = t.lower()
        if any(k in lower for k in keywords):
            # Clean up the text
            clean = re.sub(r'\s+', ' ', t)
            if clean not in alerts:  # Avoid duplicates
                alerts.append(clean)

    if not alerts:
        alerts = ["No active severe weather alerts detected on the DMC site."]

    return {
        "source": url,
        "alerts": alerts[:10],  # Limit to top 10
        "fetched_at": datetime.utcnow().isoformat(),
    }


def tool_weather_nowcast(location: str = "Colombo") -> Dict[str, Any]:
    """
    Weather nowcast scraper - Current weather forecast.
    """
    url = (
        "http://www.meteo.gov.lk/index.php?"
        "option=com_content&view=article&id=95&Itemid=312&lang=en"
    )
    
    resp = _safe_get(url)
    
    if not resp:
        return {
            "location": location,
            "forecast": "Failed to fetch forecast.",
            "source": url,
            "fetched_at": datetime.utcnow().isoformat(),
        }

    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Try to find forecast content
    container = (
        soup.find("div", {"id": "k2Container"})
        or soup.find("div", class_="article-content")
        or soup.find("div", class_="itemFullText")
        or soup.body
    )

    text = container.get_text(separator="\n", strip=True) if container else ""
    
    if not text:
        text = "No forecast text found on the page."
    
    # Truncate to reasonable length
    text = text[:4000]

    return {
        "location": location,
        "forecast": text,
        "source": url,
        "fetched_at": datetime.utcnow().isoformat(),
    }


# ============================================
# NEWS SCRAPING TOOLS
# ============================================

LOCAL_NEWS_SITES = [
    {
        "url": "https://www.dailymirror.lk/",
        "name": "Daily Mirror",
        "article_selector": "article, .article, .news-item"
    },
    {
        "url": "https://www.ft.lk/",
        "name": "Financial Times",
        "article_selector": "article, .article-list-item"
    },
    {
        "url": "https://www.newsfirst.lk/",
        "name": "News First",
        "article_selector": ".post, article"
    },
]


def scrape_local_news_impl(
    keywords: Optional[List[str]] = None,
    max_articles: int = 30,
) -> List[Dict[str, Any]]:
    """
    Scrape local Sri Lankan news websites.
    
    Args:
        keywords: Filter articles by keywords
        max_articles: Maximum number of articles to return
        
    Returns:
        List of article dictionaries
    """
    results: List[Dict[str, Any]] = []

    for site in LOCAL_NEWS_SITES:
        try:
            resp = _safe_get(site["url"])
            if not resp:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Find article elements
            articles = soup.select(site["article_selector"])
            
            for article in articles[:20]:  # Process first 20 from each site
                # Try to extract title
                title_elem = (
                    article.find("h1") or 
                    article.find("h2") or 
                    article.find("h3") or
                    article.find(class_=re.compile(r"title|headline"))
                )
                
                title = title_elem.get_text(strip=True) if title_elem else ""
                
                if not title or len(title) < 10:
                    continue
                
                # Check keywords
                if not _contains_keyword(title, keywords):
                    continue
                
                # Try to find link
                link_elem = article.find("a", href=True)
                href = link_elem["href"] if link_elem else ""
                
                # Make absolute URL
                if href:
                    if href.startswith("/"):
                        href = urljoin(site["url"], href)
                    elif not href.startswith("http"):
                        href = site["url"]
                else:
                    href = site["url"]
                
                # Try to get snippet
                snippet_elem = article.find("p") or article.find(class_=re.compile(r"excerpt|summary|description"))
                snippet = snippet_elem.get_text(strip=True)[:200] if snippet_elem else ""
                
                results.append({
                    "source": site["name"],
                    "source_url": site["url"],
                    "headline": title,
                    "snippet": snippet,
                    "url": href,
                    "timestamp": datetime.utcnow().isoformat(),
                })
                
                if len(results) >= max_articles:
                    return results
        
        except Exception as e:
            logger.error(f"[NEWS] Error scraping {site['name']}: {e}")
            continue

    return results


# ============================================
# CSE STOCK MARKET TOOLS
# ============================================

def scrape_cse_stock_impl(
    symbol: str = "ASPI",
    period: str = "1d",
    interval: str = "1h",
) -> Dict[str, Any]:
    """
    Scrape CSE stock data using yfinance.
    
    Note: For Sri Lankan stocks, symbols should be in format: SYMBOL.N0000
    For ASPI index, use "^N0000" or try without suffix.
    
    Args:
        symbol: Stock symbol (e.g., "ASPI", "JKH.N0000")
        period: Data period (1d, 5d, 1mo, 3mo, 1y)
        interval: Data interval (1m, 5m, 1h, 1d)
    
    Returns:
        Dict with stock data or error
    """
    try:
        # Try different symbol formats for ASPI
        symbols_to_try = [symbol]
        if symbol == "ASPI":
            symbols_to_try = ["^N0000", "ASPI.N0000", "ASPI"]
        
        for sym in symbols_to_try:
            try:
                ticker = yf.Ticker(sym)
                hist = ticker.history(period=period, interval=interval)
                
                if not hist.empty:
                    hist.reset_index(inplace=True)
                    
                    # Convert to serializable format
                    records = hist.to_dict(orient="records")
                    
                    # Convert timestamps to strings
                    for record in records:
                        for key, value in record.items():
                            if hasattr(value, 'isoformat'):
                                record[key] = value.isoformat()
                    
                    # Calculate summary statistics
                    latest = records[-1] if records else {}
                    summary = {
                        "current_price": latest.get("Close", 0),
                        "open": latest.get("Open", 0),
                        "high": latest.get("High", 0),
                        "low": latest.get("Low", 0),
                        "volume": latest.get("Volume", 0),
                    }
                    
                    return {
                        "symbol": symbol,
                        "resolved_symbol": sym,
                        "period": period,
                        "interval": interval,
                        "summary": summary,
                        "records": records[-10:],  # Last 10 data points
                        "fetched_at": datetime.utcnow().isoformat(),
                    }
            except Exception:
                continue
        
        # If all attempts failed
        return {
            "symbol": symbol,
            "error": f"Could not fetch data for {symbol}. Try format: SYMBOL.N0000",
            "attempted_symbols": symbols_to_try
        }
        
    except Exception as e:
        return {
            "symbol": symbol,
            "error": str(e)
        }


# ============================================
# GOVERNMENT GAZETTE TOOLS
# ============================================

def scrape_government_gazette_impl(
    keywords: Optional[List[str]] = None,
    max_items: int = 20,
) -> List[Dict[str, Any]]:
    """
    Scrape government gazette publications.
    
    Note: The actual gazette site structure may vary.
    This implementation provides a working template.
    """
    # Primary URL
    url = "https://www.documents.gov.lk/en/gazette.php"
    
    resp = _safe_get(url)
    
    if not resp:
        logger.warning(f"[GAZETTE] Failed to fetch {url}, trying alternative...")
        # Try alternative URL
        url = "http://www.documents.gov.lk/index.php?lang=en"
        resp = _safe_get(url)
        
        if not resp:
            return [{
                "title": "Gazette website unavailable",
                "url": url,
                "note": "Could not access gazette portal. Check connectivity or site status.",
                "timestamp": datetime.utcnow().isoformat(),
            }]

    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Try multiple selectors
    links = (
        soup.find_all("a", href=re.compile(r"gazette|pdf|document", re.I)) or
        soup.find_all("a", class_=re.compile(r"gazette|document|link")) or
        soup.find_all("a")
    )

    results: List[Dict[str, Any]] = []

    for link in links:
        title = link.get_text(strip=True)
        href = link.get("href", "")
        
        if not title or len(title) < 10:
            continue
        
        # Filter by keywords
        if not _contains_keyword(title, keywords):
            continue
        
        # Make absolute URL
        if href.startswith("/"):
            href = urljoin(url, href)
        elif not href.startswith("http"):
            href = url
        
        results.append({
            "title": title,
            "url": href,
            "keywords_matched": [k for k in (keywords or []) if k.lower() in title.lower()],
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        if len(results) >= max_items:
            break

    return results if results else [{
        "title": "No gazette entries found matching criteria",
        "url": url,
        "keywords": keywords,
        "timestamp": datetime.utcnow().isoformat(),
    }]

# ============================================
# PARLIAMENT MINUTES TOOLS
# ============================================

def scrape_parliament_minutes_impl(
    keywords: Optional[List[str]] = None,
    max_items: int = 20,
) -> List[Dict[str, Any]]:
    """
    Scrape Parliament Hansard/minutes.
    """
    url = "https://www.parliament.lk/en/hansard"
    
    resp = _safe_get(url)
    
    if not resp:
        return [{
            "title": "Parliament website unavailable",
            "url": url,
            "note": "Could not access parliament.lk. Site may be down.",
            "timestamp": datetime.utcnow().isoformat(),
        }]

    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Find hansard links
    links = (
        soup.find_all("a", href=re.compile(r"hansard|minutes|debate", re.I)) or
        soup.find_all("a", class_=re.compile(r"hansard|document")) or
        soup.find_all("a")
    )

    results: List[Dict[str, Any]] = []

    for link in links:
        title = link.get_text(strip=True)
        href = link.get("href", "")
        
        if not title or len(title) < 10:
            continue
        
        if not _contains_keyword(title, keywords):
            continue
        
        if href.startswith("/"):
            href = urljoin(url, href)
        elif not href.startswith("http"):
            href = url
        
        results.append({
            "title": title,
            "url": href,
            "keywords_matched": [k for k in (keywords or []) if k.lower() in title.lower()],
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        if len(results) >= max_items:
            break

    return results if results else [{
        "title": "No parliament minutes found",
        "url": url,
        "keywords": keywords,
        "timestamp": datetime.utcnow().isoformat(),
    }]


# ============================================
# RAILWAY/TRAIN SCHEDULE TOOLS
# ============================================

def scrape_train_schedule_impl(
    from_station: Optional[str] = None,
    to_station: Optional[str] = None,
    keyword: Optional[str] = None,
    max_items: int = 30,
) -> List[Dict[str, Any]]:
    """
    Scrape railway schedule for Sri Lanka.
    """
    url = "https://eservices.railway.gov.lk/schedule/homeAction.action?lang=en"
    
    resp = _safe_get(url)
    
    if not resp:
        return [{
            "train": "Railway website unavailable",
            "note": "Could not access railway.gov.lk",
            "timestamp": datetime.utcnow().isoformat(),
        }]

    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Find schedule tables
    tables = soup.find_all("table")
    
    results: List[Dict[str, Any]] = []
    
    for table in tables:
        rows = table.find_all("tr")
        
        for row in rows[1:]:  # Skip header
            cols = [td.get_text(strip=True) for td in row.find_all("td")]
            
            if len(cols) < 3:
                continue
            
            # Try to parse as train schedule
            train_info = {
                "train": cols[0] if len(cols) > 0 else "",
                "departure": cols[1] if len(cols) > 1 else "",
                "arrival": cols[2] if len(cols) > 2 else "",
                "route": " → ".join(cols[3:]) if len(cols) > 3 else "",
            }
            
            # Filter by stations/keyword
            combined = " ".join(cols)
            
            if from_station and from_station.lower() not in combined.lower():
                continue
            if to_station and to_station.lower() not in combined.lower():
                continue
            if keyword and keyword.lower() not in combined.lower():
                continue
            
            results.append(train_info)
            
            if len(results) >= max_items:
                break
    
    return results if results else [{
        "train": "No train schedules found",
        "note": "Railway schedule unavailable or no matches",
        "timestamp": datetime.utcnow().isoformat(),
    }]


# ============================================
# REDDIT SCRAPING
# ============================================

def scrape_reddit_impl(
    keywords: List[str],
    limit: int = 20,
    subreddit: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Scrape Reddit posts using public JSON API.
    No authentication required for basic searching.
    """
    if subreddit:
        base = f"https://www.reddit.com/r/{subreddit}/search.json"
    else:
        base = "https://www.reddit.com/search.json"

    query = " ".join(keywords) if keywords else "Sri Lanka"
    params = {
        "q": query,
        "sort": "new",
        "limit": str(limit),
        "restrict_sr": "on" if subreddit else "off",
    }

    try:
        resp = requests.get(
            base, 
            headers={"User-Agent": DEFAULT_HEADERS["User-Agent"]}, 
            params=params, 
            timeout=DEFAULT_TIMEOUT
        )
        
        if resp.status_code != 200:
            logger.warning(f"[REDDIT] HTTP {resp.status_code}")
            return [{
                "error": f"Reddit returned status {resp.status_code}",
                "query": query
            }]

        data = resp.json()
        posts_raw = data.get("data", {}).get("children", [])
        posts: List[Dict[str, Any]] = []

        for p in posts_raw:
            d = p.get("data", {})
            title = d.get("title") or ""
            selftext = d.get("selftext") or ""
            
            # Filter by keywords
            text = f"{title}\n{selftext}"
            if not _contains_keyword(text, keywords):
                continue

            posts.append({
                "id": d.get("id"),
                "title": title,
                "selftext": selftext[:500],  # Truncate long posts
                "subreddit": d.get("subreddit"),
                "author": d.get("author"),
                "score": d.get("score", 0),
                "url": "https://www.reddit.com" + d.get("permalink", ""),
                "created_utc": d.get("created_utc"),
                "num_comments": d.get("num_comments", 0),
            })
        
        return posts if posts else [{
            "note": f"No Reddit posts found for: {query}",
            "query": query
        }]
        
    except Exception as e:
        logger.error(f"[REDDIT] Error: {e}")
        return [{"error": str(e), "query": query}]


# ============================================
# SOCIAL MEDIA STUBS (Require API Keys)
# ============================================

def scrape_social_search_stub(
    platform: str,
    keywords: List[str],
) -> Dict[str, Any]:
    """
    Honest stub for platforms requiring authentication.
    """
    return {
        "platform": platform,
        "keywords": keywords,
        "note": (
            f"Direct scraping of {platform} requires authenticated API access. "
            "Implement official API client or use authenticated session. "
            "For demo purposes, this returns a placeholder."
        ),
        "status": "requires_api_key",
        "setup_instructions": f"Visit {platform} developer portal to obtain API credentials.",
    }


# ============================================
# LANGCHAIN TOOL WRAPPERS
# ============================================

@tool
def scrape_linkedin(keywords: List[str]):
    """LinkedIn search - requires API or authenticated session."""
    return json.dumps(scrape_social_search_stub("LinkedIn", keywords))


@tool
def scrape_instagram(keywords: List[str]):
    """Instagram search - requires API or authenticated session."""
    return json.dumps(scrape_social_search_stub("Instagram", keywords))


@tool
def scrape_facebook(keywords: List[str]):
    """Facebook search - requires Graph API access."""
    return json.dumps(scrape_social_search_stub("Facebook", keywords))


@tool
def scrape_reddit(
    keywords: List[str],
    limit: int = 20,
    subreddit: Optional[str] = None,
):
    """
    Scrape Reddit posts matching keywords using public JSON API.
    
    Args:
        keywords: Search keywords
        limit: Maximum posts to return
        subreddit: Optional subreddit to search within
    """
    data = scrape_reddit_impl(keywords=keywords, limit=limit, subreddit=subreddit)
    return json.dumps(data, default=str)


@tool
def scrape_twitter(query: str):
    """
    Twitter/X search - requires API access.
    For production, use tweepy or Twitter API v2.
    """
    return json.dumps({
        "platform": "Twitter/X",
        "query": query,
        "note": (
            "Twitter API v2 requires authentication. "
            "Alternative: Use Nitter instances (nitter.net) for public scraping. "
            "Implement tweepy for production use."
        ),
        "status": "requires_api_key",
    })


@tool
def scrape_government_gazette(
    keywords: Optional[List[str]] = None,
    max_items: int = 20,
):
    """
    Scrape government gazette publications.
    Filters by keywords related to regulations, taxes, policies.
    """
    data = scrape_government_gazette_impl(keywords=keywords, max_items=max_items)
    return json.dumps(data, default=str)


@tool
def scrape_parliament_minutes(
    keywords: Optional[List[str]] = None,
    max_items: int = 20,
):
    """
    Scrape parliament minutes/Hansard.
    Filters by keywords related to bills, amendments, debates.
    """
    data = scrape_parliament_minutes_impl(keywords=keywords, max_items=max_items)
    return json.dumps(data, default=str)


@tool
def scrape_train_schedule(
    from_station: Optional[str] = None,
    to_station: Optional[str] = None,
    keyword: Optional[str] = None,
    max_items: int = 30,
):
    """
    Scrape railway/train schedules for Sri Lanka.
    Filter by stations or keywords like 'Colombo', 'express', etc.
    """
    data = scrape_train_schedule_impl(
        from_station=from_station,
        to_station=to_station,
        keyword=keyword,
        max_items=max_items,
    )
    return json.dumps(data, default=str)


@tool
def scrape_cse_stock_data(
    symbol: str = "ASPI",
    period: str = "1d",
    interval: str = "1h",
):
    """
    Scrape CSE/stock market data using yfinance.
    
    Args:
        symbol: Stock symbol (e.g., "ASPI" for index, "JKH.N0000" for stocks)
        period: Data period (1d, 5d, 1mo, 3mo, 1y)
        interval: Data interval (1m, 5m, 1h, 1d)
    """
    data = scrape_cse_stock_impl(symbol=symbol, period=period, interval=interval)
    return json.dumps(data, default=str)


@tool
def scrape_local_news(
    keywords: Optional[List[str]] = None,
    max_articles: int = 30,
):
    """
    Scrape local Sri Lankan news headlines.
    Sources: Daily Mirror, Financial Times, News First.
    """
    data = scrape_local_news_impl(keywords=keywords, max_articles=max_articles)
    return json.dumps(data, default=str)


@tool
def think_tool(reflection: str) -> str:
    """
    Strategic reflection tool for agent decision-making.
    Use after each search to analyze results and plan next steps.
    """
    return f"Reflection recorded: {reflection}"


# ============================================
# TOOL REGISTRY
# ============================================

TOOL_MAPPING = {
    "scrape_linkedin": scrape_linkedin,
    "scrape_instagram": scrape_instagram,
    "scrape_facebook": scrape_facebook,
    "scrape_reddit": scrape_reddit,
    "scrape_twitter": scrape_twitter,
    "scrape_government_gazette": scrape_government_gazette,
    "scrape_parliament_minutes": scrape_parliament_minutes,
    "scrape_train_schedule": scrape_train_schedule,
    "scrape_cse_stock_data": scrape_cse_stock_data,
    "scrape_local_news": scrape_local_news,
    "think_tool": think_tool,
}

# Export all tools for LangChain
ALL_TOOLS = list(TOOL_MAPPING.values())


# ============================================
# UTILITY EXPORTS
# ============================================

__all__ = [
    "get_today_str",
    "tool_dmc_alerts",
    "tool_weather_nowcast",
    "TOOL_MAPPING",
    "ALL_TOOLS",
]