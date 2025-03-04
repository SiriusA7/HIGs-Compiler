# Apple Human Interface Guidelines - PDF Generator

This tool automatically scrapes and compiles Apple's Human Interface Guidelines into a comprehensive PDF document, complete with a cover page, table of contents, and bookmarks.

## 🚨 Important Notice

This tool is for **personal use only**. The Apple Human Interface Guidelines are copyrighted material owned by Apple Inc. This script merely facilitates access to publicly available content for personal reference. The generated PDF should not be redistributed or used for commercial purposes.

## 🤔 Why Use This Tool

Having Apple's Human Interface Guidelines available as a single, offline PDF provides several benefits:

- **Offline Access**: Access the complete HIG documentation during flights, commutes, or in areas with limited internet connectivity
- **Persistent Reference**: Maintain access to a specific version of the guidelines even if the online documentation changes
- **Improved Navigation**: Quickly search across the entire documentation using PDF reader search functions
- **Annotation**: Add personal notes, highlights, and bookmarks directly on the document

## ✨ Features

- Automatically discovers all HIG articles from Apple's developer website
- Generates individual PDFs for each article with proper formatting
- Creates a professional cover page and table of contents
- Merges all PDFs with working bookmarks and internal navigation
- Handles pagination for images and special sections
- Detects and removes duplicate content
- Produces a single, well-structured PDF document

## 📋 Requirements

- Python 3.7+
- Playwright
- PyPDF2

## 🛠️ Installation

1. Clone this repository:
   ```
   git clone <repository-url>
   cd HIGs-PDF
   ```

2. Install required dependencies:
   ```
   pip install playwright pypdf2
   playwright install chromium
   ```

## 🚀 Usage

Run the main script:

```
python main.py
```

The script will:
1. Discover all HIG articles from Apple's developer website
2. Generate individual PDFs for each article
3. Create a cover page and table of contents
4. Merge everything into a single PDF
5. Save the final PDF as "Apple HIGs Complete.pdf" in the "Apple-HIGs" directory

## ⚠️ Potential Issues and Solutions

### Network and Web Scraping Issues

- **Rate limiting**: The script might be blocked if too many requests are made too quickly. Solution: Add delay between requests or use proxies.
- **Website structure changes**: If Apple updates their website structure, the URL discovery might break. Solution: Update the selectors in `url_discovery.py`.
- **Timeout errors**: Some pages might take too long to load. Solution: Increase timeout values in the code.

### PDF Generation Issues

- **Missing images**: Sometimes images might not load properly. Solution: Increase the wait time for images in `pdf_generator.py`.
- **Rendering inconsistencies**: Different browsers might render content differently. Solution: Adjust the viewport settings or CSS modifications.
- **Memory issues**: Processing many large PDFs can consume significant memory. Solution: Process in smaller batches or increase available memory.

### PDF Merging Issues

- **Bookmark errors**: Incorrect page numbers in bookmarks. Solution: Check the page counting logic in `pdf_merger.py`.
- **Large file size**: The final PDF might be very large. Solution: Adjust the PDF compression settings.

## 🔍 Project Structure

- `main.py` - The entry point script
- `url_discovery.py` - Discovers HIG article URLs
- `pdf_generator.py` - Converts articles to PDFs
- `pdf_merger.py` - Merges PDFs with bookmarks
- `utils.py` - Utility functions for the project

## 📝 License

This project is for personal use only. The Apple Human Interface Guidelines content is copyrighted by Apple Inc.

## 🙏 Acknowledgements

This tool is not affiliated with, authorized, maintained, sponsored, or endorsed by Apple Inc. or any of its affiliates or subsidiaries.
