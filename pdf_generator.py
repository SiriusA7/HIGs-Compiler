from playwright.sync_api import sync_playwright
import urllib.parse
import os
from utils import sanitize_filename, get_unique_filename, calculate_content_hash, create_index_html

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

def generate_pdfs(article_urls):
    """Generate PDFs for all articles, skipping duplicates"""
    output_dir = f'Apple-HIGs'
    os.makedirs(output_dir, exist_ok=True)
    generated_files = []
    titles = []
    content_hashes = set()
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        
        # Generate PDFs for articles
        for idx, url in enumerate(article_urls, 1):
            try:
                page = context.new_page()
                page.goto(url, wait_until='networkidle', timeout=60000)
                
                content_hash = calculate_content_hash(page)
                if content_hash in content_hashes:
                    print(f"Skipping duplicate content: {url}")
                    continue
                    
                content_hashes.add(content_hash)
                
                try:
                    page.evaluate(add_page_break_script())
                except Exception as e:
                    print(f"Warning: Could not apply image pagination for {url}: {str(e)}")
                
                try:
                    page.wait_for_selector('img', state='attached', timeout=5000)
                except:
                    print(f"Warning: No images found or timeout waiting for images in {url}")
                
                title_element = page.query_selector('h1')
                title = title_element.inner_text() if title_element else 'Untitled'
                titles.append(title)
                
                path_parts = [p for p in urllib.parse.urlparse(url).path.split('/') if p]
                section = path_parts[-2] if len(path_parts) > 1 else 'misc'
                safe_title = sanitize_filename(f"{section}-{title}")
                filepath = get_unique_filename(output_dir, f"{safe_title}.pdf")
                
                page.pdf(
                    path=filepath,
                    format='A4',
                    print_background=True,
                    margin={'top': '1cm', 'bottom': '1cm', 'left': '1cm', 'right': '1cm'},
                    display_header_footer=False
                )
                
                generated_files.append(filepath)
                print(f'Generated ({idx}/{len(article_urls)}): {os.path.basename(filepath)}')
                
            except Exception as e:
                print(f'Failed {url}: {str(e)}')
            finally:
                page.close()
        
        # Create index
        sections_info = [(title, i+1) for i, title in enumerate(titles)]
        index_html = create_index_html(sections_info)
        index_file = os.path.join(output_dir, "_index.pdf")
        
        index_page = context.new_page()
        index_page.set_content(index_html)
        index_page.pdf(
            path=index_file,
            format='A4',
            print_background=True,
            margin={'top': '1cm', 'bottom': '1cm', 'left': '1cm', 'right': '1cm'},
        )
        index_page.close()
        
        generated_files.insert(0, index_file)
        browser.close()
    
    return output_dir, generated_files, sections_info
