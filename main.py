from url_discovery import get_article_urls
from pdf_generator import generate_pdfs
from pdf_merger import merge_pdfs

def main():
    articles = get_article_urls()
    print(f"Found {len(articles)} articles")
    
    print("Starting PDF generation for articles...")
    output_folder, generated_files, sections_info = generate_pdfs(articles)
    
    print("\nStarting PDF merge process...")
    final_pdf = merge_pdfs(output_folder, generated_files, sections_info)
    
    if final_pdf:
        print(f'\n✅ Successfully generated and merged PDFs into: {final_pdf}')
    else:
        print('\n❌ Failed to merge PDFs')

if __name__ == "__main__":
    main()
