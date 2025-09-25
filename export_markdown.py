from src.url_discovery import get_article_urls
from src.markdown_exporter import export_markdown


def main():
    sections = get_article_urls()
    out_dir = export_markdown(sections)
    print(f"\n✅ Markdown export complete at: {out_dir}")


if __name__ == "__main__":
    main()
