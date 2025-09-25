import os
import re
import json
import hashlib
from datetime import datetime
from urllib.parse import urlparse, urljoin
from typing import Optional
import mimetypes

import requests

from playwright.sync_api import sync_playwright
from markdownify import markdownify as md


def slugify(text: str) -> str:
    text = re.sub(r"[\s_]+", "-", text.strip().lower())
    text = re.sub(r"[^a-z0-9\-]", "", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-") or "untitled"


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def hash_text(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def html_to_markdown(html: str) -> str:
    # Convert HTML to Markdown with sane defaults for docs
    return md(
        html,
        strip=['script', 'style', 'noscript'],
        heading_style="ATX",
        bullets="-",
        escape_asterisks=False,
    )


def extract_main_html(page) -> str:
    """Extract the main content HTML from the page using client-side DOM.

    We prefer the <main> element; fallback to a best-effort content container.
    """
    try:
        html = page.evaluate(
            """
            () => {
                const pick = () => {
                    const main = document.querySelector('main');
                    if (main) return main.cloneNode(true);
                    // Fall back to primary content containers
                    const candidates = [
                        '#main', '.main', '#content', '.content', 'article',
                        '[role="main"]', 'div[aria-label*="content" i]'
                    ];
                    for (const sel of candidates) {
                        const el = document.querySelector(sel);
                        if (el) return el.cloneNode(true);
                    }
                    return document.body.cloneNode(true);
                };

                const root = pick();
                // Remove navigation, footers, asides, and non-essential UI
                root.querySelectorAll('nav, footer, aside, header .breadcrumbs, script, style, noscript').forEach(el => el.remove());
                // Remove share widgets and extraneous controls
                root.querySelectorAll('[class*="share" i], [data-social], [aria-label*="share" i]').forEach(el => el.remove());
                // Normalize image lazy attributes
                root.querySelectorAll('img[loading], img[data-src], img[srcset]').forEach(img => { img.removeAttribute('loading'); img.removeAttribute('srcset'); });
                return root.innerHTML;
            }
            """
        )
        return html or ""
    except Exception:
        try:
            return page.content()
        except Exception:
            return ""


def write_markdown_file(base_dir: str, section: str, sub_section: Optional[str], title: str, url: str, markdown: str):
    sec_slug = slugify(section)
    sub_slug = slugify(sub_section) if sub_section else None
    art_slug = slugify(title)

    dir_path = os.path.join(base_dir, sec_slug, sub_slug) if sub_slug else os.path.join(base_dir, sec_slug)
    ensure_dir(dir_path)

    file_path = os.path.join(dir_path, f"{art_slug}.md")

    frontmatter = {
        "title": title,
        "apple_url": url,
        "section": section,
        "sub_section": sub_section or None,
        "slug": art_slug,
        "source": "Apple Human Interface Guidelines",
        "fetched_at": datetime.utcnow().isoformat() + "Z",
    }

    content = "---\n" + "\n".join(f"{k}: {json.dumps(v)}" for k, v in frontmatter.items()) + "\n---\n\n" + markdown

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return file_path, frontmatter


def create_summary_and_manifest(base_dir: str, manifest_items: list):
    # Sort manifest by section/sub/title for stable browsing
    manifest_items.sort(key=lambda x: (x.get("section", ""), x.get("sub_section", ""), x.get("title", "")))

    # Write manifest.json
    with open(os.path.join(base_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest_items, f, indent=2, ensure_ascii=False)

    # Write SUMMARY.md (MkDocs/GitBook style)
    lines = ["# Summary", ""]
    current_sec = None
    current_sub = None
    for item in manifest_items:
        sec = item["section"]
        sub = item.get("sub_section")
        rel = item["relative_path"].replace(base_dir + os.sep, "")
        if sec != current_sec:
            lines.append(f"- {sec}")
            current_sec = sec
            current_sub = None
        if sub and sub != current_sub:
            lines.append(f"  - {sub}")
            current_sub = sub
        indent = "    " if sub else "  "
        lines.append(f"{indent}- [{item['title']}]({rel})")

    with open(os.path.join(base_dir, "SUMMARY.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def export_markdown(sections: list, output_dir: str = "Apple-HIGs-md") -> str:
    """Export the discovered sections into a hierarchy of Markdown files with frontmatter.

    Returns the root output directory path.
    """
    ensure_dir(output_dir)

    # Flatten unique articles preserving order
    articles = []
    for section in sections:
        sec_title = section.get("title")
        for a in section.get("articles", []):
            articles.append((sec_title, None, a))
        for sub in section.get("sub_sections", []):
            for a in sub.get("articles", []):
                articles.append((sec_title, sub.get("title"), a))

    url_seen = set()
    manifest = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1200, 'height': 800}, forced_colors='none')

        for idx, (sec, sub, art) in enumerate(articles, 1):
            page = None
            url = art.get("url")
            title = art.get("title")
            if not url or url in url_seen:
                continue
            url_seen.add(url)

            try:
                page = context.new_page()
                page.goto(url, wait_until='networkidle', timeout=60000)

                # Prefer the main element's HTML
                html = extract_main_html(page)

                # Prepare article directory (where the .md will live) for relative asset paths
                sec_slug = slugify(sec)
                sub_slug = slugify(sub) if sub else None
                art_slug = slugify(title)
                article_dir = os.path.join(output_dir, sec_slug, sub_slug) if sub_slug else os.path.join(output_dir, sec_slug)
                ensure_dir(article_dir)

                # Download and rewrite image sources for fully offline media
                html_offline = rewrite_and_cache_images(html, url, article_dir, art_slug)

                markdown = html_to_markdown(html_offline)

                # Lightweight de-duplication by content hash
                content_hash = hash_text(markdown)

                file_path, fm = write_markdown_file(output_dir, sec, sub, title, url, markdown)

                manifest.append({
                    **fm,
                    "relative_path": file_path,
                    "bytes": os.path.getsize(file_path),
                    "content_hash": content_hash,
                })

                print(f"MD ({idx}/{len(articles)}): {title}")
            except Exception as e:
                print(f"Failed MD export: {url} -> {e}")
            finally:
                try:
                    # Only attempt close if page exists and has the method
                    if page is not None and hasattr(page, 'is_closed') and not page.is_closed():
                        page.close()
                except Exception:
                    pass

        browser.close()

    # Create top-level README and indices
    with open(os.path.join(output_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(
            """
            # Apple Human Interface Guidelines (Markdown Export)

            This folder contains a local, hierarchical Markdown export of the Apple HIG.

            - One file per article, with YAML frontmatter containing section metadata.
            - Organized by Section/Sub-section/Article.md to keep files small and indexable.
            - See `SUMMARY.md` for a clickable outline and `manifest.json` for programmatic indexing.
            """.strip()
        )

    create_summary_and_manifest(output_dir, manifest)

    return output_dir


# --- Offline media helpers ---
def _infer_ext(url: str, content_type: Optional[str]) -> str:
    # Try URL path ext first
    path = urlparse(url).path
    _, ext = os.path.splitext(path)
    ext = (ext or '').lower()
    if ext in {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg', '.tif', '.tiff'}:
        return ext
    # Try MIME type
    if content_type:
        guess = mimetypes.guess_extension(content_type.split(';')[0].strip())
        if guess:
            return guess
    # Default
    return '.png'


def _download_image(abs_url: str, out_dir: str, name_seed: str, referer: Optional[str]) -> Optional[str]:
    ensure_dir(out_dir)
    h = hashlib.sha1(f"{name_seed}:{abs_url}".encode('utf-8')).hexdigest()[:16]
    # Head request to get content-type quickly (fallback to get if head fails)
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari',
        'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
    }
    if referer:
        headers['Referer'] = referer

    try:
        r = requests.get(abs_url, headers=headers, timeout=20, stream=True)
        r.raise_for_status()
        ext = _infer_ext(abs_url, r.headers.get('Content-Type'))
        fname = f"{h}{ext}"
        fpath = os.path.join(out_dir, fname)
        with open(fpath, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return fpath
    except Exception:
        return None


def rewrite_and_cache_images(html: str, page_url: str, article_dir: str, article_slug: str) -> str:
    """Download images referenced in HTML and rewrite their src to local relative paths."""
    img_dir = os.path.join(article_dir, "_assets", article_slug)
    ensure_dir(img_dir)

    # Find all image sources
    pattern = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
    seen = {}

    def repl(match):
        src = match.group(1)
        # Skip data URIs (already embedded)
        if src.startswith('data:'):
            return match.group(0)
        # Resolve absolute URL
        abs_url = urljoin(page_url, src)
        if abs_url in seen:
            local_rel = seen[abs_url]
        else:
            local_abs = _download_image(abs_url, img_dir, article_slug, referer=page_url)
            if not local_abs:
                return match.group(0)  # leave original src
            local_rel = os.path.relpath(local_abs, start=article_dir)
            seen[abs_url] = local_rel
        # Replace only the src attribute value inside the matched tag
        tag = match.group(0)
        new_tag = tag.replace(src, local_rel)
        return new_tag

    new_html = pattern.sub(repl, html)
    return new_html
