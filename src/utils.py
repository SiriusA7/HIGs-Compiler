import os
import re
import time
import hashlib
from datetime import datetime
from PyPDF2 import PdfReader

def sanitize_filename(text):
    """Create safe filenames from titles"""
    return re.sub(r'[\\/*?:"<>|]', '', text)[:100].strip()

def get_unique_filename(output_dir, base_name):
    """Create a unique filename using timestamp and hash if needed."""
    base, ext = os.path.splitext(base_name)
    timestamp = int(time.time() * 1000)
    counter = 0
    
    while True:
        if counter == 0:
            filename = f"{base}_{timestamp}{ext}"
        else:
            filename = f"{base}_{timestamp}_{counter}{ext}"
            
        filepath = os.path.join(output_dir, filename)
        if not os.path.exists(filepath):
            return filepath
        counter += 1

def calculate_content_hash(page):
    """Calculate hash of page content for duplicate detection"""
    content = page.evaluate("""() => {
        const main = document.querySelector('main') || document.body;
        const clone = main.cloneNode(true);
        const dynamics = clone.querySelectorAll('[data-dynamic], .timestamp, time');
        dynamics.forEach(el => el.remove());
        return clone.textContent;
    }""")
    return hashlib.md5(content.encode()).hexdigest()

def get_pdf_page_count(pdf_path):
    """Get the number of pages in a PDF file"""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PdfReader(file)
            return len(reader.pages)
    except Exception as e:
        print(f"Error getting page count for {pdf_path}: {str(e)}")
        return 0

def create_index_html(sections, generated_files_map, cover_page_count):
    """Create index page HTML preserving the given order for sections and sub-sections.

    We estimate the number of index pages for page number calculation and then
    assign page numbers in the same order the content will be merged.
    """

    # Start after the cover
    current_page = cover_page_count

    # Estimate index length to offset article page numbers correctly
    total_articles = sum(
        len(s.get("articles", [])) + sum(len(ss.get("articles", [])) for ss in s.get("sub_sections", []))
        for s in sections
    )
    estimated_index_pages = max(1, (total_articles // 45) + 1)
    current_page += estimated_index_pages

    # Assign page numbers in merge order
    processed_urls = set()
    for section in sections:
        for article in section.get("articles", []):
            if article["url"] in processed_urls:
                continue
            filepath, page_count = generated_files_map.get(article["url"], (None, 0))
            if filepath:
                article["page_num"] = current_page
                current_page += page_count
                processed_urls.add(article["url"])
        for sub_section in section.get("sub_sections", []):
            for article in sub_section.get("articles", []):
                if article["url"] in processed_urls:
                    continue
                filepath, page_count = generated_files_map.get(article["url"], (None, 0))
                if filepath:
                    article["page_num"] = current_page
                    current_page += page_count
                    processed_urls.add(article["url"])

    # Generate HTML (preserve order; no alphabetical sorting)
    items_html = ""
    for section in sections:
        items_html += f'<li class="section-title">{section["title"]}</li>'

        for article in section.get("articles", []):
            items_html += (
                f'<li><a href="#"><span class="title">{article["title"]}</span>'
                f'<span class="page">{article.get("page_num", "")}</span></a></li>'
            )

        if section.get("sub_sections"):
            items_html += '<ul class="sub-section">'
            for sub_section in section["sub_sections"]:
                items_html += f'<li class="sub-section-title">{sub_section["title"]}</li>'
                for article in sub_section["articles"]:
                    items_html += (
                        f'<li><a href="#"><span class="title">{article["title"]}</span>'
                        f'<span class="page">{article.get("page_num", "")}</span></a></li>'
                    )
            items_html += '</ul>'

    html = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Icons", sans-serif;
                    padding: 48px;
                    max-width: 980px;
                    margin: 0 auto;
                    color: #1d1d1f;
                }}
                h1 {{
                    font-size: 40px;
                    font-weight: 600;
                    letter-spacing: -0.003em;
                    margin-bottom: 40px;
                }}
                ul {{
                    list-style: none;
                    padding: 0;
                    margin: 0;
                }}
                li {{
                    border-bottom: 1px solid #d2d2d7;
                }}
                li.section-title {{
                    font-size: 24px;
                    font-weight: 600;
                    padding-top: 24px;
                    padding-bottom: 8px;
                    border-bottom: none;
                }}
                .sub-section {{
                    padding-left: 20px;
                    border-top: 1px solid #d2d2d7;
                    margin-top: 8px;
                }}
                .sub-section-title {{
                    font-size: 19px;
                    font-weight: 500;
                    padding-top: 16px;
                    padding-bottom: 8px;
                    border-bottom: none;
                }}
                a {{
                    text-decoration: none;
                    color: inherit;
                    padding: 12px 0;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                a:hover {{ color: #06c; }}
                .title {{ font-size: 17px; letter-spacing: -0.022em; }}
                .page {{ color: #86868b; font-size: 15px; font-weight: 400; }}
            </style>
        </head>
        <body>
            <h1>Contents</h1>
            <ul>{items_html}</ul>
        </body>
        </html>
    """
    return html, sections

def create_cover_html():
    """Create a minimalist cover page"""
    return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    margin: 0;
                    padding: 40px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                }}
                .cover {{ text-align: center; max-width: 800px; }}
                h1 {{
                    font-size: 48px;
                    font-weight: 500;
                    margin: 0 0 2rem;
                    color: #1d1d1f;
                }}
                .subtitle {{
                    font-size: 24px;
                    font-weight: 300;
                    color: #86868b;
                    margin: 0;
                }}
            </style>
        </head>
        <body>
            <div class="cover">
                <h1>Human Interface Guidelines</h1>
                <p class="subtitle">A comprehensive guide for designing<br>intuitive user experiences</p>
            </div>
        </body>
        </html>
    """
