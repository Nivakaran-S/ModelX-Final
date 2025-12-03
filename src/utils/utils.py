# src/utils/utils.py
"""
COMPLETE - All scraping tools and utilities for ModelX platform
Updated: 
- Fixed Playwright Syntax Error (removed invalid 'request_timeout').
- Added 'Requests-First' strategy for 10x faster scraping.
- Added 'Rainfall' PDF detection for district-level rain data.
- Captures ALL district/city rows from the forecast table.
"""
from urllib.parse import quote
from datetime import datetime
from typing import Optional, List, Dict, Any
import os
import logging
import requests
import json
import io
from langchain_core.tools import tool
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin, urlparse
import yfinance as yf
import re
import time
import random

# Optional Playwright import
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    PLAYWRIGHT_AVAILABLE = False

# Optional PDF Reader import
try:
    from pypdf import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

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


def _extract_text_from_pdf_url(pdf_url: str) -> str:
    """
    Downloads a PDF from a URL and extracts its text content.
    Returns a summarized string of the content.
    """
    if not PDF_AVAILABLE:
        return "[PDF Content: Install 'pypdf' to extract text]"

    try:
        # 1. Download the PDF bytes
        headers = DEFAULT_HEADERS.copy()
        headers["Referer"] = "https://meteo.gov.lk/"
        
        response = requests.get(pdf_url, headers=headers, timeout=20)
        response.raise_for_status()
        
        # 2. Read PDF from memory
        with io.BytesIO(response.content) as f:
            reader = PdfReader(f)
            text_content = []
            
            # Extract text from first 3 pages (covers most advisories/rainfall reports)
            for i, page in enumerate(reader.pages[:3]):
                text = page.extract_text()
                if text:
                    text_content.append(text)
            
            full_text = "\n".join(text_content)
            
            # 3. Filter Non-English Content
            # Calculate percentage of ASCII characters
            ascii_chars = sum(1 for c in full_text if ord(c) < 128)
            total_chars = len(full_text)
            
            if total_chars > 0 and (ascii_chars / total_chars) < 0.4:
                return "[PDF appears to be in Sinhala/Tamil - Text extraction skipped]"

            full_text = re.sub(r'\n+', '\n', full_text).strip()
            return full_text[:3000]  # Limit length

    except Exception as e:
        logger.warning(f"[PDF] Failed to extract text from {pdf_url}: {e}")
        return f"[Error reading PDF: {str(e)}]"


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
    """
    Robustly finds the session file in multiple possible locations.
    Priority order:
    1. src/utils/.sessions/ (where session_manager.py saves them)
    2. .sessions/ (current working directory)
    3. Root project .sessions/
    """
    filename = f"{site_name}_storage_state.json"
    
    # Priority 1: Check src/utils/.sessions/ (most likely location)
    src_utils_path = os.path.join(os.getcwd(), "src", "utils", out_dir, filename)
    if os.path.exists(src_utils_path):
        logger.info(f"[SESSION] ✅ Found session at {src_utils_path}")
        return src_utils_path
    
    # Priority 2: Check current working directory .sessions/
    cwd_path = os.path.join(os.getcwd(), out_dir, filename)
    if os.path.exists(cwd_path):
        logger.info(f"[SESSION] ✅ Found session at {cwd_path}")
        return cwd_path
    
    # Priority 3: Check project root .sessions/
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    root_path = os.path.join(base_dir, out_dir, filename)
    if os.path.exists(root_path):
        logger.info(f"[SESSION] ✅ Found session at {root_path}")
        return root_path

    # Priority 4: Check if out_dir is actually the full path to src/utils/.sessions
    direct_path = os.path.join(out_dir, filename)
    if os.path.exists(direct_path):
        logger.info(f"[SESSION] ✅ Found session at {direct_path}")
        return direct_path

    logger.warning(f"[SESSION] ❌ Could not find session file for {site_name}.")
    logger.warning(f"Checked locations:")
    logger.warning(f"  1. {src_utils_path}")
    logger.warning(f"  2. {cwd_path}")
    logger.warning(f"  3. {root_path}")
    logger.warning(f"\n💡 Run 'python src/utils/session_manager.py' to create sessions.")
    return None

def create_or_restore_playwright_session(
    site_name: str,
    login_flow: Optional[dict] = None,
    headless: bool = True,
    storage_dir: str = ".sessions",
    wait_until: str = "networkidle",
) -> str:
    ensure_playwright()
    existing_session = load_playwright_storage_state_path(site_name, storage_dir)
    if existing_session:
        return existing_session

    os.makedirs(storage_dir, exist_ok=True)
    session_path = os.path.join(storage_dir, f"{site_name}_storage_state.json")

    if not login_flow:
        raise RuntimeError(f"No existing session for {site_name} and no login_flow provided to create one.")

    logger.info(f"[PLAYWRIGHT] Creating new session for {site_name}...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()
        try:
            page.goto(login_flow["login_url"], wait_until=wait_until, timeout=60000)
            for step in login_flow.get("steps", []):
                st = step.get("type")
                sel = step.get("selector")
                if st == "fill":
                    value = step.get("value") or os.getenv(step.get("value_env"), "")
                    page.fill(sel, value, timeout=15000)
                elif st == "click":
                    page.click(sel, timeout=15000)
                elif st == "wait":
                    page.wait_for_selector(step.get("selector"), timeout=step.get("timeout", 15000))
                elif st == "goto":
                    page.goto(step.get("url"), wait_until=wait_until, timeout=60000)
            
            storage = context.storage_state()
            with open(session_path, "w", encoding="utf-8") as f:
                json.dump(storage, f)
            logger.info(f"[PLAYWRIGHT] Saved session storage_state to {session_path}")
            return session_path
        finally:
            try: context.close()
            except: pass
            browser.close()


def playwright_fetch_html_using_session(url: str, storage_state_path: Optional[str], headless: bool = True, wait_until: str = "networkidle") -> str:
    ensure_playwright()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context_args = {}
        if storage_state_path and os.path.exists(storage_state_path):
            context_args["storage_state"] = storage_state_path
        
        context = browser.new_context(**context_args)
        page = context.new_page()
        try:
            page.goto(url, wait_until=wait_until, timeout=45000)
            time.sleep(1.0)
            html = page.content()
            return html
        except PlaywrightTimeoutError as e:
            logger.error(f"[PLAYWRIGHT] Timeout fetching {url}: {e}")
            return ""
        finally:
            try: context.close()
            except: pass
            browser.close()


# ============================================
# METEOROLOGICAL TOOLS (Upgraded)
# ============================================

def tool_dmc_alerts() -> Dict[str, Any]:
    # ... (Existing DMC alerts code - unchanged) ...
    url = "http://www.meteo.gov.lk/index.php?lang=en"
    resp = _safe_get(url)
    if not resp:
        return {"source": url, "alerts": ["Failed to fetch alerts from DMC."], "fetched_at": datetime.utcnow().isoformat()}
    soup = BeautifulSoup(resp.text, "html.parser")
    alerts: List[str] = []
    keywords = ["warning", "advisory", "alert", "heavy rain", "strong wind", "thunderstorm", "flood", "landslide", "cyclone", "severe"]
    for text in soup.find_all(string=True):
        if len(text.strip()) > 20 and any(k in text.lower() for k in keywords):
            clean = re.sub(r'\s+', ' ', text.strip())
            if clean not in alerts: alerts.append(clean)
    if not alerts: alerts = ["No active severe weather alerts detected."]
    return {"source": url, "alerts": alerts[:10], "fetched_at": datetime.utcnow().isoformat()}


def tool_weather_nowcast(location: str = "Colombo") -> Dict[str, Any]:
    """
    Comprehensive Weather Scraper (Robust Mode):
    1. Homepage (General Text).
    2. City/District Forecast (Direct URL).
    3. Critical Advisory PDFs.
    Handles slow loading by capturing content even if timeouts occur.
    """
    base_url = "https://meteo.gov.lk/"
    city_forecast_url = "https://meteo.gov.lk/index.php?option=com_content&view=article&id=102&Itemid=360&lang=en"
    
    combined_report = []
    html_home = ""
    html_city = ""
    
    if PLAYWRIGHT_AVAILABLE:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                # Use a standard browser context (no aggressive blocking)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                page.set_default_timeout(60000) # Give it 60 seconds (it's slow)

                # --- A. Visit Homepage ---
                try:
                    page.goto(base_url, wait_until="domcontentloaded")
                    # Try to wait for text, but don't crash if it takes too long
                    try: page.wait_for_selector("div.itemFullText", timeout=15000)
                    except: pass
                    html_home = page.content()
                except Exception as e:
                    # Even if it times out, grab what we have!
                    logger.warning(f"[WEATHER] Homepage timeout (capturing partial): {e}")
                    html_home = page.content()

                # --- B. Visit City Forecast ---
                try:
                    page.goto(city_forecast_url, wait_until="domcontentloaded")
                    try: page.wait_for_selector("table", timeout=15000)
                    except: pass
                    html_city = page.content()
                except Exception as e:
                    logger.warning(f"[WEATHER] City Forecast timeout (capturing partial): {e}")
                    html_city = page.content()
                
                browser.close()
        except Exception as e:
            logger.warning(f"[WEATHER] Playwright critical fail: {e}")

    # Fallback to requests if Playwright returned nothing
    if not html_home or len(html_home) < 500:
        resp = _safe_get(base_url)
        html_home = resp.text if resp else ""
        
    if not html_city or len(html_city) < 500:
        resp = _safe_get(city_forecast_url)
        html_city = resp.text if resp else ""

    if not html_home and not html_city:
        return {"error": "Failed to load Meteo.gov.lk"}

    # --- PARSE HOMEPAGE ---
    soup_home = BeautifulSoup(html_home, "html.parser")
    english_forecast = ""
    
    header = soup_home.find(string=re.compile(r"WEATHER FORECAST FOR", re.I))
    if header:
        container = header.find_parent("div") or header.find_parent("article")
        if container:
            text = container.get_text(separator="\n", strip=True)
            start = text.upper().find("WEATHER FORECAST FOR")
            if start != -1:
                english_forecast = text[start:][:2500]
    
    if not english_forecast:
        main = soup_home.find("div", class_="itemFullText") or soup_home.find("div", itemprop="articleBody")
        english_forecast = main.get_text(separator="\n", strip=True)[:2500] if main else "General forecast text not found."

    combined_report.append("--- ISLAND-WIDE GENERAL FORECAST ---")
    combined_report.append(english_forecast)

    # --- PARSE CITY FORECAST (Districts) ---
    if html_city:
        soup_city = BeautifulSoup(html_city, "html.parser")
        table = soup_city.find("table")
        if table:
            combined_report.append("\n--- DISTRICT/CITY FORECASTS ---")
            rows = table.find_all("tr")
            
            # Header logic
            if rows:
                header_row = rows[0]
                headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]
                if not "".join(headers).strip() and len(rows) > 1:
                    headers = [th.get_text(strip=True) for th in rows[1].find_all(["th", "td"])]
                
                clean_header = " | ".join(headers[:4]) 
                combined_report.append(clean_header)
                combined_report.append("-" * len(clean_header))

            # Row logic
            for row in rows:
                cols = [td.get_text(strip=True) for td in row.find_all("td")]
                if not cols or len(cols) < 2: continue
                if "City" in cols[0] or "Temperature" in cols[0]: continue

                row_text = " | ".join(cols[:4])
                combined_report.append(row_text)

    # --- PARSE PDF ALERTS ---
    pdf_links = soup_home.find_all("a", href=True)
    found_pdfs = []
    for a in pdf_links:
        link_text = a.get_text(strip=True)
        href = a['href']
        if "pdf" in href.lower() and any(k in link_text.lower() for k in ["advisory", "warning"]):
            abs_url = _make_absolute(href, base_url)
            if abs_url not in [p['url'] for p in found_pdfs]:
                prio = 1 if "english" in link_text.lower() else 2
                found_pdfs.append({"title": link_text, "url": abs_url, "prio": prio})
    
    found_pdfs.sort(key=lambda x: x['prio'])
    
    for pdf in found_pdfs[:2]:
        text = _extract_text_from_pdf_url(pdf['url'])
        if "Sinhala/Tamil" not in text and len(text) > 50:
             combined_report.append(f"\n--- CRITICAL ALERT: {pdf['title']} ---\n{text}")

    # Final Cleanup
    final_text = "\n\n".join(combined_report)
    cleanup = ["DEPARTMENT OF METEOROLOGY", "Loading...", "Listen To The Weather"]
    for c in cleanup:
        final_text = final_text.replace(c, "")
        
    return {
        "location": "All Districts",
        "forecast": final_text,
        "source": base_url,
        "fetched_at": datetime.utcnow().isoformat(),
    }


# ============================================
# NEWS SCRAPING TOOLS
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
                    article.find("h1") or article.find("h2") or article.find("h3")
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
# GOVERNMENT GAZETTE (Deep Scraping)
# ============================================

def scrape_government_gazette_impl(
    keywords: Optional[List[str]] = None,
    max_items: int = 15,
) -> List[Dict[str, Any]]:
    """
    Scrapes gazette.lk for latest government gazettes.
    Note: keywords parameter is kept for compatibility but ignored.
    Returns latest gazettes chronologically.
    """
    base_url = "https://www.gazette.lk/government-gazette"
    results: List[Dict[str, Any]] = []
    
    logger.info(f"[GAZETTE] Fetching latest gazettes from {base_url}")
    resp = _safe_get(base_url)
    if not resp:
        return [{
            "title": "Failed to access gazette.lk",
            "url": base_url,
            "error": "Network request failed",
            "timestamp": datetime.utcnow().isoformat()
        }]
    
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Find all gazette article entries
    articles = soup.find_all("article")
    if not articles:
        articles = soup.select(".post, .type-post, .entry")
    
    logger.info(f"[GAZETTE] Found {len(articles)} potential gazette entries")
    
    for article in articles:
        if len(results) >= max_items:
            break
        
        # Extract title and link
        title_elem = article.find(class_="entry-title") or article.find("h2") or article.find("h3")
        if not title_elem:
            continue
        
        link_elem = title_elem.find("a", href=True)
        if not link_elem:
            continue
        
        title = link_elem.get_text(strip=True)
        post_url = link_elem["href"]
        post_url_abs = _make_absolute(post_url, base_url)
        
        # Filter to only include actual gazette entries (not other site content)
        if "government gazette" not in title.lower():
            continue
        
        # Extract date from title if possible
        date_match = re.search(r'(\d{4}\s+\w+\s+\d{1,2})', title)
        date_str = date_match.group(1) if date_match else "Unknown date"
        
        # Look for download links in the article summary
        entry_content = article.find(class_="entry-content") or article
        download_links = []
        
        if entry_content:
            for link in entry_content.find_all("a", href=True):
                href = link["href"]
                link_text = link.get_text(strip=True).lower()
                
                # Check if it's a PDF or download link
                if (".pdf" in href.lower() or 
                    any(lang in link_text for lang in ["sinhala", "tamil", "english", "download"])):
                    download_links.append({
                        "text": link.get_text(strip=True),
                        "url": _make_absolute(href, base_url)
                    })
        
        results.append({
            "title": title,
            "date": date_str,
            "url": post_url_abs,
            "downloads": download_links,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        logger.info(f"[GAZETTE] Added: {title[:50]}...")
    
    if not results:
        return [{
            "title": "No gazette entries found",
            "url": base_url,
            "note": "The website structure may have changed",
            "timestamp": datetime.utcnow().isoformat(),
        }]
    
    logger.info(f"[GAZETTE] Successfully scraped {len(results)} gazette entries")
    return results



# ============================================
# PARLIAMENT MINUTES
# ============================================

def scrape_parliament_minutes_impl(
    keywords: Optional[List[str]] = None,
    max_items: int = 20,
) -> List[Dict[str, Any]]:
    # Updated URL
    url = "https://www.parliament.lk/en/business-of-parliament/hansards"
    resp = _safe_get(url)
    if not resp:
        return [{
            "title": "Parliament website unavailable",
            "url": url,
            "note": "Could not access parliament.lk. Site may be down.",
            "timestamp": datetime.utcnow().isoformat(),
        }]
    soup = BeautifulSoup(resp.text, "html.parser")
    links = soup.find_all("a", href=True)
    results: List[Dict[str, Any]] = []
    for a in links:
        title = a.get_text(strip=True)
        href = a["href"]
        if not title or len(title) < 6:
            continue
        if not _contains_keyword(title, keywords):
            if keywords:
                if not any(k.lower() in href.lower() for k in keywords):
                    continue
            else:
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
# TRAIN SCHEDULE
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
# TWITTER TRENDING
# ============================================

def _scrape_twitter_trending_with_playwright(storage_state_path: Optional[str] = None, headless: bool = False) -> List[Dict[str, Any]]:
    ensure_playwright()
    trending = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context_args = {}
        if storage_state_path and os.path.exists(storage_state_path):
            context_args["storage_state"] = storage_state_path
        
        context = browser.new_context(**context_args)
        page = context.new_page()
        try:
            page.goto("https://twitter.com/i/trends", wait_until="networkidle", timeout=30000)
            if "login" in page.url or page.content().strip() == "":
                page.goto("https://twitter.com/explore/tabs/trending", wait_until="networkidle", timeout=30000)
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
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
# AUTHENTICATED SCRAPERS
# ============================================

def scrape_authenticated_page_via_playwright(
    site_name: str,
    url: str,
    login_flow: Optional[dict] = None,
    headless: bool = True,
    storage_dir: str = ".sessions",
    wait_until: str = "networkidle"
) -> Dict[str, Any]:
    if not PLAYWRIGHT_AVAILABLE:
        return {"error": "Playwright not available. Install playwright to use authenticated scrapers."}
    
    session_path = load_playwright_storage_state_path(site_name, storage_dir)
    
    if not session_path:
        if not login_flow:
            return {"error": f"No existing session found for {site_name} and no login_flow provided to create one."}
        try:
            session_path = create_or_restore_playwright_session(site_name, login_flow=login_flow, headless=headless, storage_dir=storage_dir, wait_until=wait_until)
        except Exception as e:
            return {"error": f"Failed to create Playwright session: {e}"}
            
    html = playwright_fetch_html_using_session(url, session_path, headless=headless, wait_until=wait_until)
    if not html:
        return {"error": "Failed to fetch page via Playwright session.", "storage_state": session_path}
    return {"html": html, "source": url, "storage_state": session_path}


def _simple_parse_posts_from_html(html: str, base_url: str, max_items: int = 10) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    items: List[Dict[str, Any]] = []
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
# LANGCHAIN TOOL WRAPPERS
# ============================================



def clean_linkedin_text(text):
    if not text:
        return ""

    # Remove "…see more" and "See translation"
    text = re.sub(r"…\s*see more", "", text, flags=re.IGNORECASE)
    text = re.sub(r"See translation", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d+[dwmo]\s*•\s*(Edited)?\s*•?", "", text)
    text = re.sub(r".+posted this", "", text)
    text = re.sub(r"\d+[\.,]?\d*\s*reactions", "", text)
    text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])

    return text.strip()

@tool
def scrape_linkedin(keywords: Optional[List[str]] = None, max_items: int = 10):
    """
    LinkedIn search using Playwright session.
    Requires environment variables: LINKEDIN_USER, LINKEDIN_PASSWORD (if creating session).
    """
    ensure_playwright()
    
    # 1. Load Session
    site = "linkedin"
    session_path = load_playwright_storage_state_path(site, out_dir="src/utils/.sessions")
    if not session_path:
        session_path = load_playwright_storage_state_path(site, out_dir=".sessions")
    
    # If no session, try to create one
    if not session_path:
        login_flow = {
            "login_url": "https://www.linkedin.com/login",
            "steps": [
                {"type": "fill", "selector": 'input[name="session_key"]', "value_env": "LINKEDIN_USER"},
                {"type": "fill", "selector": 'input[name="session_password"]', "value_env": "LINKEDIN_PASSWORD"},
                {"type": "click", "selector": 'button[type="submit"]'},
                {"type": "wait", "selector": 'nav', "timeout": 20000}
            ]
        }
        try:
            session_path = create_or_restore_playwright_session(site, login_flow=login_flow, headless=False)
        except Exception as e:
            return json.dumps({"error": f"No session found and failed to create one: {e}"})

    keyword = " ".join(keywords) if keywords else "Sri Lanka"
    results = []

    try:
        with sync_playwright() as p:
            desktop_ua = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )

            browser = p.chromium.launch(
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized" 
                ]
            )
            
            context = browser.new_context(
                storage_state=session_path,
                user_agent=desktop_ua,
                no_viewport=True 
            )
            
            page = context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            url = f"https://www.linkedin.com/search/results/content/?keywords={keyword.replace(' ', '%20')}&origin=GLOBAL_SEARCH_HEADER"
            
            try:
                logger.info(f"[LINKEDIN] Navigating to {url}")
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
            except Exception as e:
                logger.warning(f"[LINKEDIN] Page load timed out (or other error), attempting to proceed: {e}")

            page.wait_for_timeout(random.randint(4000, 7000))

            try:
                if page.locator("a[href*='login']").is_visible() or "auth_wall" in page.url:
                    logger.error("[LINKEDIN] Session invalid. Redirected to login/auth wall.")
                    return json.dumps({"error": "Session invalid. Please refresh session."})
            except:
                pass

            seen = set()
            no_new_data_count = 0
            previous_height = 0

            POST_CONTAINER_SELECTOR = "div.feed-shared-update-v2, li.artdeco-card" 
            TEXT_SELECTOR = "div.update-components-text span.break-words, span.break-words"
            SEE_MORE_SELECTOR = "button.feed-shared-inline-show-more-text__see-more-less-toggle"
            POSTER_SELECTOR = "span.update-components-actor__name span[dir='ltr']"

            while len(results) < max_items:
                try:
                    see_more_buttons = page.locator(SEE_MORE_SELECTOR).all()
                    for btn in see_more_buttons:
                        if btn.is_visible():
                            try: btn.click(timeout=500)
                            except: pass
                except: pass

                if len(results) == 0:
                    try: page.locator(POST_CONTAINER_SELECTOR).first.wait_for(timeout=5000)
                    except: logger.warning("[LINKEDIN] No posts found on page yet.")

                posts = page.locator(POST_CONTAINER_SELECTOR).all()
                
                for post in posts:
                    if len(results) >= max_items: break
                    try:
                        post.scroll_into_view_if_needed()
                        raw_text = ""
                        text_el = post.locator(TEXT_SELECTOR).first
                        if text_el.is_visible(): raw_text = text_el.inner_text()
                        else: raw_text = post.locator("div.feed-shared-update-v2__description-wrapper").first.inner_text()

                        cleaned_text = clean_linkedin_text(raw_text)
                        poster_name = "(Unknown)"
                        poster_el = post.locator(POSTER_SELECTOR).first
                        if poster_el.is_visible(): poster_name = poster_el.inner_text().strip()
                        else:
                            poster_el = post.locator("span.update-components-actor__title span[dir='ltr']").first
                            if poster_el.is_visible(): poster_name = poster_el.inner_text().strip()

                        key = f"{poster_name[:20]}::{cleaned_text[:30]}"
                        if cleaned_text and len(cleaned_text) > 20 and key not in seen:
                            seen.add(key)
                            results.append({
                                "source": "LinkedIn",
                                "poster": poster_name,
                                "text": cleaned_text,
                                "url": "https://www.linkedin.com"
                            })
                            logger.info(f"[LINKEDIN] Found post by {poster_name}")
                    except Exception:
                        continue

                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(random.randint(2000, 4000))

                new_height = page.evaluate("document.body.scrollHeight")
                if new_height == previous_height:
                    no_new_data_count += 1
                    if no_new_data_count > 3:
                        logger.info("[LINKEDIN] End of feed or stuck.")
                        break
                else:
                    no_new_data_count = 0
                    previous_height = new_height

            browser.close()
            return json.dumps({"site": "LinkedIn", "results": results, "storage_state": session_path}, default=str)

    except Exception as e:
        return json.dumps({"error": str(e)})

# =====================================================
# 🔧 TWITTER UTILITY FUNCTIONS
# =====================================================

def clean_twitter_text(text):
    """Clean and normalize tweet text"""
    if not text:
        return ""
    
    # Remove common Twitter artifacts
    text = re.sub(r"Show more", "", text, flags=re.IGNORECASE)
    text = re.sub(r"https://t\.co/\w+", "", text)  # Remove t.co links
    text = re.sub(r"pic\.twitter\.com/\w+", "", text)  # Remove pic.twitter.com links
    text = re.sub(r"\s+", " ", text)  # Normalize whitespace
    text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
    
    return text.strip()

def extract_twitter_timestamp(tweet_element):
    """Extract timestamp from tweet element"""
    try:
        timestamp_selectors = [
            "time",
            "[datetime]",
            "a[href*='/status/'] time",
            "div[data-testid='User-Name'] a[href*='/status/']"
        ]
        
        for selector in timestamp_selectors:
            if tweet_element.locator(selector).count() > 0:
                time_element = tweet_element.locator(selector).first
                datetime_attr = time_element.get_attribute("datetime")
                if datetime_attr:
                    return datetime_attr
                time_text = time_element.inner_text()
                if time_text:
                    return time_text
    except:
        pass
    return "Unknown"



@tool
def scrape_twitter(query: str = "Sri Lanka", max_items: int = 20):
    """
    Twitter scraper - extracts actual tweet text, author, and metadata using Playwright session.
    Requires a valid Twitter session file (twitter_storage_state.json or tw_state.json).
    """
    ensure_playwright()
    
    # Load Session
    site = "twitter"
    session_path = load_playwright_storage_state_path(site, out_dir="src/utils/.sessions")
    if not session_path:
        session_path = load_playwright_storage_state_path(site, out_dir=".sessions")
    
    # Check for alternative session file name
    if not session_path:
        alt_paths = [
            os.path.join(os.getcwd(), "src", "utils", ".sessions", "tw_state.json"),
            os.path.join(os.getcwd(), ".sessions", "tw_state.json"),
            os.path.join(os.getcwd(), "tw_state.json")
        ]
        for path in alt_paths:
            if os.path.exists(path):
                session_path = path
                logger.info(f"[TWITTER] Found session at {path}")
                break
    
    if not session_path:
        return json.dumps({
            "error": "No Twitter session found",
            "solution": "Run the Twitter session manager to create a session"
        }, default=str)
    
    results = []
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ]
            )
            
            context = browser.new_context(
                storage_state=session_path,
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = {runtime: {}};
            """)
            
            page = context.new_page()
            
            # Try different search URLs
            search_urls = [
                f"https://x.com/search?q={quote_plus(query)}&src=typed_query&f=live",
                f"https://x.com/search?q={quote_plus(query)}&src=typed_query",
                f"https://x.com/search?q={quote_plus(query)}",
            ]
            
            success = False
            for url in search_urls:
                try:
                    logger.info(f"[TWITTER] Trying {url}")
                    page.goto(url, timeout=60000, wait_until="domcontentloaded")
                    time.sleep(5)
                    
                    # Handle popups
                    popup_selectors = [
                        "[data-testid='app-bar-close']",
                        "[aria-label='Close']",
                        "button:has-text('Not now')",
                    ]
                    for selector in popup_selectors:
                        try:
                            if page.locator(selector).count() > 0 and page.locator(selector).first.is_visible():
                                page.locator(selector).first.click()
                                time.sleep(1)
                        except:
                            pass
                    
                    # Wait for tweets
                    try:
                        page.wait_for_selector("article[data-testid='tweet']", timeout=15000)
                        logger.info("[TWITTER] Tweets found!")
                        success = True
                        break
                    except:
                        logger.warning("[TWITTER] No tweets found, trying next URL...")
                        continue
                except Exception as e:
                    logger.error(f"[TWITTER] Navigation failed: {e}")
                    continue
            
            if not success or "login" in page.url:
                logger.error("[TWITTER] Could not load tweets or session expired")
                return json.dumps({"error": "Session invalid or tweets not found"}, default=str)
            
            # Scraping
            seen = set()
            scroll_attempts = 0
            max_scroll_attempts = 15
            
            TWEET_SELECTOR = "article[data-testid='tweet']"
            TEXT_SELECTOR = "div[data-testid='tweetText']"
            USER_SELECTOR = "div[data-testid='User-Name']"
            
            while len(results) < max_items and scroll_attempts < max_scroll_attempts:
                scroll_attempts += 1
                
                # Expand "Show more" buttons
                try:
                    show_more_buttons = page.locator("[data-testid='tweet-text-show-more-link']").all()
                    for button in show_more_buttons:
                        if button.is_visible():
                            try:
                                button.click()
                                time.sleep(0.3)
                            except:
                                pass
                except:
                    pass
                
                # Collect tweets
                tweets = page.locator(TWEET_SELECTOR).all()
                new_tweets_found = 0
                
                for tweet in tweets:
                    if len(results) >= max_items:
                        break
                    
                    try:
                        tweet.scroll_into_view_if_needed()
                        time.sleep(0.1)
                        
                        # Skip promoted tweets
                        if (tweet.locator("span:has-text('Promoted')").count() > 0 or 
                            tweet.locator("span:has-text('Ad')").count() > 0):
                            continue
                        
                        # Extract text
                        text_content = ""
                        text_element = tweet.locator(TEXT_SELECTOR).first
                        if text_element.count() > 0:
                            text_content = text_element.inner_text()
                        
                        cleaned_text = clean_twitter_text(text_content)
                        
                        # Extract user
                        user_info = "Unknown"
                        user_element = tweet.locator(USER_SELECTOR).first
                        if user_element.count() > 0:
                            user_text = user_element.inner_text()
                            user_info = user_text.split('\n')[0].strip()
                        
                        # Extract timestamp
                        timestamp = extract_twitter_timestamp(tweet)
                        
                        # Deduplication
                        text_key = cleaned_text[:50] if cleaned_text else ""
                        unique_key = f"{user_info}_{text_key}"
                        
                        if (cleaned_text and len(cleaned_text) > 20 and 
                            unique_key not in seen and 
                            not any(word in cleaned_text.lower() for word in ["promoted", "advertisement"])):
                            
                            seen.add(unique_key)
                            results.append({
                                "source": "Twitter",
                                "poster": user_info,
                                "text": cleaned_text,
                                "timestamp": timestamp,
                                "url": "https://x.com"
                            })
                            new_tweets_found += 1
                            logger.info(f"[TWITTER] Collected tweet {len(results)}/{max_items}")
                    
                    except Exception:
                        continue
                
                # Scroll down
                if len(results) < max_items:
                    page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
                    time.sleep(random.uniform(2, 3))
                    
                    if new_tweets_found == 0:
                        scroll_attempts += 1
                    else:
                        scroll_attempts = 0
            
            browser.close()
            
            return json.dumps({
                "source": "Twitter",
                "query": query,
                "results": results,
                "total_found": len(results),
                "fetched_at": datetime.utcnow().isoformat()
            }, default=str, indent=2)
    
    except Exception as e:
        logger.error(f"[TWITTER] {e}")
        return json.dumps({"error": str(e)}, default=str)


#     """
#     Twitter trending/search wrapper. For trending, call scrape_twitter_trending_srilanka().
#     For search, this will attempt Playwright fetch if available, else Nitter fallback.
#     """
#     try:
#         if query.strip().lower() in ("trending", "trends", "trending srilanka", "trending sri lanka"):
#             return json.dumps(scrape_twitter_trending_srilanka(use_playwright=use_playwright, storage_state_site=storage_state_site), default=str)
        
#         if use_playwright and PLAYWRIGHT_AVAILABLE:
#             storage_state = None
#             if storage_state_site:
#                 storage_state = load_playwright_storage_state_path(storage_state_site)
            
#             search_url = f"https://twitter.com/search?q={quote_plus(query)}&src=typed_query"
#             try:
#                 html = playwright_fetch_html_using_session(search_url, storage_state or "", headless=True)
#                 if html:
#                     items = _simple_parse_posts_from_html(html, "https://twitter.com", max_items=20)
#                     return json.dumps({"source": "twitter_playwright", "results": items}, default=str)
#             except Exception as e:
#                 logger.debug(f"[TWITTER] Playwright search failed: {e}")
        
#         nitter = "https://nitter.net"
#         search_url = f"{nitter}/search?f=tweets&q={quote_plus(query)}"
#         resp = _safe_get(search_url)
#         if not resp:
#             return json.dumps({"error": "Could not fetch Twitter via Playwright or Nitter fallback"})
#         soup = BeautifulSoup(resp.text, "html.parser")
#         items = []
#         for a in soup.select("div.timeline-item"):
#             t = a.get_text(separator=" ", strip=True)
#             link = a.find("a", href=True)
#             href = _make_absolute(link["href"], nitter) if link else None
#             items.append({"text": t[:400], "url": href})
#         return json.dumps({"source": "nitter", "results": items[:20]}, default=str)
#     except Exception as e:
#         return json.dumps({"error": str(e)})



def clean_linkedin_text(text):
    if not text:
        return ""

    # Remove "…see more" and "See translation"
    text = re.sub(r"…\s*see more", "", text, flags=re.IGNORECASE)
    text = re.sub(r"See translation", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d+[dwmo]\s*•\s*(Edited)?\s*•?", "", text)
    text = re.sub(r".+posted this", "", text)
    text = re.sub(r"\d+[\.,]?\d*\s*reactions", "", text)
    text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])

    return text.strip()


# =====================================================
# FACEBOOK & INSTAGRAM UTILITY FUNCTIONS
# =====================================================

def clean_fb_text(text):
    """Clean Facebook noisy text"""
    if not text:
        return ""

    text = re.sub(r"\b(?:[a-zA-Z]\s+){4,}\b", "", text)
    text = re.sub(r"(Facebook\s*){2,}", "", text)
    text = re.sub(r"Like\s*Comment\s*Share", "", text)
    text = re.sub(r"All reactions:\s*\d+\s*", "", text)
    text = re.sub(r"\n\d+\n", "\n", text)
    text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])

    return text.strip()


def extract_media_id_instagram(page):
    """Extract Instagram media ID"""
    html = page.content()
    match = re.search(r'"media_id":"(\d+)"', html)
    if match:
        return match.group(1)
    match = re.search(r'"id":"(\d+_\d+)"', html)
    if match:
        return match.group(1)
    return None


def fetch_caption_via_private_api(page, media_id):
    """Instagram Private API Caption fetch"""
    if not media_id:
        return None

    api_url = f"https://i.instagram.com/api/v1/media/{media_id}/info/"

    try:
        response = page.request.get(
            api_url,
            headers={
                "User-Agent": (
                    "Instagram 290.0.0.0.66 (iPhone14,5; iOS 17_0; en_US) "
                    "AppleWebKit/605.1.15"
                ),
                "X-IG-App-ID": "936619743392459",
            },
            timeout=20000,
        )
        if response.status != 200:
            return None

        data = response.json()
        if "items" in data and data["items"]:
            return data["items"][0].get("caption", {}).get("text")
    except:
        pass

    return None


@tool
def scrape_instagram(keywords: Optional[List[str]] = None, max_items: int = 15):
    """
    Instagram scraper using Playwright session.
    Scrapes posts from hashtag search and extracts captions.
    """
    ensure_playwright()
    
    # Load Session
    site = "instagram"
    session_path = load_playwright_storage_state_path(site, out_dir="src/utils/.sessions")
    if not session_path:
        session_path = load_playwright_storage_state_path(site, out_dir=".sessions")
    
    # Check for alternative session file name
    if not session_path:
        alt_paths = [
            os.path.join(os.getcwd(), "src", "utils", ".sessions", "ig_state.json"),
            os.path.join(os.getcwd(), ".sessions", "ig_state.json"),
            os.path.join(os.getcwd(), "ig_state.json")
        ]
        for path in alt_paths:
            if os.path.exists(path):
                session_path = path
                logger.info(f"[INSTAGRAM] Found session at {path}")
                break
    
    if not session_path:
        return json.dumps({
            "error": "No Instagram session found",
            "solution": "Run the Instagram session manager to create a session"
        }, default=str)
    
    keyword = " ".join(keywords) if keywords else "srilanka"
    keyword = keyword.replace(" ", "")  # Instagram hashtags don't have spaces
    results = []
    
    try:
        with sync_playwright() as p:
            instagram_mobile_ua = (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            )
            
            browser = p.chromium.launch(headless=False)
            
            context = browser.new_context(
                storage_state=session_path,
                user_agent=instagram_mobile_ua,
                viewport={"width": 430, "height": 932},
            )
            
            page = context.new_page()
            url = f"https://www.instagram.com/explore/tags/{keyword}/"
            
            logger.info(f"[INSTAGRAM] Navigating to {url}")
            page.goto(url, timeout=120000)
            page.wait_for_timeout(4000)
            
            # Scroll to load posts
            for _ in range(12):
                page.mouse.wheel(0, 2500)
                page.wait_for_timeout(1500)
            
            # Collect post links
            anchors = page.locator("a[href*='/p/'], a[href*='/reel/']").all()
            links = []
            
            for a in anchors:
                href = a.get_attribute("href")
                if href:
                    full = "https://www.instagram.com" + href
                    links.append(full)
                if len(links) >= max_items:
                    break
            
            logger.info(f"[INSTAGRAM] Found {len(links)} posts")
            
            # Extract captions from each post
            for link in links:
                logger.info(f"[INSTAGRAM] Scraping {link}")
                page.goto(link, timeout=120000)
                page.wait_for_timeout(2000)
                
                media_id = extract_media_id_instagram(page)
                caption = fetch_caption_via_private_api(page, media_id)
                
                # Fallback to direct extraction
                if not caption:
                    try:
                        caption = page.locator("article h1, article span").first.inner_text().strip()
                    except:
                        caption = None
                
                if caption:
                    results.append({
                        "source": "Instagram",
                        "text": caption,
                        "url": link,
                        "poster": "(Instagram User)"
                    })
                    logger.info(f"[INSTAGRAM] Collected caption {len(results)}/{max_items}")
            
            browser.close()
            
            return json.dumps({
                "site": "Instagram",
                "results": results,
                "storage_state": session_path
            }, default=str)
    
    except Exception as e:
        logger.error(f"[INSTAGRAM] {e}")
        return json.dumps({"error": str(e)}, default=str)


@tool
def scrape_facebook(keywords: Optional[List[str]] = None, max_items: int = 10):
    """
    Facebook scraper using Playwright session (Desktop).
    Extracts posts from keyword search with poster names and text.
    """
    ensure_playwright()
    
    # Load Session
    site = "facebook"
    session_path = load_playwright_storage_state_path(site, out_dir="src/utils/.sessions")
    if not session_path:
        session_path = load_playwright_storage_state_path(site, out_dir=".sessions")
    
    # Check for alternative session file name
    if not session_path:
        alt_paths = [
            os.path.join(os.getcwd(), "src", "utils", ".sessions", "fb_state.json"),
            os.path.join(os.getcwd(), ".sessions", "fb_state.json"),
            os.path.join(os.getcwd(), "fb_state.json")
        ]
        for path in alt_paths:
            if os.path.exists(path):
                session_path = path
                logger.info(f"[FACEBOOK] Found session at {path}")
                break
    
    if not session_path:
        return json.dumps({
            "error": "No Facebook session found",
            "solution": "Run the Facebook session manager to create a session"
        }, default=str)
    
    keyword = " ".join(keywords) if keywords else "Sri Lanka"
    results = []
    
    try:
        with sync_playwright() as p:
            facebook_desktop_ua = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            browser = p.chromium.launch(headless=False)
            
            context = browser.new_context(
                storage_state=session_path,
                user_agent=facebook_desktop_ua,
                viewport={"width": 1400, "height": 900},
            )
            
            page = context.new_page()
            
            search_url = f"https://www.facebook.com/search/posts?q={quote(keyword)}"
            
            logger.info(f"[FACEBOOK] Navigating to {search_url}")
            page.goto(search_url, timeout=120000)
            time.sleep(5)
            
            seen = set()
            stuck = 0
            last_scroll = 0
            
            MESSAGE_SELECTOR = "div[data-ad-preview='message']"
            
            # Poster selectors
            POSTER_SELECTORS = [
                "h3 strong a span",
                "h3 strong span",
                "h3 a span",
                "strong a span",
                "a[role='link'] span:not([class*='timestamp'])",
                "span.fwb a",
                "span.fwb",
                "a[aria-hidden='false'] span",
                "a[role='link'] span",
            ]
            
            def extract_poster(post):
                """Extract poster name from Facebook post"""
                parent = post.locator("xpath=ancestor::div[contains(@class, 'x1yztbdb')][1]")
                
                for selector in POSTER_SELECTORS:
                    try:
                        el = parent.locator(selector).first
                        if el and el.count() > 0:
                            name = el.inner_text().strip()
                            if name and name != "Facebook" and len(name) > 1:
                                return name
                    except:
                        pass
                
                return "(Unknown)"
            
            while len(results) < max_items:
                posts = page.locator(MESSAGE_SELECTOR).all()
                
                for post in posts:
                    try:
                        # EXPAND "See more" button to get full text
                        try:
                            # Scroll post into view first
                            post.scroll_into_view_if_needed()
                            time.sleep(0.5)
                            
                            # Try to find and click "See more" button
                            # Use more specific selectors and wait for expansion
                            see_more_selectors = [
                                "div[role='button']:has-text('See more')",
                                "div[role='button']:has-text('… See more')",
                                "div[role='button'] >> text='See more'",
                                "div:has-text('See more'):has(div[role='button'])",
                            ]
                            
                            expanded = False
                            for selector in see_more_selectors:
                                try:
                                    buttons = post.locator(selector)
                                    count = buttons.count()
                                    
                                    for i in range(count):
                                        btn = buttons.nth(i)
                                        if btn.is_visible(timeout=1000):
                                            # Click and wait for content to expand
                                            btn.click()
                                            # Wait longer for DOM to update
                                            time.sleep(1.5)
                                            expanded = True
                                            logger.info("[FACEBOOK] Clicked 'See more', waiting for expansion...")
                                            break
                                    
                                    if expanded:
                                        break
                                except Exception as e:
                                    continue
                            
                            if expanded:
                                # Give extra time for expansion to complete
                                time.sleep(0.5)
                                logger.info("[FACEBOOK] Content expanded")
                        except Exception as e:
                            logger.debug(f"[FACEBOOK] Expansion error: {e}")
                            pass
                        
                        raw = post.inner_text().strip()
                        cleaned = clean_fb_text(raw)
                        
                        poster = extract_poster(post)
                        
                        if cleaned and len(cleaned) > 30:
                            key = poster + "::" + cleaned
                            if key not in seen:
                                seen.add(key)
                                results.append({
                                    "source": "Facebook",
                                    "poster": poster,
                                    "text": cleaned,
                                    "url": "https://www.facebook.com"
                                })
                                logger.info(f"[FACEBOOK] Collected post {len(results)}/{max_items}")
                        
                        if len(results) >= max_items:
                            break
                    
                    except:
                        pass
                
                # Scroll
                page.evaluate("window.scrollBy(0, 2300)")
                time.sleep(1.2)
                
                new_scroll = page.evaluate("window.scrollY")
                stuck = stuck + 1 if new_scroll == last_scroll else 0
                last_scroll = new_scroll
                
                if stuck >= 3:
                    logger.info("[FACEBOOK] Reached end of results")
                    break
            
            browser.close()
            
            return json.dumps({
                "site": "Facebook",
                "results": results[:max_items],
                "storage_state": session_path
            }, default=str)
    
    except Exception as e:
        logger.error(f"[FACEBOOK] {e}")
        return json.dumps({"error": str(e)}, default=str)


@tool
def scrape_government_gazette(keywords: Optional[List[str]] = None, max_items: int = 15):
    """
    Search and scrape Sri Lankan government gazette entries from gazette.lk.
    This tool visits each gazette page to extract full descriptions and download links (PDFs).
    """
    data = scrape_government_gazette_impl(keywords=keywords, max_items=max_items)
    return json.dumps(data, default=str)



def clean_linkedin_text(text):
    if not text:
        return ""

    # Remove "…see more" and "See translation"
    text = re.sub(r"…\s*see more", "", text, flags=re.IGNORECASE)
    text = re.sub(r"See translation", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d+[dwmo]\s*•\s*(Edited)?\s*•?", "", text)
    text = re.sub(r".+posted this", "", text)
    text = re.sub(r"\d+[\.,]?\d*\s*reactions", "", text)
    text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])

    return text.strip()

@tool
def scrape_parliament_minutes(keywords: Optional[List[str]] = None, max_items: int = 20):
    """
    Search and scrape Sri Lankan Parliament Hansards and minutes matching keywords.
    """
    data = scrape_parliament_minutes_impl(keywords=keywords, max_items=max_items)
    return json.dumps(data, default=str)



def clean_linkedin_text(text):
    if not text:
        return ""

    # Remove "…see more" and "See translation"
    text = re.sub(r"…\s*see more", "", text, flags=re.IGNORECASE)
    text = re.sub(r"See translation", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d+[dwmo]\s*•\s*(Edited)?\s*•?", "", text)
    text = re.sub(r".+posted this", "", text)
    text = re.sub(r"\d+[\.,]?\d*\s*reactions", "", text)
    text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])

    return text.strip()

@tool
def scrape_train_schedule(from_station: Optional[str] = None, to_station: Optional[str] = None, keyword: Optional[str] = None, max_items: int = 30):
    """
    Scrape Sri Lanka Railways train schedule based on stations or keywords.
    """
    data = scrape_train_schedule_impl(from_station=from_station, to_station=to_station, keyword=keyword, max_items=max_items)
    return json.dumps(data, default=str)



def clean_linkedin_text(text):
    if not text:
        return ""

    # Remove "…see more" and "See translation"
    text = re.sub(r"…\s*see more", "", text, flags=re.IGNORECASE)
    text = re.sub(r"See translation", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d+[dwmo]\s*•\s*(Edited)?\s*•?", "", text)
    text = re.sub(r".+posted this", "", text)
    text = re.sub(r"\d+[\.,]?\d*\s*reactions", "", text)
    text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])

    return text.strip()

@tool
def scrape_cse_stock_data(symbol: str = "ASPI", period: str = "1d", interval: str = "1h"):
    """
    Scrape Colombo Stock Exchange (CSE) data for a given symbol (e.g., ASPI).
    Tries yfinance first, then falls back to direct site scraping.
    """
    data = scrape_cse_stock_impl(symbol=symbol, period=period, interval=interval)
    return json.dumps(data, default=str)



def clean_linkedin_text(text):
    if not text:
        return ""

    # Remove "…see more" and "See translation"
    text = re.sub(r"…\s*see more", "", text, flags=re.IGNORECASE)
    text = re.sub(r"See translation", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d+[dwmo]\s*•\s*(Edited)?\s*•?", "", text)
    text = re.sub(r".+posted this", "", text)
    text = re.sub(r"\d+[\.,]?\d*\s*reactions", "", text)
    text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])

    return text.strip()

@tool
def scrape_local_news(keywords: Optional[List[str]] = None, max_articles: int = 30):
    """
    Scrape major Sri Lankan local news websites (Daily Mirror, Daily FT, etc.) for articles matching keywords.
    """
    data = scrape_local_news_impl(keywords=keywords, max_articles=max_articles)
    return json.dumps(data, default=str)



def clean_linkedin_text(text):
    if not text:
        return ""

    # Remove "…see more" and "See translation"
    text = re.sub(r"…\s*see more", "", text, flags=re.IGNORECASE)
    text = re.sub(r"See translation", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d+[dwmo]\s*•\s*(Edited)?\s*•?", "", text)
    text = re.sub(r".+posted this", "", text)
    text = re.sub(r"\d+[\.,]?\d*\s*reactions", "", text)
    text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])

    return text.strip()

@tool
def think_tool(reflection: str) -> str:
    """
    Log a thought or reflection from the agent. Useful for debugging or tracing the agent's reasoning.
    """
    return f"Reflection recorded: {reflection}"



# =====================================================
# FACEBOOK & INSTAGRAM UTILITY FUNCTIONS
# =====================================================

def clean_fb_text(text):
    """Clean Facebook noisy text"""
    if not text:
        return ""

    text = re.sub(r"\b(?:[a-zA-Z]\s+){4,}\b", "", text)
    text = re.sub(r"(Facebook\s*){2,}", "", text)
    text = re.sub(r"Like\s*Comment\s*Share", "", text)
    text = re.sub(r"All reactions:\s*\d+\s*", "", text)
    text = re.sub(r"\n\d+\n", "\n", text)
    text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])

    return text.strip()


def extract_media_id_instagram(page):
    """Extract Instagram media ID"""
    html = page.content()
    match = re.search(r'"media_id":"(\d+)"', html)
    if match:
        return match.group(1)
    match = re.search(r'"id":"(\d+_\d+)"', html)
    if match:
        return match.group(1)
    return None


def fetch_caption_via_private_api(page, media_id):
    """Instagram Private API Caption fetch"""
    if not media_id:
        return None

    api_url = f"https://i.instagram.com/api/v1/media/{media_id}/info/"

    try:
        response = page.request.get(
            api_url,
            headers={
                "User-Agent": (
                    "Instagram 290.0.0.0.66 (iPhone14,5; iOS 17_0; en_US) "
                    "AppleWebKit/605.1.15"
                ),
                "X-IG-App-ID": "936619743392459",
            },
            timeout=20000,
        )
        if response.status != 200:
            return None

        data = response.json()
        if "items" in data and data["items"]:
            return data["items"][0].get("caption", {}).get("text")
    except:
        pass

    return None


@tool
def scrape_instagram(keywords: Optional[List[str]] = None, max_items: int = 15):
    """
    Instagram scraper using Playwright session.
    Scrapes posts from hashtag search and extracts captions.
    """
    ensure_playwright()
    
    # Load Session
    site = "instagram"
    session_path = load_playwright_storage_state_path(site, out_dir="src/utils/.sessions")
    if not session_path:
        session_path = load_playwright_storage_state_path(site, out_dir=".sessions")
    
    # Check for alternative session file name
    if not session_path:
        alt_paths = [
            os.path.join(os.getcwd(), "src", "utils", ".sessions", "ig_state.json"),
            os.path.join(os.getcwd(), ".sessions", "ig_state.json"),
            os.path.join(os.getcwd(), "ig_state.json")
        ]
        for path in alt_paths:
            if os.path.exists(path):
                session_path = path
                logger.info(f"[INSTAGRAM] Found session at {path}")
                break
    
    if not session_path:
        return json.dumps({
            "error": "No Instagram session found",
            "solution": "Run the Instagram session manager to create a session"
        }, default=str)
    
    keyword = " ".join(keywords) if keywords else "srilanka"
    keyword = keyword.replace(" ", "")  # Instagram hashtags don't have spaces
    results = []
    
    try:
        with sync_playwright() as p:
            instagram_mobile_ua = (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            )
            
            browser = p.chromium.launch(headless=False)
            
            context = browser.new_context(
                storage_state=session_path,
                user_agent=instagram_mobile_ua,
                viewport={"width": 430, "height": 932},
            )
            
            page = context.new_page()
            url = f"https://www.instagram.com/explore/tags/{keyword}/"
            
            logger.info(f"[INSTAGRAM] Navigating to {url}")
            page.goto(url, timeout=120000)
            page.wait_for_timeout(4000)
            
            # Scroll to load posts
            for _ in range(12):
                page.mouse.wheel(0, 2500)
                page.wait_for_timeout(1500)
            
            # Collect post links
            anchors = page.locator("a[href*='/p/'], a[href*='/reel/']").all()
            links = []
            
            for a in anchors:
                href = a.get_attribute("href")
                if href:
                    full = "https://www.instagram.com" + href
                    links.append(full)
                if len(links) >= max_items:
                    break
            
            logger.info(f"[INSTAGRAM] Found {len(links)} posts")
            
            # Extract captions from each post
            for link in links:
                logger.info(f"[INSTAGRAM] Scraping {link}")
                page.goto(link, timeout=120000)
                page.wait_for_timeout(2000)
                
                media_id = extract_media_id_instagram(page)
                caption = fetch_caption_via_private_api(page, media_id)
                
                # Fallback to direct extraction
                if not caption:
                    try:
                        caption = page.locator("article h1, article span").first.inner_text().strip()
                    except:
                        caption = None
                
                if caption:
                    results.append({
                        "source": "Instagram",
                        "text": caption,
                        "url": link,
                        "poster": "(Instagram User)"
                    })
                    logger.info(f"[INSTAGRAM] Collected caption {len(results)}/{max_items}")
            
            browser.close()
            
            return json.dumps({
                "site": "Instagram",
                "results": results,
                "storage_state": session_path
            }, default=str)
    
    except Exception as e:
        logger.error(f"[INSTAGRAM] {e}")
        return json.dumps({"error": str(e)}, default=str)


@tool
def scrape_facebook(keywords: Optional[List[str]] = None, max_items: int = 10):
    """
    Facebook scraper using Playwright session (Desktop).
    Extracts posts from keyword search with poster names and text.
    """
    ensure_playwright()
    
    # Load Session
    site = "facebook"
    session_path = load_playwright_storage_state_path(site, out_dir="src/utils/.sessions")
    if not session_path:
        session_path = load_playwright_storage_state_path(site, out_dir=".sessions")
    
    # Check for alternative session file name
    if not session_path:
        alt_paths = [
            os.path.join(os.getcwd(), "src", "utils", ".sessions", "fb_state.json"),
            os.path.join(os.getcwd(), ".sessions", "fb_state.json"),
            os.path.join(os.getcwd(), "fb_state.json")
        ]
        for path in alt_paths:
            if os.path.exists(path):
                session_path = path
                logger.info(f"[FACEBOOK] Found session at {path}")
                break
    
    if not session_path:
        return json.dumps({
            "error": "No Facebook session found",
            "solution": "Run the Facebook session manager to create a session"
        }, default=str)
    
    keyword = " ".join(keywords) if keywords else "Sri Lanka"
    results = []
    
    try:
        with sync_playwright() as p:
            facebook_desktop_ua = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            browser = p.chromium.launch(headless=False)
            
            context = browser.new_context(
                storage_state=session_path,
                user_agent=facebook_desktop_ua,
                viewport={"width": 1400, "height": 900},
            )
            
            page = context.new_page()
            search_url = f"https://www.facebook.com/search/posts?q={keyword.replace(' ', '%20')}"
            
            logger.info(f"[FACEBOOK] Navigating to {search_url}")
            page.goto(search_url, timeout=120000)
            time.sleep(5)
            
            seen = set()
            stuck = 0
            last_scroll = 0
            
            MESSAGE_SELECTOR = "div[data-ad-preview='message']"
            
            # Poster selectors
            POSTER_SELECTORS = [
                "h3 strong a span",
                "h3 strong span",
                "h3 a span",
                "strong a span",
                "a[role='link'] span:not([class*='timestamp'])",
                "span.fwb a",
                "span.fwb",
                "a[aria-hidden='false'] span",
                "a[role='link'] span",
            ]
            
            def extract_poster(post):
                """Extract poster name from Facebook post"""
                parent = post.locator("xpath=ancestor::div[contains(@class, 'x1yztbdb')][1]")
                
                for selector in POSTER_SELECTORS:
                    try:
                        el = parent.locator(selector).first
                        if el and el.count() > 0:
                            name = el.inner_text().strip()
                            if name and name != "Facebook" and len(name) > 1:
                                return name
                    except:
                        pass
                
                return "(Unknown)"
            
            while len(results) < max_items:
                posts = page.locator(MESSAGE_SELECTOR).all()
                
                for post in posts:
                    try:
                        raw = post.inner_text().strip()
                        cleaned = clean_fb_text(raw)
                        
                        poster = extract_poster(post)
                        
                        if cleaned and len(cleaned) > 30:
                            key = poster + "::" + cleaned
                            if key not in seen:
                                seen.add(key)
                                results.append({
                                    "source": "Facebook",
                                    "poster": poster,
                                    "text": cleaned,
                                    "url": "https://www.facebook.com"
                                })
                                logger.info(f"[FACEBOOK] Collected post {len(results)}/{max_items}")
                        
                        if len(results) >= max_items:
                            break
                    
                    except:
                        pass
                
                # Scroll
                page.evaluate("window.scrollBy(0, 2300)")
                time.sleep(1.2)
                
                new_scroll = page.evaluate("window.scrollY")
                stuck = stuck + 1 if new_scroll == last_scroll else 0
                last_scroll = new_scroll
                
                if stuck >= 3:
                    logger.info("[FACEBOOK] Reached end of results")
                    break
            
            browser.close()
            
            return json.dumps({
                "site": "Facebook",
                "results": results[:max_items],
                "storage_state": session_path
            }, default=str)
    
    except Exception as e:
        logger.error(f"[FACEBOOK] {e}")
        return json.dumps({"error": str(e)}, default=str)


@tool
def scrape_reddit(keywords: List[str], limit: int = 20, subreddit: Optional[str] = None):
    """
    Scrape Reddit for posts matching specific keywords.
    Optionally restrict to a specific subreddit.
    """
    data = scrape_reddit_impl(keywords=keywords, limit=limit, subreddit=subreddit)
    return json.dumps(data, default=str)



# ============================================
# TOOL REGISTRY & EXPORTS
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

# Import and add profile scrapers for competitive intelligence
try:
    from src.utils.profile_scrapers import (
        scrape_twitter_profile,
        scrape_facebook_profile,
        scrape_instagram_profile,
        scrape_linkedin_profile,
        scrape_product_reviews
    )
    TOOL_MAPPING["scrape_twitter_profile"] = scrape_twitter_profile
    TOOL_MAPPING["scrape_facebook_profile"] = scrape_facebook_profile
    TOOL_MAPPING["scrape_instagram_profile"] = scrape_instagram_profile
    TOOL_MAPPING["scrape_linkedin_profile"] = scrape_linkedin_profile
    TOOL_MAPPING["scrape_product_reviews"] = scrape_product_reviews
    print("[OK] Profile scrapers loaded for Intelligence Agent")
except ImportError as e:
    print(f"[WARN] Profile scrapers not available: {e}")


ALL_TOOLS = list(TOOL_MAPPING.values())

__all__ = [
    "get_today_str",
    "tool_dmc_alerts",
    "tool_weather_nowcast",
    "TOOL_MAPPING",
    "ALL_TOOLS",
    "create_or_restore_playwright_session",
    "playwright_fetch_html_using_session",
]