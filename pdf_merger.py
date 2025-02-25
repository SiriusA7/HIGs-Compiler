from PyPDF2 import PdfMerger, PdfReader
import os

def merge_pdfs(output_dir, generated_files, sections_info):
    """Merge PDFs with working bookmarks and internal links"""
    merged_output = "Apple HIGs Complete.pdf"
    
    if not generated_files:
        print("No PDFs found to merge.")
        return None

    try:
        merger = PdfMerger()
        current_page = 0
        
        if os.path.exists(generated_files[0]):
            merger.append(generated_files[0])
            current_page += len(PdfReader(generated_files[0]).pages)
        
        for idx, pdf_path in enumerate(generated_files[1:], 1):
            if os.path.exists(pdf_path):
                print(f"Adding: {os.path.basename(pdf_path)}")
                try:
                    section = sections_info[idx-1]
                    reader = PdfReader(pdf_path)
                    num_pages = len(reader.pages)
                    
                    merger.append(
                        pdf_path,
                        outline_item={
                            "title": section['title'],
                            "page_number": current_page,
                            "type": "/Fit"
                        }
                    )
                    
                    current_page += num_pages
                except Exception as e:
                    print(f"Error adding {pdf_path}: {str(e)}")
                    continue

        merged_path = os.path.join(output_dir, merged_output)
        merger.write(merged_path)
        merger.close()

        # Clean up individual PDFs
        for pdf in generated_files:
            try:
                if os.path.exists(pdf):
                    os.remove(pdf)
            except Exception as e:
                print(f"Error removing {pdf}: {str(e)}")

        return merged_path

    except Exception as e:
        print(f"Error during PDF merge: {str(e)}")
        return None
