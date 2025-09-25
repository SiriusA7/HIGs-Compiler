from playwright.sync_api import sync_playwright
import urllib.parse
import os
from src.utils import (
    sanitize_filename, get_unique_filename, calculate_content_hash,
    create_index_html, get_pdf_page_count, create_cover_html
)

def add_page_break_script():
    """JavaScript to handle image pagination and section breaks"""
    return """
        // Handle images and their captions
        function wrapImageWithCaption(img) {
            const wrapper = document.createElement('div');
            wrapper.style.pageBreakInside = 'avoid';
            wrapper.style.breakInside = 'avoid';
            wrapper.style.margin = '1em 0';
            wrapper.style.display = 'flex';
            wrapper.style.flexDirection = 'column';

            // Find related caption
            let caption = img.closest('figure')?.querySelector('figcaption') ||
                         (img.nextElementSibling?.matches('.caption, [class*="caption"], p[class*="caption"]') 
                            ? img.nextElementSibling : null) ||
                         img.closest('dt')?.nextElementSibling;

            // Get the container that holds both image and caption
            const container = img.closest('figure') || img.parentElement;
            
            if (container) {
                container.style.pageBreakInside = 'avoid';
                container.style.breakInside = 'avoid';
                
                if (!container.parentElement?.hasAttribute('data-image-wrapper')) {
                    wrapper.setAttribute('data-image-wrapper', 'true');
                    container.parentNode.insertBefore(wrapper, container);
                    wrapper.appendChild(container);
                }
            } else {
                wrapper.setAttribute('data-image-wrapper', 'true');
                img.parentNode.insertBefore(wrapper, img);
                wrapper.appendChild(img);
                if (caption) wrapper.appendChild(caption);
            }
        }

        // Handle Resources and Change Log sections
        function handleSpecialSections() {
            const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6'));
            
            const resourcesHeading = headings.find(h => 
                h.textContent.toLowerCase().includes('resource') ||
                h.textContent.toLowerCase().includes('related') ||
                h.textContent.toLowerCase().includes('see also')
            );

            if (resourcesHeading) {
                // Create resources wrapper with page break
                const wrapper = document.createElement('div');
                wrapper.style.pageBreakBefore = 'always';
                wrapper.style.breakBefore = 'page';
                
                // Get all content until next major heading or end
                const content = [];
                let current = resourcesHeading;
                
                while (current) {
                    const next = current.nextElementSibling;
                    if (next && next.matches('h1')) break;
                    content.push(current);
                    current = next;
                }

                // Move content to wrapper
                resourcesHeading.parentNode.insertBefore(wrapper, resourcesHeading);
                content.forEach(node => wrapper.appendChild(node));
            }
        }

        // Process images first
        document.querySelectorAll('img, [role="img"], svg').forEach(wrapImageWithCaption);
        document.querySelectorAll('.graphics-container, [class*="figure"], [class*="image"]').forEach(container => {
            container.style.pageBreakInside = 'avoid';
            container.style.breakInside = 'avoid';
        });

        // Then handle special sections
        handleSpecialSections();
    """

def generate_pdfs(sections):
    """Generate PDFs for all articles, based on the hierarchical section data."""
    output_dir = 'Apple-HIGs'
    os.makedirs(output_dir, exist_ok=True)
    
    all_articles = []
    # Flatten the sections structure to a list of articles for processing (preserve given order)
    for section in sections:
        for a in section.get("articles", []):
            all_articles.append(a)
        for sub_section in section.get("sub_sections", []):
            for a in sub_section.get("articles", []):
                all_articles.append(a)

    generated_files_map = {}  # url -> (filepath, page_count)
    hash_to_file = {}  # content_hash -> (filepath, page_count)
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={'width': 1200, 'height': 800},
            forced_colors='none'
        )
        
        # Generate PDFs for all unique articles
        for idx, article in enumerate(all_articles, 1):
            url = article["url"]
            title = article["title"]
            
            try:
                page = context.new_page()
                page.goto(url, wait_until='networkidle', timeout=60000)
                
                content_hash = calculate_content_hash(page)
                if content_hash in hash_to_file:
                    # Duplicate content: reuse existing file and page count
                    existing_file, page_count = hash_to_file[content_hash]
                    generated_files_map[url] = (existing_file, page_count)
                    print(f"Skipping duplicate content (reused): {url}")
                    continue
                
                try:
                    page.evaluate(add_page_break_script())
                except Exception as e:
                    print(f"Warning: Could not apply image pagination for {url}: {str(e)}")
                
                try:
                    page.wait_for_selector('img', state='attached', timeout=15000)
                except:
                    print(f"Warning: No images found or timeout waiting for images in {url}")
                
                path_parts = [p for p in urllib.parse.urlparse(url).path.split('/') if p]
                # Build a descriptive but safe filename using last 2 segments to reduce collisions
                tail = "-".join(path_parts[-2:]) if len(path_parts) >= 2 else (path_parts[-1] if path_parts else 'article')
                safe_title = sanitize_filename(f"human-interface-guidelines-{tail}-{title}")
                filepath = get_unique_filename(output_dir, f"{safe_title}.pdf")
                
                pdf_options = {
                    'path': filepath,
                    'format': 'A4',
                    'print_background': True,
                    'margin': {'top': '1cm', 'bottom': '1cm', 'left': '1cm', 'right': '1cm'},
                    'display_header_footer': False
                }
                
                page.pdf(**pdf_options)
                
                page_count = get_pdf_page_count(filepath)
                generated_files_map[url] = (filepath, page_count)
                hash_to_file[content_hash] = (filepath, page_count)
                print(f'Generated ({idx}/{len(all_articles)}): {os.path.basename(filepath)} - {page_count} pages')
                
            except Exception as e:
                print(f'Failed {url}: {str(e)}')
            finally:
                if 'page' in locals() and not page.is_closed():
                    page.close()
        
        # --- Create Cover and Index ---
        # Generate cover page
        cover_page = context.new_page()
        cover_html = create_cover_html()
        cover_page.set_content(cover_html)
        cover_file = os.path.join(output_dir, "_cover.pdf")
        cover_page.pdf(path=cover_file, format='A4', print_background=True, margin={'top': '1cm', 'bottom': '1cm', 'left': '1cm', 'right': '1cm'})
        cover_page.close()
        cover_page_count = get_pdf_page_count(cover_file)

        # Create index
        index_html, sections_info_for_index = create_index_html(sections, generated_files_map, cover_page_count)
        index_file = os.path.join(output_dir, "_index.pdf")
        index_page = context.new_page()
        index_page.set_content(index_html)
        index_page.pdf(path=index_file, format='A4', print_background=True, margin={'top': '1cm', 'bottom': '1cm', 'left': '1cm', 'right': '1cm'})
        index_page.close()
        
        browser.close()
        
        return (output_dir, sections, generated_files_map, cover_file, index_file)
