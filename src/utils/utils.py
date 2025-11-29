# src/utils/utils.py
"""
COMPLETE - All scraping tools and utilities for ModelX platform
Updated: Deep scraping for Government Gazette to retrieve full details and download links.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
import os
import logging
import requests
import json
from langchain_core.tools import tool
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin, urlparse
import yfinance as yf
import re
import time

# Optional Playwright import (only used if available / required)
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    PLAYWRIGHT_AVAILABLE = False

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
# UTILITIES
# ============================================

def get_today_str() -> str:
    return datetime.now().strftime("%a %b %d, %Y")


def _safe_get(url: str, timeout: int = DEFAULT_TIMEOUT, headers: Optional[Dict[str,str]] = None) -> Optional[requests.Response]:
    """HTTP GET with retries and basic error handling."""
    headers = headers or DEFAULT_HEADERS
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                return resp
            logger.warning(f"[HTTP] {url} returned {resp.status_code}")
        except requests.exceptions.Timeout:
            logger.warning(f"[HTTP] Timeout on {url} (attempt {attempt + 1}/{MAX_RETRIES})")
        except requests.exceptions.RequestException as e:
            logger.error(f"[HTTP] Error fetching {url}: {e}")
        if attempt < MAX_RETRIES - 1:
            time.sleep(2 ** attempt)
    return None


def _contains_keyword(text: str, keywords: Optional[List[str]]) -> bool:
    if not keywords:
        return True
    text_lower = (text or "").lower()
    return any(k.lower() in text_lower for k in keywords)


def _extract_text_from_html(html: str, selector: str = "body") -> str:
    soup = BeautifulSoup(html, "html.parser")
    element = soup.select_one(selector) or soup.body
    return element.get_text(separator="\n", strip=True) if element else ""


def _make_absolute(href: str, base: str) -> str:
    if not href:
        return base
    if href.startswith("//"):
        parsed = urlparse(base)
        return f"{parsed.scheme}:{href}"
    if href.startswith("/"):
        return urljoin(base, href)
    if href.startswith("http"):
        return href
    return urljoin(base, href)


# ============================================
# PLAYWRIGHT SESSION HELPERS
# ============================================

def ensure_playwright():
    if not PLAYWRIGHT_AVAILABLE:
        raise RuntimeError("Playwright is not installed. Install with `pip install playwright` and run `playwright install`.")


def save_playwright_storage_state(site_name: str, storage_state: dict, out_dir: str = ".sessions") -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{site_name}_storage_state.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(storage_state, f)
    return path


def load_playwright_storage_state_path(site_name: str, out_dir: str = ".sessions") -> Optional[str]:
    path = os.path.join(out_dir, f"{site_name}_storage_state.json")
    return path if os.path.exists(path) else None


def create_or_restore_playwright_session(
    site_name: str,
    login_flow: Optional[dict] = None,
    headless: bool = True,
    storage_dir: str = ".sessions",
    wait_until: str = "networkidle",
) -> str:
    """
    Create or restore a Playwright session for a site. If session file exists, returns its path.
    If not, runs a minimal login flow if provided (login_flow is a dict describing interactions).
    """
    ensure_playwright()
    os.makedirs(storage_dir, exist_ok=True)
    session_path = os.path.join(storage_dir, f"{site_name}_storage_state.json")
    if os.path.exists(session_path):
        logger.info(f"[PLAYWRIGHT] Found existing session for {site_name} at {session_path}")
        return session_path

    if not login_flow:
        raise RuntimeError(f"No existing session for {site_name} and no login_flow provided to create one.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()
        try:
            page.goto(login_flow["login_url"], wait_until=wait_until, timeout=60000)
            # Execute steps
            for step in login_flow.get("steps", []):
                st = step.get("type")
                sel = step.get("selector")
                if st == "fill":
                    value = ""
                    if "value" in step:
                        value = step["value"]
                    elif "value_env" in step:
                        value = os.getenv(step["value_env"], "")
                    page.fill(sel, value, timeout=15000)
                elif st == "click":
                    page.click(sel, timeout=15000)
                elif st == "wait":
                    page.wait_for_selector(step.get("selector"), timeout=step.get("timeout", 15000))
                elif st == "goto":
                    page.goto(step.get("url"), wait_until=wait_until, timeout=60000)
                else:
                    logger.debug(f"[PLAYWRIGHT] Unknown step type: {st}")
            # After manual/automated flow, save storage state
            storage = context.storage_state()
            with open(session_path, "w", encoding="utf-8") as f:
                json.dump(storage, f)
            logger.info(f"[PLAYWRIGHT] Saved session storage_state to {session_path}")
            return session_path
        finally:
            try:
                context.close()
            except Exception:
                pass
            browser.close()


def playwright_fetch_html_using_session(url: str, storage_state_path: str, headless: bool = True, wait_until: str = "networkidle") -> str:
    """
    Uses Playwright + storage_state to visit `url` and return the rendered HTML.
    """
    ensure_playwright()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(storage_state=storage_state_path)
        page = context.new_page()
        try:
            page.goto(url, wait_until=wait_until, timeout=45000)
            # Give time for JS (optional) - short sleep
            time.sleep(1.0)
            html = page.content()
            return html
        except PlaywrightTimeoutError as e:
            logger.error(f"[PLAYWRIGHT] Timeout fetching {url}: {e}")
            return ""
        finally:
            try:
                context.close()
            except Exception:
                pass
            browser.close()


# ============================================
# METEOROLOGICAL TOOLS (existing)
# ============================================

def tool_dmc_alerts() -> Dict[str, Any]:
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
    keywords = [
        "warning", "advisory", "alert", "heavy rain", "strong wind",
        "thunderstorm", "flood", "landslide", "cyclone", "severe"
    ]
    for text in soup.find_all(string=True):
        t = text.strip()
        if not t or len(t) < 20:
            continue
        lower = t.lower()
        if any(k in lower for k in keywords):
            clean = re.sub(r'\s+', ' ', t)
            if clean not in alerts:
                alerts.append(clean)
    if not alerts:
        alerts = ["No active severe weather alerts detected on the DMC site."]
    return {
        "source": url,
        "alerts": alerts[:10],
        "fetched_at": datetime.utcnow().isoformat(),
    }


def tool_weather_nowcast(location: str = "Colombo") -> Dict[str, Any]:
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
    container = (
        soup.find("div", {"id": "k2Container"})
        or soup.find("div", class_="article-content")
        or soup.find("div", class_="itemFullText")
        or soup.body
    )
    text = container.get_text(separator="\n", strip=True) if container else ""
    if not text:
        text = "No forecast text found on the page."
    text = text[:4000]
    return {
        "location": location,
        "forecast": text,
        "source": url,
        "fetched_at": datetime.utcnow().isoformat(),
    }


# ============================================
# NEWS SCRAPING TOOLS (improved)
# ============================================

LOCAL_NEWS_SITES = [
    {
        "url": "https://www.dailymirror.lk/",
        "name": "Daily Mirror",
        "article_selector": "article, .news-block, .article, .card"
    },
    {
        "url": "https://www.ft.lk/",
        "name": "Daily FT",
        "article_selector": "article, .article-list-item, .card"
    },
    {
        "url": "https://www.newsfirst.lk/",
        "name": "News First",
        "article_selector": ".post, article, .news-block"
    },
]


def scrape_local_news_impl(
    keywords: Optional[List[str]] = None,
    max_articles: int = 30,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for site in LOCAL_NEWS_SITES:
        try:
            resp = _safe_get(site["url"])
            if not resp:
                logger.warning(f"[NEWS] Failed to fetch {site['url']}")
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            articles = soup.select(site.get("article_selector", "article"))
            for article in articles:
                title_elem = (
                    article.find("h1")
                    or article.find("h2")
                    or article.find("h3")
                    or article.find(class_=re.compile(r"(title|headline|heading)", re.I))
                )
                title = title_elem.get_text(strip=True) if title_elem else ""
                if not title or len(title) < 8:
                    a = article.find("a", href=True)
                    title = title or (a.get_text(strip=True) if a else "")
                if not title or len(title) < 8:
                    continue
                if not _contains_keyword(title, keywords):
                    continue
                link_elem = article.find("a", href=True)
                href = link_elem["href"] if link_elem else site["url"]
                href = _make_absolute(href, site["url"])
                snippet_elem = article.find("p") or article.find(class_=re.compile(r"(excerpt|summary|description)", re.I))
                snippet = snippet_elem.get_text(strip=True)[:300] if snippet_elem else ""
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
# REDDIT SCRAPING
# ============================================

def scrape_reddit_impl(
    keywords: List[str],
    limit: int = 20,
    subreddit: Optional[str] = None,
) -> List[Dict[str, Any]]:
    base = f"https://www.reddit.com/r/{subreddit}/search.json" if subreddit else "https://www.reddit.com/search.json"
    query = " ".join(keywords) if keywords else "Sri Lanka"
    params = {"q": query, "sort": "new", "limit": str(limit), "restrict_sr": "on" if subreddit else "off"}
    headers = {"User-Agent": DEFAULT_HEADERS["User-Agent"], "Accept": "application/json"}
    try:
        resp = requests.get(base, headers=headers, params=params, timeout=DEFAULT_TIMEOUT)
        if resp.status_code != 200:
            logger.warning(f"[REDDIT] HTTP {resp.status_code} for {base}")
            return [{"error": f"Reddit returned status {resp.status_code}", "query": query}]
        data = resp.json()
        posts_raw = data.get("data", {}).get("children", [])
        posts: List[Dict[str, Any]] = []
        for p in posts_raw:
            d = p.get("data", {})
            title = d.get("title") or ""
            selftext = d.get("selftext") or ""
            text = f"{title}\n{selftext}"
            if not _contains_keyword(text, keywords):
                continue
            posts.append({
                "id": d.get("id"),
                "title": title,
                "selftext": selftext[:500],
                "subreddit": d.get("subreddit"),
                "author": d.get("author"),
                "score": d.get("score", 0),
                "url": "https://www.reddit.com" + d.get("permalink", ""),
                "created_utc": d.get("created_utc"),
                "num_comments": d.get("num_comments", 0),
            })
        return posts if posts else [{"note": f"No Reddit posts found for: {query}", "query": query}]
    except Exception as e:
        logger.error(f"[REDDIT] Error: {e}")
        return [{"error": str(e), "query": query}]


# ============================================
# CSE / STOCK DATA
# ============================================

def scrape_cse_stock_impl(
    symbol: str = "ASPI",
    period: str = "1d",
    interval: str = "1h",
) -> Dict[str, Any]:
    try:
        symbols_to_try = [symbol]
        if symbol.upper() in ("ASPI", "ASPI.N0000"):
            symbols_to_try = ["^N0000", "ASPI.N0000", "ASPI"]
        for sym in symbols_to_try:
            try:
                ticker = yf.Ticker(sym)
                hist = ticker.history(period=period, interval=interval)
                if hist is None or hist.empty:
                    continue
                hist = hist.reset_index()
                records = hist.to_dict(orient="records")
                for record in records:
                    for key, value in list(record.items()):
                        if hasattr(value, "isoformat"):
                            record[key] = value.isoformat()
                latest = records[-1] if records else {}
                summary = {
                    "current_price": latest.get("Close", latest.get("close", 0)),
                    "open": latest.get("Open", latest.get("open", 0)),
                    "high": latest.get("High", latest.get("high", 0)),
                    "low": latest.get("Low", latest.get("low", 0)),
                    "volume": latest.get("Volume", latest.get("volume", 0)),
                }
                return {
                    "symbol": symbol,
                    "resolved_symbol": sym,
                    "period": period,
                    "interval": interval,
                    "summary": summary,
                    "records": records[-10:],
                    "fetched_at": datetime.utcnow().isoformat(),
                }
            except Exception as e_inner:
                logger.debug(f"[CSE] yfinance attempt failed for {sym}: {e_inner}")
                continue
        # Fallback: try a lightweight scrape on CSE website
        cse_url = "https://www.cse.lk/"
        resp = _safe_get(cse_url)
        if resp:
            try:
                soup = BeautifulSoup(resp.text, "html.parser")
                text = soup.get_text(separator="\n", strip=True)
                m = re.search(r"(ASPI|All Share Price Index)[^\d\n\r]*([\d,]+\.\d+)", text, re.I)
                if m:
                    value = m.group(2).replace(",", "")
                    return {
                        "symbol": symbol,
                        "resolved_symbol": "CSE-scan",
                        "period": period,
                        "interval": interval,
                        "summary": {"current_price": float(value)},
                        "records": [],
                        "fetched_at": datetime.utcnow().isoformat(),
                    }
            except Exception:
                pass
        return {"symbol": symbol, "error": f"Could not fetch data for {symbol}. Try correct symbol format (e.g., SYMBOL.N0000).", "attempted_symbols": symbols_to_try}
    except Exception as e:
        logger.error(f"[CSE] Error: {e}")
        return {"symbol": symbol, "error": str(e)}


# ============================================
# GOVERNMENT GAZETTE (Updated for Deep Scraping)
# ============================================

def scrape_government_gazette_impl(
    keywords: Optional[List[str]] = None,
    max_items: int = 15,  # Reduced default max items to avoid long wait times
) -> List[Dict[str, Any]]:
    """
    Scrapes gazette.lk for latest gazettes.
    Goes into each gazette page to retrieve full details and download links.
    """
    base_url = "https://www.gazette.lk/government-gazette"
    results: List[Dict[str, Any]] = []
    
    # 1. Fetch the listing page
    logger.info(f"[GAZETTE] Fetching listing from {base_url}")
    resp = _safe_get(base_url)
    if not resp:
        return [{"title": "Failed to access gazette.lk", "url": base_url, "timestamp": datetime.utcnow().isoformat()}]
    
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # 2. Find articles in the list
    articles = soup.find_all("article")
    if not articles:
        articles = soup.select(".post, .type-post, .entry, .news-block")
        
    for article in articles:
        if len(results) >= max_items:
            break

        # Extract Title & Link from the listing
        title_elem = article.find(class_="entry-title") or article.find("h2") or article.find("h3")
        if not title_elem:
            continue
            
        link_elem = title_elem.find("a", href=True)
        if not link_elem:
            continue
            
        title = link_elem.get_text(strip=True)
        post_url = link_elem["href"]
        post_url_abs = _make_absolute(post_url, base_url)
        
        # Keyword filtering on title
        if not _contains_keyword(title, keywords):
            continue
        
        # 3. Deep Scrape: Visit the individual gazette page
        logger.info(f"[GAZETTE] Deep scraping: {title[:30]}...")
        # Add a small delay to be polite
        time.sleep(0.5) 
        
        detail_resp = _safe_get(post_url_abs)
        if not detail_resp:
            # If fail, just add what we have
            results.append({
                "title": title,
                "url": post_url_abs,
                "note": "Could not fetch details",
                "timestamp": datetime.utcnow().isoformat()
            })
            continue

        # 4. Parse Inner Content
        detail_soup = BeautifulSoup(detail_resp.text, "html.parser")
        
        # Extract Content Text
        content_div = detail_soup.find(class_="entry-content") or detail_soup.find("article")
        content_text = content_div.get_text(separator="\n", strip=True) if content_div else ""
        
        # Extract Download Links (PDFs)
        # Look for links that end in .pdf OR contain "download" text classes
        download_links = []
        all_links = content_div.find_all("a", href=True) if content_div else []
        
        for a in all_links:
            href = a["href"]
            text = a.get_text(strip=True).lower()
            
            # Heuristic for download links
            is_pdf = href.lower().endswith(".pdf")
            is_download_text = any(x in text for x in ["download", "sinhala", "tamil", "english", "gazette"])
            
            # We want to capture language specific links usually found on these pages
            if is_pdf or is_download_text:
                download_links.append({
                    "text": a.get_text(strip=True),
                    "url": href
                })

        # 5. Compile Result
        results.append({
            "title": title,
            "url": post_url_abs,
            "description": content_text[:1000] + "..." if len(content_text) > 1000 else content_text,
            "downloads": download_links,
            "timestamp": datetime.utcnow().isoformat(),
        })
            
    if not results:
        return [{
            "title": "No gazette entries found matching criteria",
            "url": base_url,
            "keywords": keywords,
            "timestamp": datetime.utcnow().isoformat(),
        }]
        
    return results


# ============================================
# PARLIAMENT MINUTES (improved)
# ============================================

def scrape_parliament_minutes_impl(
    keywords: Optional[List[str]] = None,
    max_items: int = 20,
) -> List[Dict[str, Any]]:
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
    # Collect likely hansard / minutes links
    links = soup.find_all("a", href=True)
    results: List[Dict[str, Any]] = []
    for a in links:
        title = a.get_text(strip=True)
        href = a["href"]
        if not title or len(title) < 6:
            continue
        if not _contains_keyword(title, keywords):
            # also inspect href tokens
            if keywords:
                if not any(k.lower() in href.lower() for k in keywords):
                    continue
            else:
                # no keywords provided, accept things with hansard/minutes or debate
                if not re.search(r"(hansard|minutes|debate|transcript)", title + href, re.I):
                    continue
        href_abs = _make_absolute(href, url)
        results.append({
            "title": title,
            "url": href_abs,
            "timestamp": datetime.utcnow().isoformat(),
        })
        if len(results) >= max_items:
            break
    if not results:
        return [{
            "title": "No parliament minutes found",
            "url": url,
            "keywords": keywords,
            "timestamp": datetime.utcnow().isoformat(),
        }]
    return results


# ============================================
# TRAIN SCHEDULE (improved)
# ============================================

def scrape_train_schedule_impl(
    from_station: Optional[str] = None,
    to_station: Optional[str] = None,
    keyword: Optional[str] = None,
    max_items: int = 30,
) -> List[Dict[str, Any]]:
    url = "https://eservices.railway.gov.lk/schedule/homeAction.action?lang=en"
    resp = _safe_get(url)
    if not resp:
        return [{
            "train": "Railway website unavailable",
            "note": "Could not access railway.gov.lk",
            "timestamp": datetime.utcnow().isoformat(),
        }]
    soup = BeautifulSoup(resp.text, "html.parser")
    tables = soup.find_all("table")
    results: List[Dict[str, Any]] = []
    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:]:
            cols = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cols) < 2:
                continue
            train_info = {
                "train": cols[0] if len(cols) > 0 else "",
                "departure": cols[1] if len(cols) > 1 else "",
                "arrival": cols[2] if len(cols) > 2 else "",
                "route": " → ".join(cols[3:]) if len(cols) > 3 else "",
            }
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
    if not results:
        return [{
            "train": "No train schedules found",
            "note": "Railway schedule unavailable or no matches",
            "timestamp": datetime.utcnow().isoformat(),
        }]
    return results


# ============================================
# TWITTER TRENDING (Playwright primary, Nitter fallback)
# ============================================

def _scrape_twitter_trending_with_playwright(storage_state_path: Optional[str] = None, headless: bool = True) -> List[Dict[str, Any]]:
    ensure_playwright()
    trending = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context_args = {}
        if storage_state_path:
            context_args["storage_state"] = storage_state_path
        context = browser.new_context(**context_args)
        page = context.new_page()
        try:
            # Visit Twitter Explore/Trending tab (may require login)
            page.goto("https://twitter.com/i/trends", wait_until="networkidle", timeout=30000)
            # fallback to /explore/tabs/trending
            if "login" in page.url or page.content().strip() == "":
                page.goto("https://twitter.com/explore/tabs/trending", wait_until="networkidle", timeout=30000)
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            # Trend items may be in aria roles or headings -- collect common patterns
            items = soup.select("div[role='article'] a, div[data-testid='trend'], div.trend-card, span.trend-name")
            seen = set()
            for it in items:
                text = it.get_text(separator=" ", strip=True)
                href = it.get("href") or ""
                if not text or len(text) < 2:
                    continue
                if text in seen:
                    continue
                seen.add(text)
                trending.append({"trend": text, "url": _make_absolute(href, "https://twitter.com") if href else None})
            # final fallback: extract hashtags / strong texts
            if not trending:
                for tag in soup.find_all(string=re.compile(r"#\w+")):
                    t = tag.strip()
                    if t not in seen:
                        trending.append({"trend": t, "url": None})
                        seen.add(t)
            return trending
        except Exception as e:
            logger.error(f"[TWITTER] Playwright trending error: {e}")
            return []
        finally:
            try:
                context.close()
            except Exception:
                pass
            browser.close()


def _scrape_twitter_trending_with_nitter(instance: str = "https://nitter.net") -> List[Dict[str, Any]]:
    """Best-effort: try to fetch trending posts / search 'Sri Lanka trends' from a Nitter instance."""
    trends = []
    try:
        search_url = f"{instance}/search?f=tweets&q=Sri%20Lanka%20trend"
        resp = _safe_get(search_url)
        if not resp:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.select("a:not([href^='/pic/'])"):
            text = a.get_text(separator=" ", strip=True)
            href = a.get("href", "")
            if not text:
                continue
            if len(text) < 3:
                continue
            trends.append({"trend": text, "url": _make_absolute(href, instance)})
        return trends[:20]
    except Exception as e:
        logger.debug(f"[TWITTER] Nitter fallback failed: {e}")
        return []


def scrape_twitter_trending_srilanka(use_playwright: bool = True, storage_state_site: Optional[str] = None) -> Dict[str, Any]:
    """
    Return trending topics for Sri Lanka. Best-effort:
      1) If Playwright available and use_playwright, try Playwright (optionally with storage_state file).
      2) Fallback to Nitter instance scrape.
    """
    # Try Playwright
    if use_playwright and PLAYWRIGHT_AVAILABLE:
        storage_state = None
        if storage_state_site:
            storage_state = load_playwright_storage_state_path(storage_state_site)
        try:
            trends = _scrape_twitter_trending_with_playwright(storage_state_path=storage_state)
            if trends:
                return {"source": "twitter_playwright", "trends": trends, "fetched_at": datetime.utcnow().isoformat()}
        except Exception as e:
            logger.debug(f"[TWITTER] Playwright attempt failed: {e}")

    # Nitter fallback
    nitter_instances = ["https://nitter.net", "https://nitter.snopyta.org", "https://nitter.1d4.us"]
    for inst in nitter_instances:
        try:
            trends = _scrape_twitter_trending_with_nitter(inst)
            if trends:
                return {"source": inst, "trends": trends, "fetched_at": datetime.utcnow().isoformat()}
        except Exception:
            continue

    return {"source": "none", "trends": [], "note": "Could not fetch Twitter trends. Try supplying Playwright session or check network."}


# ============================================
# AUTHENTICATED SCRAPERS (LinkedIn / Instagram / Facebook)
# Use Playwright and storage_state files to persist sessions.
# ============================================

def scrape_authenticated_page_via_playwright(
    site_name: str,
    url: str,
    login_flow: Optional[dict] = None,
    headless: bool = True,
    storage_dir: str = ".sessions",
    wait_until: str = "networkidle"
) -> Dict[str, Any]:
    """
    Unified helper: create/restore Playwright session and fetch fully-rendered HTML.
    Returns: {"html": ..., "source": url, "storage_state": path}
    """
    if not PLAYWRIGHT_AVAILABLE:
        return {"error": "Playwright not available. Install playwright to use authenticated scrapers."}
    session_path = load_playwright_storage_state_path(site_name, storage_dir)
    if not session_path:
        if not login_flow:
            return {"error": f"No existing session found for {site_name} and no login_flow provided to create one."}
        # create session
        try:
            session_path = create_or_restore_playwright_session(site_name, login_flow=login_flow, headless=headless, storage_dir=storage_dir, wait_until=wait_until)
        except Exception as e:
            return {"error": f"Failed to create Playwright session: {e}"}
    # Fetch page using saved session
    html = playwright_fetch_html_using_session(url, session_path, headless=headless, wait_until=wait_until)
    if not html:
        return {"error": "Failed to fetch page via Playwright session.", "storage_state": session_path}
    return {"html": html, "source": url, "storage_state": session_path}


def _simple_parse_posts_from_html(html: str, base_url: str, max_items: int = 10) -> List[Dict[str, Any]]:
    """A generic helper that attempts to extract posts/headlines from rendered HTML."""
    soup = BeautifulSoup(html, "html.parser")
    items: List[Dict[str, Any]] = []
    # Common patterns: article, div.post, li.feed, div.feed-item
    candidates = soup.select("article, div.post, div.feed-item, li.stream-item, div._4ikz")
    if not candidates:
        candidates = soup.find_all(["article", "div"], limit=200)
    seen = set()
    for c in candidates:
        title_tag = (c.find("h1") or c.find("h2") or c.find("h3") or c.find("a"))
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        if not title or title in seen or len(title) < 4:
            continue
        seen.add(title)
        a = c.find("a", href=True)
        url = _make_absolute(a["href"], base_url) if a else base_url
        text = c.get_text(separator=" ", strip=True)[:500]
        items.append({"title": title, "snippet": text, "url": url})
        if len(items) >= max_items:
            break
    return items


# ============================================
# LANGCHAIN TOOL WRAPPERS (updated)
# ============================================

@tool
def scrape_linkedin(keywords: Optional[List[str]] = None, max_items: int = 10):
    """
    LinkedIn search using Playwright session.
    Requires environment variables: LINKEDIN_USER, LINKEDIN_PASSWORD (if creating session).
    You must create a login_flow dict to automate login if no session file exists.
    """
    site = "linkedin"
    login_flow = {
        "login_url": "https://www.linkedin.com/login",
        "steps": [
            {"type": "fill", "selector": 'input[name="session_key"]', "value_env": "LINKEDIN_USER"},
            {"type": "fill", "selector": 'input[name="session_password"]', "value_env": "LINKEDIN_PASSWORD"},
            {"type": "click", "selector": 'button[type="submit"]'},
            {"type": "wait", "selector": 'nav', "timeout": 20000}
        ]
    }
    # Use LinkedIn search URL for keyword(s)
    query = "+".join(keywords) if keywords else "Sri+Lanka"
    url = f"https://www.linkedin.com/search/results/all/?keywords={quote_plus(query)}"
    try:
        r = scrape_authenticated_page_via_playwright(site, url, login_flow=login_flow)
        if "html" in r:
            items = _simple_parse_posts_from_html(r["html"], "https://www.linkedin.com", max_items=max_items)
            return json.dumps({"site": "LinkedIn", "results": items, "storage_state": r.get("storage_state")}, default=str)
        return json.dumps(r, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def scrape_instagram(keywords: Optional[List[str]] = None, max_items: int = 10):
    """
    Instagram scraping via Playwright session. Use IG credentials in env if session needs creating:
    INSTAGRAM_USER, INSTAGRAM_PASSWORD.
    """
    site = "instagram"
    login_flow = {
        "login_url": "https://www.instagram.com/accounts/login/",
        "steps": [
            {"type": "wait", "selector": 'input[name="username"]', "timeout": 20000},
            {"type": "fill", "selector": 'input[name="username"]', "value_env": "INSTAGRAM_USER"},
            {"type": "fill", "selector": 'input[name="password"]', "value_env": "INSTAGRAM_PASSWORD"},
            {"type": "click", "selector": 'button[type="submit"]'},
            {"type": "wait", "selector": 'nav', "timeout": 20000}
        ]
    }
    q = keywords[0] if keywords else "srilanka"
    url = f"https://www.instagram.com/explore/tags/{quote_plus(q)}/"
    try:
        r = scrape_authenticated_page_via_playwright(site, url, login_flow=login_flow)
        if "html" in r:
            items = _simple_parse_posts_from_html(r["html"], "https://www.instagram.com", max_items=max_items)
            return json.dumps({"site": "Instagram", "results": items, "storage_state": r.get("storage_state")}, default=str)
        return json.dumps(r, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def scrape_facebook(keywords: Optional[List[str]] = None, max_items: int = 10):
    """
    Facebook scraping via Playwright session. Use FB credentials in env if creating a session:
    FACEBOOK_USER, FACEBOOK_PASSWORD.
    """
    site = "facebook"
    login_flow = {
        "login_url": "https://www.facebook.com/login",
        "steps": [
            {"type": "fill", "selector": 'input[name="email"]', "value_env": "FACEBOOK_USER"},
            {"type": "fill", "selector": 'input[name="pass"]', "value_env": "FACEBOOK_PASSWORD"},
            {"type": "click", "selector": 'button[name="login"]'},
            {"type": "wait", "selector": 'div[role="navigation"]', "timeout": 20000}
        ]
    }
    q = "+".join(keywords) if keywords else "Sri Lanka"
    url = f"https://www.facebook.com/search/top/?q={quote_plus(q)}"
    try:
        r = scrape_authenticated_page_via_playwright(site, url, login_flow=login_flow)
        if "html" in r:
            items = _simple_parse_posts_from_html(r["html"], "https://www.facebook.com", max_items=max_items)
            return json.dumps({"site": "Facebook", "results": items, "storage_state": r.get("storage_state")}, default=str)
        return json.dumps(r, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def scrape_reddit(
    keywords: List[str],
    limit: int = 20,
    subreddit: Optional[str] = None,
):
    """
    Scrape Reddit for posts matching specific keywords.
    Optionally restrict to a specific subreddit.
    """
    data = scrape_reddit_impl(keywords=keywords, limit=limit, subreddit=subreddit)
    return json.dumps(data, default=str)


@tool
def scrape_twitter(query: str = "Sri Lanka", use_playwright: bool = True, storage_state_site: Optional[str] = None):
    """
    Twitter trending/search wrapper. For trending, call scrape_twitter_trending_srilanka().
    For search, this will attempt Playwright fetch if available, else Nitter fallback.
    """
    try:
        # If query == 'trending' treat specially
        if query.strip().lower() in ("trending", "trends", "trending srilanka", "trending sri lanka"):
            return json.dumps(scrape_twitter_trending_srilanka(use_playwright=use_playwright, storage_state_site=storage_state_site), default=str)
        # Otherwise perform search (playwright primary)
        if use_playwright and PLAYWRIGHT_AVAILABLE:
            storage_state = None
            if storage_state_site:
                storage_state = load_playwright_storage_state_path(storage_state_site)
            search_url = f"https://twitter.com/search?q={quote_plus(query)}&src=typed_query"
            try:
                html = playwright_fetch_html_using_session(search_url, storage_state or "", headless=True)
                if html:
                    items = _simple_parse_posts_from_html(html, "https://twitter.com", max_items=20)
                    return json.dumps({"source": "twitter_playwright", "results": items}, default=str)
            except Exception as e:
                logger.debug(f"[TWITTER] Playwright search failed: {e}")
        # Nitter fallback
        nitter = "https://nitter.net"
        search_url = f"{nitter}/search?f=tweets&q={quote_plus(query)}"
        resp = _safe_get(search_url)
        if not resp:
            return json.dumps({"error": "Could not fetch Twitter via Playwright or Nitter fallback"})
        soup = BeautifulSoup(resp.text, "html.parser")
        items = []
        for a in soup.select("div.timeline-item"):
            t = a.get_text(separator=" ", strip=True)
            link = a.find("a", href=True)
            href = _make_absolute(link["href"], nitter) if link else None
            items.append({"text": t[:400], "url": href})
        return json.dumps({"source": "nitter", "results": items[:20]}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def scrape_government_gazette(
    keywords: Optional[List[str]] = None,
    max_items: int = 15,
):
    """
    Search and scrape Sri Lankan government gazette entries from gazette.lk.
    This tool visits each gazette page to extract full descriptions and download links (PDFs).
    """
    data = scrape_government_gazette_impl(keywords=keywords, max_items=max_items)
    return json.dumps(data, default=str)


@tool
def scrape_parliament_minutes(
    keywords: Optional[List[str]] = None,
    max_items: int = 20,
):
    """
    Search and scrape Sri Lankan Parliament Hansards and minutes matching keywords.
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
    Scrape Sri Lanka Railways train schedule based on stations or keywords.
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
    Scrape Colombo Stock Exchange (CSE) data for a given symbol (e.g., ASPI).
    Tries yfinance first, then falls back to direct site scraping.
    """
    data = scrape_cse_stock_impl(symbol=symbol, period=period, interval=interval)
    return json.dumps(data, default=str)


@tool
def scrape_local_news(
    keywords: Optional[List[str]] = None,
    max_articles: int = 30,
):
    """
    Scrape major Sri Lankan local news websites (Daily Mirror, Daily FT, etc.) for articles matching keywords.
    """
    data = scrape_local_news_impl(keywords=keywords, max_articles=max_articles)
    return json.dumps(data, default=str)


@tool
def think_tool(reflection: str) -> str:
    """
    Log a thought or reflection from the agent. Useful for debugging or tracing the agent's reasoning.
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

ALL_TOOLS = list(TOOL_MAPPING.values())


# ============================================
# EXPORTS
# ============================================

__all__ = [
    "get_today_str",
    "tool_dmc_alerts",
    "tool_weather_nowcast",
    "TOOL_MAPPING",
    "ALL_TOOLS",
    # keep other functions importable if desired
    "create_or_restore_playwright_session",
    "playwright_fetch_html_using_session",
]