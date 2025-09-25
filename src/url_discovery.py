from playwright.sync_api import sync_playwright, Page
from urllib.parse import urljoin


def get_article_urls():
    """
    Discover all HIG article URLs by fully expanding and scrolling the virtualized
    navigation, then organize them to mirror the site's hierarchy and order.

    Returns: List[{
      title: str,
      articles: List[{title, url}],
      sub_sections: List[{title, articles: List[{title, url}]}]
    }]
    """
    start_url = "https://developer.apple.com/design/human-interface-guidelines/"
    base_url = "https://developer.apple.com"

    # Desired top-level order as shown in the site's Topics section
    TOP_LEVEL_ORDER = [
        "Getting Started",
        "Foundations",
        "Patterns",
        "Components",
        "Inputs",
        "Technologies",
    ]

    # Desired Components sub-section order
    COMPONENTS_ORDER = [
        "Content",
        "Layout and Organization",
        "Menus and Actions",
        "Navigation and Search",
        "Presentation",
        "Selection and Input",
        "Status",
        "System Experiences",
    ]

    slug_to_top = {
        "getting-started": "Getting Started",
        "foundations": "Foundations",
        "patterns": "Patterns",
        "components": "Components",
        "inputs": "Inputs",
        "technologies": "Technologies",
    }

    comp_slug_to_name = {
        "content": "Content",
        "layout-and-organization": "Layout and Organization",
        "menus-and-actions": "Menus and Actions",
        "navigation-and-search": "Navigation and Search",
        "presentation": "Presentation",
        "selection-and-input": "Selection and Input",
        "status": "Status",
        "system-experiences": "System Experiences",
    }

    sections_map = {}
    discovered_links = []  # preserve DOM order
    seen_hrefs = set()

    def ensure_section(name: str):
        if name not in sections_map:
            sections_map[name] = {"title": name, "articles": [], "_sub_map": {}, "sub_sections": []}
        return sections_map[name]

    def add_article(section_name: str, title: str, url: str):
        section = ensure_section(section_name)
        section["articles"].append({"title": title, "url": url})

    def add_sub_article(section_name: str, sub_name: str, title: str, url: str):
        section = ensure_section(section_name)
        if sub_name not in section["_sub_map"]:
            section["_sub_map"][sub_name] = []
        section["_sub_map"][sub_name].append({"title": title, "url": url})

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            print(f"Loading main navigation page: {start_url}")
            page.goto(start_url, wait_until="networkidle", timeout=90000)

            if "Human Interface Guidelines" not in page.title():
                raise Exception("Failed to load HIG main page")

            # Try to locate navigation sidebar; not fatal if not present or fails
            navigator = None
            try:
                navigator = page.wait_for_selector("nav.navigator", state="visible", timeout=20000)
            except Exception:
                navigator = None

            # Helper: scroll through the virtualized navigator and expand all toggles
            def crawl_nav():
                nonlocal discovered_links, seen_hrefs

                # Function runs a full top->bottom pass while expanding as it goes
                def run_pass(direction: str = "down"):
                    # Reset to edge
                    if direction == "down":
                        navigator.evaluate("(el) => { el.scrollTo(0, 0); }")
                    else:
                        # Go to bottom first for the upward pass
                        navigator.evaluate("(el) => { el.scrollTo(0, el.scrollHeight); }")

                    last_count = len(discovered_links)
                    stable_steps = 0
                    for _ in range(400):  # generous upper bound
                        # Expand visible toggles
                        toggles = navigator.query_selector_all('[aria-expanded="false"]')
                        for btn in toggles or []:
                            try:
                                btn.click()
                                page.wait_for_timeout(60)
                            except Exception:
                                pass

                        # Collect currently rendered links in order
                        links = navigator.query_selector_all('a[href^="/design/human-interface-guidelines/"]') or []
                        for link in links:
                            href = link.get_attribute("href")
                            if not href:
                                continue
                            # Normalize to site-internal path
                            if href.startswith("https://developer.apple.com"):
                                href = href[len("https://developer.apple.com"):]
                            elif href.startswith("http"):
                                continue
                            if not href.startswith("/design/human-interface-guidelines/"):
                                continue
                            # Prefer the visible label text within the link
                            title_el = link.query_selector('p.highlight') or link
                            try:
                                title = title_el.inner_text().strip()
                            except Exception:
                                title = (href.rstrip("/").split("/")[-1] or "").replace("-", " ").title()

                            if href not in seen_hrefs:
                                seen_hrefs.add(href)
                                discovered_links.append({"href": href, "title": title})

                        # Scroll one step
                        at_edge = navigator.evaluate(
                            "(el) => { const nearTop = el.scrollTop <= 1; const nearBottom = el.scrollTop >= (el.scrollHeight - el.clientHeight - 1); return {nearTop, nearBottom, top: el.scrollTop, max: el.scrollHeight - el.clientHeight}; }"
                        )

                        if (direction == "down" and at_edge["nearBottom"]) or (direction == "up" and at_edge["nearTop"]):
                            stable_steps += 1
                            if stable_steps >= 3:
                                break
                        else:
                            delta = 400 if direction == "down" else -400
                            navigator.evaluate("(el, d) => { el.scrollBy(0, d); }", delta)
                            page.wait_for_timeout(120)

                        # If nothing new for a while, early stop
                        if len(discovered_links) == last_count:
                            stable_steps += 1
                        else:
                            stable_steps = 0
                            last_count = len(discovered_links)

                # Two passes can help reveal nodes that render only after parents expand
                run_pass("down")
                run_pass("up")
                run_pass("down")

            if navigator:
                print("Expanding and scrolling navigation to discover all links...")
                crawl_nav()
                print(f"Found {len(discovered_links)} total links in the navigator (unique by href).")
            else:
                print("Navigation sidebar not detected; falling back to section page traversal.")

            # Helper: scroll full page to force-load lazy/virtual content
            def scroll_full_page():
                try:
                    last = -1
                    same_count = 0
                    for _ in range(60):
                        height = page.evaluate("() => document.scrollingElement.scrollHeight")
                        if height == last:
                            same_count += 1
                        else:
                            same_count = 0
                        if same_count >= 2:
                            break
                        page.evaluate("() => window.scrollBy(0, window.innerHeight)")
                        page.wait_for_timeout(150)
                        last = height
                    # Return to top for consistent DOM order reads
                    page.evaluate("() => window.scrollTo(0, 0)")
                    page.wait_for_timeout(100)
                except Exception:
                    pass

            # Helper to collect links from the current page by URL prefix, in DOM order
            def collect_links_from_page(url_prefix: str):
                # Ensure content is fully rendered
                scroll_full_page()
                links = page.query_selector_all('a[href^="/design/human-interface-guidelines/"]') or []
                items = []
                for a in links:
                    href = a.get_attribute("href")
                    if not href:
                        continue
                    # Normalize to same-origin path
                    if href.startswith("https://developer.apple.com"):
                        href = href[len("https://developer.apple.com"):]
                    elif href.startswith("http"):
                        continue
                    title_el = a.query_selector('p.highlight, h2, h3, .card-title') or a
                    try:
                        title = title_el.inner_text().strip()
                    except Exception:
                        title = (href.rstrip("/").split("/")[-1] or "").replace("-", " ").title()
                    items.append({"href": href, "title": title})
                return items

            # Traverse each top-level section page to capture full set of links
            def add_if_new(items):
                for it in items:
                    href = it["href"].split("#")[0]
                    if href not in seen_hrefs and href.startswith("/design/human-interface-guidelines/"):
                        seen_hrefs.add(href)
                        discovered_links.append(it)

            # Build per-section crawl
            for top_slug, top_name in slug_to_top.items():
                section_url = urljoin(base_url, f"/design/human-interface-guidelines/{top_slug}/")
                try:
                    page.goto(section_url, wait_until="networkidle", timeout=60000)
                except Exception:
                    continue

                # On the section landing page, collect all internal links
                prefix = f"/design/human-interface-guidelines/{top_slug}"
                items = collect_links_from_page(prefix)
                add_if_new(items)

                # Special: Components -> also visit each sub-section page to collect its articles
                if top_slug == "components":
                    # Identify sub-section links (depth == 4: /.../components/<sub>/)
                    sub_links = []
                    for it in items:
                        parts = [p for p in it["href"].split("/") if p]
                        if len(parts) >= 4 and parts[2] == "components":
                            # keep unique sub-section hrefs (both overview and deeper will be revisited)
                            sub_links.append(it["href"].split("#")[0].rstrip("/"))
                    sub_links = list(dict.fromkeys(sub_links))  # de-dup preserving order

                    # Ensure we also visit any known sub-sections, even if not linked on the landing page
                    for sub_slug in comp_slug_to_name.keys():
                        candidate = f"/design/human-interface-guidelines/components/{sub_slug}"
                        if candidate not in sub_links:
                            sub_links.append(candidate)

                    for sub_href in sub_links:
                        # Only visit sub-section overview pages (exactly /components/<sub>)
                        p = [p for p in sub_href.split("/") if p]
                        if len(p) == 4 and p[2] == "components":
                            sub_url = urljoin(base_url, sub_href + "/")
                            try:
                                page.goto(sub_url, wait_until="networkidle", timeout=60000)
                                sub_items = collect_links_from_page(sub_href)
                                add_if_new(sub_items)
                            except Exception:
                                pass

            # Classify links using page content (header/breadcrumb) with fallback slug mappings
            # Fallback mappings for root-level articles that belong to a top section (from your list)
            getting_started_slugs = {
                "designing-for-ios", "designing-for-ipados", "designing-for-macos", "designing-for-tvos",
                "designing-for-visionos", "designing-for-watchos", "designing-for-games",
            }
            foundations_slugs = {
                "accessibility", "app-icons", "branding", "color", "dark-mode", "icons", "images",
                "immersive-experiences", "inclusion", "layout", "materials", "motion", "privacy",
                "right-to-left", "sf-symbols", "spatial-layout", "typography", "writing",
            }
            patterns_slugs = {
                "charting-data", "collaboration-and-sharing", "drag-and-drop", "entering-data", "feedback",
                "file-management", "going-full-screen", "launching", "live-viewing-apps", "loading",
                "managing-accounts", "managing-notifications", "modality", "multitasking", "offering-help",
                "onboarding", "playing-audio", "playing-haptics", "playing-video", "printing",
                "ratings-and-reviews", "searching", "settings", "undo-and-redo", "workouts",
            }
            inputs_slugs = {
                "action-button", "apple-pencil-and-scribble", "camera-control", "digital-crown", "eyes",
                "focus-and-selection", "game-controls", "gestures", "gyroscope-and-accelerometer", "gyro-and-accelerometer", "keyboards",
                "nearby-interactions", "pointing-devices", "remotes",
            }
            technologies_slugs = {
                "airplay", "always-on", "app-clips", "apple-pay", "augmented-reality", "carekit", "carplay",
                "game-center", "generative-ai", "healthkit", "homekit", "icloud", "id-verifier",
                "imessage-apps-and-stickers", "in-app-purchase", "live-photos", "mac-catalyst",
                "machine-learning", "maps", "nfc", "photo-editing", "researchkit", "shareplay", "shazamkit",
                "sign-in-with-apple", "siri", "tap-to-pay-on-iphone", "voiceover", "wallet",
            }

            # Components: map flat article slugs to sub-section names
            components_articles_by_sub = {
                "Content": {
                    "charts", "image-views", "text-views", "web-views",
                },
                "Layout and Organization": {
                    "boxes", "collections", "column-views", "disclosure-controls", "labels",
                    "lists-and-tables", "lockups", "outline-views", "split-views", "tab-views",
                },
                "Menus and Actions": {
                    "activity-views", "buttons", "context-menus", "dock-menus", "edit-menus",
                    "home-screen-quick-actions", "menus", "ornaments", "pop-up-buttons", "pull-down-buttons",
                    "the-menu-bar", "toolbars",
                },
                "Navigation and Search": {
                    "path-controls", "search-fields", "sidebars", "tab-bars", "token-fields",
                },
                "Presentation": {
                    "action-sheets", "alerts", "page-controls", "panels", "popovers", "scroll-views",
                    "sheets", "windows",
                },
                "Selection and Input": {
                    "color-wells", "combo-boxes", "digit-entry-views", "image-wells", "pickers",
                    "segmented-controls", "sliders", "steppers", "text-fields", "toggles", "virtual-keyboards",
                },
                "Status": {
                    "activity-rings", "gauges", "progress-indicators", "rating-indicators",
                },
                "System Experiences": {
                    "app-shortcuts", "complications", "controls", "live-activities", "notifications",
                    "status-bars", "top-shelf", "watch-faces", "widgets",
                },
            }

            from typing import Optional
            def map_root_slug_to_top(slug: str) -> Optional[str]:
                if slug in getting_started_slugs:
                    return "Getting Started"
                if slug in foundations_slugs:
                    return "Foundations"
                if slug in patterns_slugs:
                    return "Patterns"
                if slug in inputs_slugs:
                    return "Inputs"
                if slug in technologies_slugs:
                    return "Technologies"
                return None
            def extract_page_context_text() -> str:
                try:
                    ctx = page.evaluate(
                        """
                        () => {
                            const texts = [];
                            const grab = (sel) => Array.from(document.querySelectorAll(sel)).forEach(el => {
                                const t = (el.innerText || '').trim(); if (t) texts.push(t);
                            });
                            // Breadcrumbs / category labels / badges / eyebrows
                            grab('nav[aria-label*="breadcrumb" i] a');
                            grab('[class*="eyebrow" i], .eyebrow, .topic-eyebrow, .badge, .category, .section-eyebrow');
                            // Prominent headings
                            grab('main header h1, main header h2, main h1');
                            return texts.join('\n').slice(0, 4000);
                        }
                        """
                    )
                    return (ctx or '').lower()
                except Exception:
                    try:
                        return (page.title() or '').lower()
                    except Exception:
                        return ''

            def detect_top_and_sub(text_lower: str):
                top = None
                for name in TOP_LEVEL_ORDER:
                    if name.lower() in text_lower:
                        top = name
                        break
                sub = None
                if top == 'Components':
                    for name in COMPONENTS_ORDER:
                        if name.lower() in text_lower:
                            sub = name
                            break
                return top, sub

            # Visit each discovered link and classify it
            seen_urls_for_classification = set()
            for item in discovered_links:
                href = item["href"].split("#")[0]
                title = item["title"]
                full_url = urljoin(base_url, href)
                if full_url in seen_urls_for_classification:
                    continue
                seen_urls_for_classification.add(full_url)

                parts = [p for p in href.split("/") if p]
                if len(parts) < 3 or parts[0] != "design" or parts[1] != "human-interface-guidelines":
                    continue
                # Remove any repeated 'human-interface-guidelines'
                i = 2
                while i < len(parts) and parts[i] == "human-interface-guidelines":
                    parts.pop(i)
                if len(parts) < 3:
                    continue

                # Skip top-level overview pages
                if parts[2] in slug_to_top and len(parts) == 3:
                    continue
                # Skip component sub-section overview pages
                if parts[2] == "components" and len(parts) == 4:
                    continue

                # Load page quickly for classification
                try:
                    page.goto(full_url, wait_until="domcontentloaded", timeout=30000)
                except Exception:
                    pass
                ctx_text = extract_page_context_text()
                top_name, sub_name = detect_top_and_sub(ctx_text)

                # Fallbacks
                if not top_name:
                    slug = parts[2]
                    if slug in slug_to_top and len(parts) >= 4:
                        top_name = slug_to_top[slug]
                    else:
                        # First, check if it's a flat Components article
                        comp_sub = None
                        for sub_name_cand, slugs in components_articles_by_sub.items():
                            if slug in slugs:
                                top_name = "Components"
                                comp_sub = sub_name_cand
                                break
                        if not top_name:
                            mapped = map_root_slug_to_top(slug)
                            if mapped:
                                top_name = mapped

                if not top_name:
                    # Could not classify
                    continue

                if top_name == "Components":
                    # Prefer sub_name from content; else infer from path or flat mapping
                    if not sub_name:
                        if len(parts) >= 4 and parts[2] == "components":
                            sub_slug = parts[3]
                            sub_name = comp_slug_to_name.get(sub_slug, sub_slug.replace("-", " ").title())
                        else:
                            # from flat mapping if available
                            for sub_name_cand, slugs in components_articles_by_sub.items():
                                if parts[2] in slugs:
                                    sub_name = sub_name_cand
                                    break
                    if sub_name:
                        add_sub_article(top_name, sub_name, title, full_url)
                    else:
                        # If we still couldn't detect a sub-section, add under Components root
                        add_article(top_name, title, full_url)
                else:
                    add_article(top_name, title, full_url)

            # Convert section map to ordered list
            sections = []

            # First, add known top-level sections in the desired order
            for name in TOP_LEVEL_ORDER:
                if name in sections_map:
                    sec = sections_map[name]
                    # Emit sub-sections for Components in the specified order
                    if name == "Components":
                        sub_sections = []
                        # Ordered first
                        for sub_name in COMPONENTS_ORDER:
                            if sub_name in sec["_sub_map"]:
                                sub_sections.append({
                                    "title": sub_name,
                                    "articles": sec["_sub_map"][sub_name],
                                })
                        # Then any extra sub-sections the site may have added
                        for sub_name, articles in sec["_sub_map"].items():
                            if sub_name not in COMPONENTS_ORDER:
                                sub_sections.append({"title": sub_name, "articles": articles})
                        sec["sub_sections"] = sub_sections

                    sections.append({
                        "title": sec["title"],
                        "articles": sec["articles"],
                        "sub_sections": sec["sub_sections"],
                    })

            # Finally, append any unexpected sections (in nav order of discovery)
            for name, sec in sections_map.items():
                if name not in TOP_LEVEL_ORDER:
                    sections.append({
                        "title": sec["title"],
                        "articles": sec["articles"],
                        "sub_sections": [
                            {"title": k, "articles": v} for k, v in sec["_sub_map"].items()
                        ],
                    })

        except Exception as e:
            print(f"An error occurred during URL discovery: {str(e)}")
            sections = []
        finally:
            browser.close()

    # Basic stats
    total_articles = sum(len(s.get("articles", [])) + sum(len(ss.get("articles", [])) for ss in s.get("sub_sections", [])) for s in sections)
    print(f"\nDiscovered {len(sections)} sections.")
    print(f"Found {total_articles} articles across {len(sections)} sections.")

    # Print concise discovery summary with counts and sample URLs
    if sections:
        print("\nDiscovery summary:")
        for section in sections:
            root_count = len(section.get("articles", []))
            sub_sections = section.get("sub_sections", [])
            sub_total = sum(len(ss.get("articles", [])) for ss in sub_sections)
            print(f"- {section['title']}: {root_count + sub_total} articles (root: {root_count}, sub-sections: {len(sub_sections)})")

            # Root article samples
            if root_count:
                root_samples = ", ".join(a.get("url", "") for a in section["articles"][:2])
                print(f"  root samples: {root_samples}")

            # Sub-section counts and samples
            for ss in sub_sections:
                ss_count = len(ss.get("articles", []))
                ss_samples = ", ".join(a.get("url", "") for a in ss.get("articles", [])[:2])
                print(f"  - {ss['title']}: {ss_count} articles; samples: {ss_samples}")
    return sections
