"""
Stage A: Scrape business URL and extract brand information using robust Playwright logic
"""

from __future__ import annotations

import re
import importlib
import requests
import random
import socket
import ipaddress
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from typing import Dict, Any, List

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

STEALTH_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}


def _is_safe_url(url: str) -> bool:
    """H4 FIX: Enhanced SSRF protection with IPv6 support and broader checks."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
            
        hostname = parsed.hostname
        if not hostname:
            return False
        
        # Block common internal hostnames
        blocked_hosts = {"localhost", "metadata.google.internal", "169.254.169.254"}
        if hostname.lower() in blocked_hosts:
            return False
            
        # Resolve ALL addresses (IPv4 + IPv6) to block DNS rebinding via IPv6
        try:
            addr_infos = socket.getaddrinfo(hostname, None)
        except socket.gaierror:
            return False
        
        for addr_info in addr_infos:
            ip_str = addr_info[4][0]
            ip_obj = ipaddress.ip_address(ip_str)
            
            # Block private, loopback, link-local, multicast, and reserved IPs
            if (ip_obj.is_loopback or ip_obj.is_private or ip_obj.is_link_local 
                or ip_obj.is_multicast or ip_obj.is_reserved):
                return False
            
        return True
    except Exception:
        return False


def scrape_business_url(url: str) -> Dict[str, Any]:
    """
    Scrape a business URL using Playwright -> Requests -> Domain stub fallback.
    Returns the exact Dict shape expected by script_generator.py.
    """
    if not _is_safe_url(url):
        return {
            "url": url,
            "fetch_method": "fallback",
            "company_name": "Invalid URL",
            "tagline": "Discover quality you can trust",
            "description": "Information not available.",
            "products": ["Services", "Solutions", "Products"],
            "industry": "services",
            "call_to_action": "Contact us today",
            "images": [],
            "og_image": None,
            "colors": [],
            "tone": "professional",
            "target_audience": "general",
        }

    return (
        _try_playwright(url)
        or _try_requests(url)
        or _try_domain(url)
    )


def _try_playwright(url: str) -> dict | None:
    try:
        sync_api = importlib.import_module("playwright.sync_api")
        sync_playwright = getattr(sync_api, "sync_playwright")
    except Exception:
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ]
            )
            ctx = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1280, "height": 800},
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Cache-Control": "no-cache",
                }
            )
            page = ctx.new_page()

            # Hide bot fingerprint
            page.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
            )

            resp = page.goto(url, timeout=20000, wait_until="domcontentloaded")

            if resp and resp.status == 403:
                browser.close()
                return None

            og_title    = _get_meta(page, 'meta[property="og:title"]')
            page_title  = page.title()
            h1_text     = _safe_text(page, "h1")
            brand_name  = og_title or h1_text or page_title or url

            og_desc     = _get_meta(page, 'meta[property="og:description"]')
            meta_desc   = _get_meta(page, 'meta[name="description"]')
            tagline     = og_desc or meta_desc or ""

            og_image    = _get_meta(page, 'meta[property="og:image"]')
            images      = page.eval_on_selector_all(
                "img[src]",
                "imgs => imgs.map(i=>i.src).filter(s=>s.startsWith('http')).slice(0,6)"
            )

            colors      = _extract_colors_pw(page)
            html        = page.content()
            browser.close()

        # Extract remaining fields via BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        products = extract_products(soup)
        industry = extract_industry(soup)
        cta = extract_cta(soup)

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = " ".join(soup.get_text().split())[:1500]

        return {
            "url": url,
            "fetch_method": "playwright",
            "company_name": brand_name[:100] if brand_name else "Business",
            "tagline": tagline[:300] if tagline else "",
            "description": text[:1000] if text else "",
            "products": products,
            "industry": industry,
            "call_to_action": cta,
            "images": images,
            "og_image": og_image,
            "colors": colors,
            "tone": "professional",
            "target_audience": "general",
        }

    except Exception as e:
        # L3 FIX: Log playwright errors instead of silently swallowing
        print(f"Playwright scraping failed for {url}: {e}")
        return None


def _try_requests(url: str) -> dict | None:
    try:
        headers = {"User-Agent": random.choice(USER_AGENTS), **STEALTH_HEADERS}
        r = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        if r.status_code == 403:
            return None
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")
        og_title = soup.find("meta", {"property": "og:title"})
        og_desc  = soup.find("meta", {"property": "og:description"})
        og_img   = soup.find("meta", {"property": "og:image"})
        title    = soup.find("title")

        name = (og_title["content"] if og_title and og_title.get("content") else
                title.text.strip() if title else url)
                
        tagline = og_desc["content"] if og_desc and og_desc.get("content") else extract_tagline(soup)

        products = extract_products(soup)
        industry = extract_industry(soup)
        cta = extract_cta(soup)

        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        text = " ".join(soup.get_text().split())[:1500]

        return {
            "url": url,
            "fetch_method": "requests",
            "company_name": name[:100],
            "tagline": tagline[:300],
            "description": text[:1000],
            "products": products,
            "industry": industry,
            "call_to_action": cta,
            "images": [],
            "og_image": og_img["content"] if og_img and og_img.get("content") else None,
            "colors": [],
            "tone": "professional",
            "target_audience": "general",
        }
    except Exception:
        return None


def _try_domain(url: str) -> dict:
    domain = url.split("//")[-1].split("/")[0].replace("www.", "")
    brand_name = domain.split(".")[0].replace("-", " ").replace("_", " ").title()

    return {
        "url": url,
        "fetch_method": "fallback",
        "company_name": brand_name,
        "tagline": f"Discover {brand_name} — quality you can trust",
        "description": f"{brand_name} is a professional business providing high-quality products and services. Visit {domain} to learn more.",
        "products": ["Services", "Solutions", "Products"],
        "industry": "services",
        "call_to_action": "Contact us today",
        "images": [],
        "og_image": None,
        "colors": [],
        "tone": "professional",
        "target_audience": "general",
    }


# ── Helpers ──

def _get_meta(page, selector: str) -> str | None:
    try:
        el = page.locator(selector).first
        val = el.get_attribute("content", timeout=2000)
        return val.strip() if val else None
    except Exception:
        return None

def _safe_text(page, selector: str) -> str | None:
    try:
        el = page.locator(selector).first
        val = el.text_content(timeout=2000)
        return val.strip() if val else None
    except Exception:
        return None

def _extract_colors_pw(page) -> list:
    try:
        return page.evaluate("""
            () => {
                const found = new Set();
                for (const el of document.querySelectorAll('*')) {
                    const s = window.getComputedStyle(el);
                    const bg = s.backgroundColor;
                    const c  = s.color;
                    if (bg && !bg.includes('rgba(0, 0, 0, 0)')) found.add(bg);
                    if (c)  found.add(c);
                    if (found.size >= 5) break;
                }
                return [...found].slice(0, 5);
            }
        """)
    except Exception:
        return []


def extract_tagline(soup) -> str:
    meta_desc = soup.find('meta', {'name': 'description'})
    if meta_desc and meta_desc.get('content'):
        return meta_desc['content'][:150]
    h2 = soup.find('h2')
    if h2 and h2.string:
        return h2.string.strip()[:150]
    p = soup.find('p')
    if p and p.string:
        return p.string.strip()[:150]
    return "Professional services for your business"

def extract_products(soup) -> list:
    products = []
    h3_tags = soup.find_all('h3', limit=5)
    for h3 in h3_tags:
        text = h3.get_text().strip()
        if text and len(text) > 3:
            products.append(text[:50])
    lis = soup.find_all('li', limit=5)
    for li in lis:
        text = li.get_text().strip()
        if text and len(text) > 3:
            products.append(text[:50])
    return products[:5] if products else ["Services", "Solutions", "Products"]

def extract_industry(soup) -> str:
    page_text = soup.get_text().lower()
    industries = {
        "healthcare": ["hospital", "clinic", "doctor", "medical", "health"],
        "finance": ["bank", "loan", "investment", "insurance", "financial"],
        "retail": ["shop", "store", "buy", "sale", "product"],
        "technology": ["software", "app", "tech", "digital", "web"],
        "education": ["course", "training", "school", "learn", "university"],
        "real estate": ["property", "house", "apartment", "rent", "real estate"],
        "hospitality": ["hotel", "restaurant", "bar", "cafe", "catering"],
        "services": ["consulting", "agency", "design", "marketing", "business"]
    }
    for industry, keywords in industries.items():
        if any(kw in page_text for kw in keywords):
            return industry
    return "services"

def extract_cta(soup) -> str:
    cta_buttons = soup.find_all(['button', 'a'], limit=20)
    cta_keywords = ['contact', 'get started', 'sign up', 'buy', 'learn more', 'shop now', 'call']
    for btn in cta_buttons:
        text = btn.get_text().lower().strip()
        if any(kw in text for kw in cta_keywords):
            return btn.get_text().strip()[:50]
    return "Contact us today"
