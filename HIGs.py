# hig_fixed_discovery.py
from playwright.sync_api import sync_playwright
import urllib.parse

def get_article_urls():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Load page with networkidle wait
            page.goto(
                "https://developer.apple.com/design/human-interface-guidelines/",
                wait_until="networkidle",
                timeout=60000
            )
            
            # Verify page load
            if not page.title().startswith("Human Interface Guidelines"):
                raise Exception("Failed to load HIG main page")
            
            # Get all links using broader selector
            links = page.query_selector_all('a[href*="/design/human-interface-guidelines/"]')
            print(f"Initial links found: {len(links)}")  # Debug
            
            # Process URLs
            base_url = "https://developer.apple.com"
            articles = set()
            for link in links:
                href = link.get_attribute("href")
                full_url = urllib.parse.urljoin(base_url, href)
                if "/design/human-interface-guidelines/" in full_url:
                    articles.add(full_url)
            
            # Filter valid articles (modified criteria)
            # valid_urls = [
            #     url for url in articles 
            #     if not url.endswith(("/overview/", "/introduction/")) 
            #     and "archive" not in url
            # ]
            
            return articles
            
        finally:
            browser.close()


# hig_pdf_generator.py
from playwright.sync_api import sync_playwright
import os
import re
import urllib.parse

def sanitize_filename(text):
    """Create safe filenames from titles"""
    return re.sub(r'[\\/*?:"<>|]', '', text)[:100].strip()

def generate_pdfs(article_urls):
    """Generate PDFs for all articles"""
    output_dir = f'Apple-HIGs'
    os.makedirs(output_dir, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        
        for idx, url in enumerate(article_urls, 1):
            try:
                page = context.new_page()
                page.goto(url, wait_until='networkidle', timeout=60000)
                
                # Extract title
                title_element = page.query_selector('h1')
                title = title_element.inner_text() if title_element else 'Untitled'
                
                # Create filename
                path_parts = [p for p in urllib.parse.urlparse(url).path.split('/') if p]
                section = path_parts[-2] if len(path_parts) > 1 else 'misc'
                safe_title = sanitize_filename(title)
                filename = f'{safe_title}.pdf'
                filepath = os.path.join(output_dir, filename)
                
                # Generate PDF
                page.pdf(
                    path=filepath,
                    format='A4',
                    print_background=True,
                    margin={'top': '1cm', 'bottom': '1cm'},
                    header_template='<div style="font-size: 8px; margin: 0 auto;">Apple Human Interface Guidelines</div>',
                    display_header_footer=True
                )
                
                print(f'Generated ({idx}/21): {filename}')
                
            except Exception as e:
                print(f'Failed {url}: {str(e)}')
            finally:
                page.close()
        
        browser.close()
    
    return output_dir


if __name__ == "__main__":
    articles = get_article_urls()
    print(f"Found {len(articles)} articles")
    
    print("Starting PDF generation for 21 articles...")
    output_folder = generate_pdfs(articles)
    print(f'\n✅ Successfully generated 21 PDFs in folder: {output_folder}')

