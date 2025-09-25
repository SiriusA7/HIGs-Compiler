from src.url_discovery import get_article_urls
from src.pdf_generator import generate_pdfs
from src.pdf_merger import merge_pdfs

def main():
    # This now returns a hierarchical structure of sections
    sections = get_article_urls()
    print(f"Found {sum(len(s.get('articles', [])) + sum(len(ss.get('articles', [])) for ss in s.get('sub_sections', [])) for s in sections)} articles across {len(sections)} sections")
    
    print("\nStarting PDF generation for all articles...")
    # generate_pdfs now takes the sections object and returns more structured data
    output_folder, sections_data, generated_files_map, cover_file, index_file = generate_pdfs(sections)
    
    print("\nStarting PDF merge process...")
    # merge_pdfs is updated to handle the new data structure and create nested bookmarks
    final_pdf = merge_pdfs(output_folder, sections_data, generated_files_map, cover_file, index_file)
    
    if final_pdf:
        print(f'\n✅ Successfully generated and merged PDFs into: {final_pdf}')
    else:
        print('\n❌ Failed to merge PDFs')

if __name__ == "__main__":
    main()
