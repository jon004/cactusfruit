import psycopg2
from typing import List
from documentutils.models import EmbeddedChunk

class EmbeddingsDAO:
    def __init__(self, db_conn):
        self.conn = db_conn

    def delete_by_source(self, source_path: str):
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM embeddings WHERE source_path = %s", (source_path,))
        self.conn.commit()

    def append_chunks(self, chunks: List[EmbeddedChunk]):
        with self.conn.cursor() as cur:
            for chunk in chunks:
                cur.execute(
                    """INSERT INTO embeddings 
                    (vector, text, body, source_path, page_index, token_offset, token_count, section_path, section_index, section_total) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        chunk.vector, chunk.prefixed_text, chunk.raw_text,
                        chunk.metadata['source'], chunk.metadata['page_start'],
                        0, chunk.token_count, chunk.metadata['section_path'],
                        chunk.metadata['section_index'], chunk.metadata['section_total']
                    )
                )
        self.conn.commit()

    def vector_search(self, query_vector: List[float], limit: int):
        with self.conn.cursor() as cur:
            # Use pgvector's <=> operator for Cosine Distance
            cur.execute("""
                SELECT id, source_path, page_index 
                FROM embeddings 
                ORDER BY vector <=> %s::vector 
                LIMIT %s
            """, (query_vector, limit))
            return [{"id": row[0], "source": row[1], "page": row[2]} for row in cur.fetchall()]
