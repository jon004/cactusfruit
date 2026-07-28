import psycopg2
from typing import Dict

class PageDAO:
    def __init__(self, db_conn):
        self.conn = db_conn

    def delete_by_source(self, source_path: str):
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM pages WHERE source_path = %s", (source_path,))
        self.conn.commit()

    def save_pages(self, source_path: str, pages: Dict[int, str]):
        with self.conn.cursor() as cur:
            for page_no, text in pages.items():
                cur.execute(
                    "INSERT INTO pages (source_path, page_index, raw_text) VALUES (%s, %s, %s)",
                    (source_path, page_no, text)
                )
        self.conn.commit()

    def full_text_search(self, query: str, limit: int):
        with self.conn.cursor() as cur:
            # Using trigram similarity (% operator requires pg_trgm extension)
            cur.execute("""
                SELECT id, source_path, page_index 
                FROM pages 
                WHERE raw_text %% %s 
                ORDER BY similarity(raw_text, %s) DESC 
                LIMIT %s
            """, (query, query, limit))
            return [{"id": row[0], "source": row[1], "page": row[2]} for row in cur.fetchall()]
