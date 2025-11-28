from datetime import datetime
from typing_extensions import Annotated, Dict, Any, List, Literal, Optional, List 
import os
import logging
import requests
import json
from langchain_core.tools import tool, InjectedToolArg
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import yfinance as yf


def get_today_str() -> str:
    """Get current data in a human-readable format."""
    return datetime.now().strftime("%a %b %d, %Y")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def _contains_keyword(text: str, keywords: List[str]) -> bool:
    if not keywords:
        return True
    text_lower = text.lower()
    return any(k.lower() in text_lower for k in keywords)


def _safe_get(url: str, timeout: int = 10) -> Optional[requests.Response]:
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        if resp.status_code == 200:
            return resp
        print(f"[SCRAPER] Non-200 status {resp.status_code} for {url}")
        return None
    except Exception as e:
        print(f"[SCRAPER] Error fetching {url}: {e}")
        return None

@tool 
def think_tool(reflection:str) -> str:
    """
    Tool for strategic reflection on execution progress and decision-making.

    Use this tool after each search to analyze results and plan next steps systematically.
    This creates a deliberate pause in customer query execution workflow for quality decision-making.

    When to use:
    - After receiving search results: What key information did I find?
    - Before deciding next steps: Do I have enough to answer comprehensively?
    - When assessing execution gaps: What specific execution am I still missing?
    - Before concluding execution: Can I provide a complete answer now?

    Reflection should address:
    1. Analysis of current findings - What concrete information have I gathered?
    2. Gap assessment - What crucial execution or information is still missing?
    3. Quality evaluation - Do I have sufficient evidence/examples for a good answer?
    4. Strategic decision - Should I continue execution or provide my output?

    Args: 
        reflection: Your detailed reflection on the execution progress, findings, gaps, and next steps

    Returns:
        Confirmation that reflection was recorded for decision-making
    """
    return f"Reflection recorded: {reflection}"


# ---- 2.1 NEWS (Local sites, HTML scraping) ----

LOCAL_NEWS_SITES = [
    "https://www.dailymirror.lk/",
    "https://www.ft.lk/",
    "https://www.newsfirst.lk/",
]


def scrape_local_news_impl(
    keywords: Optional[List[str]] = None,
    max_articles: int = 30,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    for site in LOCAL_NEWS_SITES:
        resp = _safe_get(site)
        if not resp:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        # Very generic: you can tune per-site selectors later
        candidates = soup.find_all(["a", "h1", "h2", "h3"])

        for tag in candidates:
            title = tag.get_text(strip=True)
            href = tag.get("href") or ""

            if not title:
                continue
            if not _contains_keyword(title, keywords or []):
                continue

            # Build absolute URLs for relative links when possible
            if href and href.startswith("/"):
                href_full = site.rstrip("/") + href
            elif href.startswith("http"):
                href_full = href
            else:
                href_full = site

            results.append(
                {
                    "source": site,
                    "headline": title,
                    "url": href_full,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

            if len(results) >= max_articles:
                return results

    return results


# ---- 2.2 CSE STOCK (yfinance, API-like) ----

def scrape_cse_stock_impl(
    symbol: str,
    period: str = "1mo",
    interval: str = "1d",
) -> Dict[str, Any]:
    """
    Hybrid: uses yfinance (Yahoo Finance) to fetch OHLCV for a given symbol.

    For Sri Lankan stocks, the user must pass the correct Yahoo symbol,
    e.g. 'COMB.N0000' or whatever mapping they use.
    """
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        hist.reset_index(inplace=True)

        # Convert DataFrame to a compact JSON-like structure
        records = hist.to_dict(orient="records")
        return {
            "symbol": symbol,
            "period": period,
            "interval": interval,
            "records": records,
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


# ---- 2.3 Government Gazette (HTML scraping) ----

def scrape_government_gazette_impl(
    keywords: Optional[List[str]] = None,
    max_items: int = 20,
) -> List[Dict[str, Any]]:
    """
    Example scraper for Sri Lankan gazette portal.
    You'll probably need to adjust URL and selectors to match the real site.
    """
    # TODO: Replace with the actual gazette listing URL
    url = "https://www.documents.gov.lk/en/gazette.php"  # Example only

    resp = _safe_get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.find_all("a")

    results: List[Dict[str, Any]] = []

    for a in rows:
        title = a.get_text(strip=True)
        href = a.get("href") or ""
        if not title:
            continue

        if not _contains_keyword(title, keywords or []):
            continue

        if href.startswith("/"):
            href_full = url.rstrip("/") + href
        elif href.startswith("http"):
            href_full = href
        else:
            href_full = url

        results.append(
            {
                "title": title,
                "url": href_full,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        if len(results) >= max_items:
            break

    return results


# ---- 2.4 Parliament Minutes (HTML scraping) ----

def scrape_parliament_minutes_impl(
    keywords: Optional[List[str]] = None,
    max_items: int = 20,
) -> List[Dict[str, Any]]:
    """
    Example scraper for Parliament Hansard/minutes.
    Again, URL + selectors may need to be tuned to the real site.
    """
    # TODO: Replace with real site
    url = "https://www.parliament.lk/en/hansard"  # Example only

    resp = _safe_get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    items = soup.find_all("a")

    results: List[Dict[str, Any]] = []

    for a in items:
        title = a.get_text(strip=True)
        href = a.get("href") or ""
        if not title:
            continue

        if not _contains_keyword(title, keywords or []):
            continue

        if href.startswith("/"):
            href_full = url.rstrip("/") + href
        elif href.startswith("http"):
            href_full = href
        else:
            href_full = url

        results.append(
            {
                "title": title,
                "url": href_full,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        if len(results) >= max_items:
            break

    return results


# ---- 2.5 Train Schedule (HTML scraping) ----

def scrape_train_schedule_impl(
    from_station: Optional[str] = None,
    to_station: Optional[str] = None,
    keyword: Optional[str] = None,
    max_items: int = 30,
) -> List[Dict[str, Any]]:
    """
    Example railway schedule scraper.
    You will need to tailor this to the actual eservices.railway.gov.lk schedule page.
    """
    # TODO: replace with real search endpoint or listing page
    url = "https://eservices.railway.gov.lk/schedule/"  # Example only

    resp = _safe_get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.find_all("tr")

    results: List[Dict[str, Any]] = []

    for row in rows:
        cols = [c.get_text(strip=True) for c in row.find_all("td")]
        if len(cols) < 3:
            continue

        train_name = cols[0]
        departure = cols[1]
        arrival = cols[2]

        combined = " ".join(cols)
        if from_station and from_station.lower() not in combined.lower():
            continue
        if to_station and to_station.lower() not in combined.lower():
            continue
        if keyword and keyword.lower() not in combined.lower():
            continue

        results.append(
            {
                "train": train_name,
                "departure": departure,
                "arrival": arrival,
            }
        )
        if len(results) >= max_items:
            break

    return results


# ---- 2.6 Reddit (public JSON API) ----

def scrape_reddit_impl(
    keywords: List[str],
    limit: int = 20,
    subreddit: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Hybrid: use Reddit's public JSON endpoints (no auth for basic searching).
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
            base, headers={"User-Agent": "Mozilla/5.0"}, params=params, timeout=10
        )
        if resp.status_code != 200:
            print(f"[REDDIT] HTTP {resp.status_code}")
            return []

        data = resp.json()
        posts_raw = data.get("data", {}).get("children", [])
        posts: List[Dict[str, Any]] = []

        for p in posts_raw:
            d = p.get("data", {})
            title = d.get("title") or ""
            selftext = d.get("selftext") or ""
            text = f"{title}\n{selftext}"
            if not _contains_keyword(text, keywords or []):
                continue

            posts.append(
                {
                    "id": d.get("id"),
                    "title": title,
                    "selftext": selftext,
                    "subreddit": d.get("subreddit"),
                    "url": "https://www.reddit.com" + d.get("permalink", ""),
                    "created_utc": d.get("created_utc"),
                }
            )
        return posts
    except Exception as e:
        print(f"[REDDIT] Error: {e}")
        return []


# ---- 2.7 Social (LinkedIn/IG/FB/Twitter) – honest limited stubs ----

def scrape_social_search_stub(
    platform: str,
    keywords: List[str],
) -> Dict[str, Any]:
    """
    Honest stub: explains that real scraping for this platform requires API or authenticated session.
    Still returns a structured object so your pipeline doesn't break.
    """
    return {
        "platform": platform,
        "keywords": keywords,
        "note": (
            f"Direct scraping of {platform} requires an authenticated session/API. "
            "Implement session-based scraping or official API client here."
        ),
    }


# ==========================================
# 3. TOOLS (LangChain @tool wrappers)
# ==========================================

@tool
def scrape_linkedin(keywords: List[str]):
    """Hybrid placeholder for LinkedIn search – requires API or authenticated session."""
    return json.dumps(scrape_social_search_stub("LinkedIn", keywords))


@tool
def scrape_instagram(keywords: List[str]):
    """Hybrid placeholder for Instagram search – requires API or authenticated session."""
    return json.dumps(scrape_social_search_stub("Instagram", keywords))


@tool
def scrape_facebook(keywords: List[str]):
    """Hybrid placeholder for Facebook search – requires API or authenticated session."""
    return json.dumps(scrape_social_search_stub("Facebook", keywords))


@tool
def scrape_reddit(
    keywords: List[str],
    limit: int = 20,
    subreddit: Optional[str] = None,
):
    """Scrape Reddit posts matching keywords using public JSON endpoints."""
    data = scrape_reddit_impl(keywords=keywords, limit=limit, subreddit=subreddit)
    return json.dumps(data)


@tool
def scrape_twitter(query: str):
    """
    Hybrid placeholder for Twitter/X search – realistically should use API
    or a Nitter-like mirror. Implement that logic here if you have a stable endpoint.
    """
    return json.dumps(
        {
            "platform": "Twitter/X",
            "query": query,
            "note": (
                "Implement X/Twitter API or Nitter-based scraping here; "
                "this is a structured placeholder."
            ),
        }
    )


@tool
def scrape_government_gazette(
    keywords: Optional[List[str]] = None,
    max_items: int = 20,
):
    """Scrapes government gazette publications (HTML, keyword-filtered)."""
    data = scrape_government_gazette_impl(keywords=keywords, max_items=max_items)
    return json.dumps(data)


@tool
def scrape_parliament_minutes(
    keywords: Optional[List[str]] = None,
    max_items: int = 20,
):
    """Scrapes parliament minutes/Hansard (HTML, keyword-filtered)."""
    data = scrape_parliament_minutes_impl(keywords=keywords, max_items=max_items)
    return json.dumps(data)


@tool
def scrape_train_schedule(
    from_station: Optional[str] = None,
    to_station: Optional[str] = None,
    keyword: Optional[str] = None,
    max_items: int = 30,
):
    """Scrapes railway/train schedules for Sri Lanka (HTML, filtered)."""
    data = scrape_train_schedule_impl(
        from_station=from_station,
        to_station=to_station,
        keyword=keyword,
        max_items=max_items,
    )
    return json.dumps(data)


@tool
def scrape_cse_stock_data(
    symbol: str,
    period: str = "1mo",
    interval: str = "1d",
):
    """Scrapes CSE/stock market data using yfinance (hybrid API wrapper)."""
    data = scrape_cse_stock_impl(symbol=symbol, period=period, interval=interval)
    return json.dumps(data)


@tool
def scrape_local_news(
    keywords: Optional[List[str]] = None,
    max_articles: int = 30,
):
    """Scrapes local news headlines from Sri Lankan sites, filtered by keywords."""
    data = scrape_local_news_impl(keywords=keywords, max_articles=max_articles)
    return json.dumps(data)


# Map string names to actual functions for the Worker/ToolNode
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
}

