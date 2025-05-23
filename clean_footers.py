
import sqlite3
import re

DB_PATH = "yardbonita.db"

def remove_footer_blocks(html):
    if not html:
        return html
    pattern = re.compile(r'<div class="(related-articles|author-byline)">.*?</div>', flags=re.DOTALL)
    cleaned = re.sub(pattern, '', html).strip()
    cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned).strip()
    return cleaned

def clean_article_htmls():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT uuid, article_html FROM articles
        WHERE article_html LIKE '%<div class="related-articles%">%'
           OR article_html LIKE '%<div class="author-byline%">%'
    """)
    rows = cursor.fetchall()

    for uuid, html in rows:
        cleaned_html = remove_footer_blocks(html)
        if cleaned_html != html:
            cursor.execute("UPDATE articles SET article_html = ? WHERE uuid = ?", (cleaned_html, uuid))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    clean_article_htmls()
