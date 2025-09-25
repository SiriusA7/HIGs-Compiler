from PyPDF2 import PdfMerger, PdfReader
import os


def merge_pdfs(output_dir, sections, generated_files_map, cover_file, index_file):
    """Merge PDFs with nested bookmarks, preserving the discovered hierarchy order."""
    merged_output = "Apple HIGs Complete.pdf"

    if not generated_files_map:
        print("No PDFs found to merge.")
        return None

    try:
        merger = PdfMerger()

        # 1. Add Cover
        cover_pages = 0
        if os.path.exists(cover_file):
            merger.append(cover_file)
            cover_pages = get_pdf_page_count(cover_file)

        # 2. Add Index
        index_pages = 0
        if os.path.exists(index_file):
            merger.append(index_file)
            index_pages = get_pdf_page_count(index_file)

        # 3. Append content PDFs in the order provided by sections
        files_to_append = []
        for section in sections:
            for article in section.get("articles", []):
                filepath, _ = generated_files_map.get(article["url"], (None, None))
                if filepath and os.path.exists(filepath):
                    files_to_append.append(filepath)
            for sub_section in section.get("sub_sections", []):
                for article in sub_section.get("articles", []):
                    filepath, _ = generated_files_map.get(article["url"], (None, None))
                    if filepath and os.path.exists(filepath):
                        files_to_append.append(filepath)

        for filepath in files_to_append:
            print(f"Appending: {os.path.basename(filepath)}")
            merger.append(filepath)

        # 4. Build the outline (bookmarks)
        current_page = cover_pages + index_pages  # zero-based index in PyPDF2

        for section in sections:
            # Section bookmark points to the first page of the section's first article
            section_start_page = current_page
            parent_bookmark = merger.add_outline_item(section["title"], section_start_page)

            # Articles directly under the section
            for article in section.get("articles", []):
                filepath, page_count = generated_files_map.get(article["url"], (None, 0))
                if filepath and os.path.exists(filepath):
                    merger.add_outline_item(article["title"], current_page, parent=parent_bookmark)
                    current_page += page_count

            # Sub-sections
            for sub_section in section.get("sub_sections", []):
                sub_parent_bookmark = merger.add_outline_item(sub_section["title"], current_page, parent=parent_bookmark)
                for article in sub_section.get("articles", []):
                    filepath, page_count = generated_files_map.get(article["url"], (None, 0))
                    if filepath and os.path.exists(filepath):
                        merger.add_outline_item(article["title"], current_page, parent=sub_parent_bookmark)
                        current_page += page_count

        # Write final merged PDF
        merged_path = os.path.join(output_dir, merged_output)
        merger.write(merged_path)
        merger.close()

        # Clean up individual PDFs
        try:
            if os.path.exists(cover_file):
                os.remove(cover_file)
            if os.path.exists(index_file):
                os.remove(index_file)
            for filepath, _ in generated_files_map.values():
                if os.path.exists(filepath):
                    os.remove(filepath)
        except Exception:
            # Non-critical cleanup errors can be ignored
            pass

        return merged_path

    except Exception as e:
        print(f"Error during PDF merge: {str(e)}")
        return None

def get_pdf_page_count(pdf_path):
    """Helper to get page count, needed for bookmark logic."""
    from PyPDF2 import PdfReader
    try:
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            return len(reader.pages)
    except Exception:
        return 0
