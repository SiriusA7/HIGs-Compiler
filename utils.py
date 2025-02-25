import os
import re
import time
import hashlib

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

def create_index_html(sections_info):
    """Create an HTML index page with links."""
    index_html = """
    <html>
    <head>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 2cm; }
            h1 { color: #333; margin-bottom: 1cm; }
            .toc { margin-top: 1cm; }
            .toc-item { 
                margin: 0.5cm 0;
                color: #333;
                text-decoration: none;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .toc-item span { color: #666; }
        </style>
    </head>
    <body>
        <h1>Apple Human Interface Guidelines</h1>
        <div class="toc">
    """
    
    for title, page_num in sections_info:
        index_html += f"""
            <div class="toc-item">
                <a href="#{page_num}">{title}</a>
                <span>{page_num}</span>
            </div>
        """
    
    index_html += """
        </div>
    </body>
    </html>
    """
    return index_html
