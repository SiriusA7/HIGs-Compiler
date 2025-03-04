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

def create_index_html(sections_info):
    """Create index page HTML with Apple-style design"""
    items = '\n'.join([
        f'<li><a href="#{idx}"><span class="title">{title}</span>'
        f'<span class="page">{page}</span></a></li>'
        for idx, (title, page) in enumerate(sections_info, 1)
    ])
    
    return f"""
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
                    border-top: 1px solid #d2d2d7;
                }}
                li {{
                    border-bottom: 1px solid #d2d2d7;
                }}
                a {{
                    text-decoration: none;
                    color: inherit;
                    padding: 12px 0;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                a:hover {{
                    color: #06c;
                }}
                .title {{
                    font-size: 17px;
                    letter-spacing: -0.022em;
                }}
                .page {{
                    color: #86868b;
                    font-size: 15px;
                    font-weight: 400;
                }}
            </style>
        </head>
        <body>
            <h1>Contents</h1>
            <ul>{items}</ul>
        </body>
        </html>
    """

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
