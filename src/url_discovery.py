from playwright.sync_api import sync_playwright
from urllib.parse import urljoin, urlparse

def get_article_urls():
    """Get unique article URLs, removing duplicates"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto(
                "https://developer.apple.com/design/human-interface-guidelines/",
                wait_until="networkidle",
                timeout=60000
            )
            
            if not page.title().startswith("Human Interface Guidelines"):
                raise Exception("Failed to load HIG main page")
            
            links = page.query_selector_all('a[href*="/design/human-interface-guidelines/"]')
            print(f"Initial links found: {len(links)}")
            
            base_url = "https://developer.apple.com"
            articles = set()
            seen_paths = set()
            
            for link in links:
                href = link.get_attribute("href")
                full_url = urljoin(base_url, href)
                parsed = urlparse(full_url)
                path = parsed.path.rstrip('/')
                
                if "/design/human-interface-guidelines/" in full_url and path not in seen_paths:
                    seen_paths.add(path)
                    articles.add(full_url)
                    print(f"Added unique URL: {full_url}")
            
            print(f"Found {len(articles)} unique articles after deduplication")
            return sorted(articles)
            
        finally:
            browser.close()
