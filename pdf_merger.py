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
        
        # Add cover page
        if os.path.exists(generated_files[0]):
            cover_pages = len(PdfReader(generated_files[0]).pages)
            merger.append(generated_files[0])
        
        # Add index page
        if os.path.exists(generated_files[1]):
            index_pages = len(PdfReader(generated_files[1]).pages)
            merger.append(generated_files[1])
        
        # Add content pages with bookmarks using provided page numbers
        for idx, pdf_path in enumerate(generated_files[2:], 1):
            if os.path.exists(pdf_path):
                print(f"Adding: {os.path.basename(pdf_path)}")
                try:
                    section_title, page_number = sections_info[idx-1]
                    
                    # Add bookmark with named destination
                    merger.append(
                        pdf_path,
                        outline_item={
                            "title": section_title,
                            "page_number": page_number + index_pages - 1,
                            "type": "/Fit",
                            "color": "0,0,0",  # Black color for bookmark
                            "dest": f"section_{idx}"  # Named destination for internal linking
                        }
                    )
                except Exception as e:
                    print(f"Error adding {pdf_path}: {str(e)}")
                    continue

        # Write final merged PDF
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
