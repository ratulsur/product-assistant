# scraper2.py
# Run:  python scraper2.py
# Deps (install into your venv):
#   python -m pip install requests beautifulsoup4 pandas gradio
# Optional for JS-rendered pages:
#   python -m pip install playwright
#   python -m playwright install chromium

from __future__ import annotations
import os
import re
import csv
import time
import tempfile
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import pandas as pd

import gradio as gr

# ---------- IMPORTANT COMPLIANCE GUARD ----------
# This app is for sites that PERMIT scraping.
# Myntra's Terms forbid automated scraping/crawling.
BLOCKED_HOSTS = {"myntra.com", "www.myntra.com"}

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
}

def make_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1.2,  # 0, 1.2, 2.4, 4.8, ...
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        raise_on_status=False,
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://", HTTPAdapter(max_retries=retries))
    return s

def domain_blocked(url: str) -> bool:
    host = urlparse(url).hostname or ""
    host = host.lower()
    return host.endswith("myntra.com")

def fetch_html(url: str, use_js: bool, network_timeout_read: int = 45) -> str:
    """
    Fetch page HTML. If use_js=True, try Playwright for JS-rendered pages.
    """
    if domain_blocked(url):
        raise ValueError(
            "This app blocks requests to 'myntra.com' to respect their Terms of Use. "
            "Please use a site that explicitly permits scraping (e.g., books.toscrape.com) "
            "or obtain official/API access."
        )

    if use_js:
        try:
            from playwright.sync_api import sync_playwright
        except Exception:
            raise RuntimeError(
                "Playwright is not installed. Install it via:\n"
                "  python -m pip install playwright\n"
                "  python -m playwright install chromium\n"
                "Or uncheck 'Render JavaScript' and try again."
            )
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()
            page.set_default_timeout(60000)  # 60s
            page.goto(url, wait_until="networkidle")
            html = page.content()
            browser.close()
            return html
    else:
        s = make_session()
        resp = s.get(url, headers=HEADERS, timeout=(10, network_timeout_read))
        resp.raise_for_status()
        return resp.text

def txt(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(strip=True)) if el else ""

def sel_one(root, selector: str):
    try:
        return root.select_one(selector) if selector else None
    except Exception:
        return None

def sel_all(root, selector: str):
    try:
        return root.select(selector) if selector else []
    except Exception:
        return []

def to_abs(url: str, base: str) -> str:
    if not url:
        return url
    return urljoin(base, url)

def clean_price(s: str) -> Optional[float]:
    if not s:
        return None
    m = re.search(r"(\d[\d,]*\.?\d*)", s.replace("\xa0", " "))
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except Exception:
        return None

def parse_products(
    page_url: str,
    html: str,
    selectors: Dict[str, str],
    max_items: int = 50,
) -> List[Dict[str, Optional[str]]]:
    """
    Generic parser using user-provided CSS selectors.
    selectors = {
        "card": "CSS for a product card (required)",
        "name": "CSS within card for product name/text",
        "price": "CSS within card for price",
        "image": "CSS within card for <img> (src)",
        "review": "CSS within card for review text/score (optional)",
        "link": "CSS within card for product link (href)",
    }
    """
    soup = BeautifulSoup(html, "html.parser")
    cards = sel_all(soup, selectors.get("card", ""))[:max_items]

    out: List[Dict[str, Optional[str]]] = []
    for c in cards:
        name_el = sel_one(c, selectors.get("name", ""))
        price_el = sel_one(c, selectors.get("price", ""))
        image_el = sel_one(c, selectors.get("image", ""))
        review_el = sel_one(c, selectors.get("review", ""))
        link_el = sel_one(c, selectors.get("link", ""))

        name = txt(name_el)
        price_raw = txt(price_el)
        price_val = clean_price(price_raw)
        image_url = None
        if image_el:
            # prefer src, fallback to data-src
            image_url = image_el.get("src") or image_el.get("data-src") or image_el.get("data-original")
            image_url = to_abs(image_url, page_url)
        review = txt(review_el) if review_el else None
        product_url = to_abs(link_el.get("href"), page_url) if link_el and link_el.has_attr("href") else None

        out.append(
            {
                "product_name": name or None,
                "price_text": price_raw or None,
                "price_value": price_val,
                "image_url": image_url,
                "review": review,
                "product_url": product_url,
            }
        )
    return out

def scrape_once(
    url: str,
    use_js: bool,
    selectors: Dict[str, str],
    max_items: int = 50,
) -> pd.DataFrame:
    html = fetch_html(url, use_js=use_js, network_timeout_read=60)
    rows = parse_products(url, html, selectors, max_items=max_items)
    df = pd.DataFrame(rows)
    # light cleanup for display
    return df

def make_csv(df: pd.DataFrame) -> str:
    tmpdir = tempfile.mkdtemp(prefix="scrape_")
    path = os.path.join(tmpdir, "products.csv")
    df.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL)
    return path

# Default selectors (WORKING EXAMPLE for https://books.toscrape.com)
DEFAULT_SELECTORS = {
    "card": "ol.row li",                    # product card
    "name": "h3 a",                         # anchor text is the title
    "price": ".price_color",                # price text
    "image": ".image_container img",        # <img src=...>
    "review": "p.star-rating",              # class indicates rating
    "link": "h3 a",                         # product detail link
}

# --------- Gradio App ---------
def do_scrape(
    url: str,
    use_js: bool,
    max_items: int,
    card_css: str,
    name_css: str,
    price_css: str,
    image_css: str,
    review_css: str,
    link_css: str,
):
    if not url or not url.strip():
        return gr.Update(), None, "Please provide a URL."

    try:
        selectors = {
            "card": card_css.strip(),
            "name": name_css.strip(),
            "price": price_css.strip(),
            "image": image_css.strip(),
            "review": review_css.strip(),
            "link": link_css.strip(),
        }
        df = scrape_once(url.strip(), use_js=use_js, selectors=selectors, max_items=int(max_items or 50))
        if df.empty:
            return df, None, "No products found with the given selectors. Try adjusting them."
        csv_path = make_csv(df)
        msg = f"Scraped {len(df)} rows. CSV is ready."
        return df.head(50), csv_path, msg
    except Exception as e:
        return gr.Update(), None, f"Error: {e}"

with gr.Blocks(css="""
#note {font-size: 0.95rem;}
.small { font-size: 0.9rem; color: #444; }
""") as demo:
    gr.Markdown("## Generic Product Scraper (for permitted sites)")
    gr.Markdown(
        "<div id='note'>"
        "<b>Use only on sites that allow scraping.</b> "
        "This app blocks <code>myntra.com</code> to respect their Terms. "
        "Test with <a href='https://books.toscrape.com' target='_blank'>books.toscrape.com</a>.</div>",
        elem_id="note"
    )

    with gr.Row():
        url_in = gr.Textbox(label="Listing URL", placeholder="https://books.toscrape.com/catalogue/category/books_1/index.html")
    with gr.Row():
        use_js_in = gr.Checkbox(label="Render JavaScript (Playwright)", value=False)
        max_items_in = gr.Number(label="Max products", value=50, precision=0)

    with gr.Accordion("Advanced: CSS selectors", open=False):
        card_css_in = gr.Textbox(label="Product card CSS", value=DEFAULT_SELECTORS["card"])
        name_css_in = gr.Textbox(label="Name CSS", value=DEFAULT_SELECTORS["name"])
        price_css_in = gr.Textbox(label="Price CSS", value=DEFAULT_SELECTORS["price"])
        image_css_in = gr.Textbox(label="Image CSS", value=DEFAULT_SELECTORS["image"])
        review_css_in = gr.Textbox(label="Review CSS (optional)", value=DEFAULT_SELECTORS["review"])
        link_css_in = gr.Textbox(label="Product link CSS (optional)", value=DEFAULT_SELECTORS["link"])

    run_btn = gr.Button("Scrape")
    out_df = gr.Dataframe(interactive=False, label="Preview (up to 50 rows)")
    out_file = gr.File(label="Download CSV")
    out_msg = gr.Markdown("", elem_classes=["small"])

    run_btn.click(
        fn=do_scrape,
        inputs=[
            url_in, use_js_in, max_items_in,
            card_css_in, name_css_in, price_css_in, image_css_in, review_css_in, link_css_in
        ],
        outputs=[out_df, out_file, out_msg]
    )

if __name__ == "__main__":
    # If your venv was created without pip, fix with:
    #   python -m ensurepip --upgrade
    #   python -m pip install --upgrade pip
    #   python -m pip install requests beautifulsoup4 pandas gradio
    demo.launch()
