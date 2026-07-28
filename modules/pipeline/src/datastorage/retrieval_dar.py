from typing import List, Dict
from datastorage.page_dao import PageDAO
from datastorage.embeddings_dao import EmbeddingsDAO
from languagemodels.embedder import ChunkEmbedder

class RetrievalDAR:
    def __init__(self, conn):
        self.conn = conn
        self.page_dao = PageDAO(conn)
        self.emb_dao = EmbeddingsDAO(conn)
        self.embedder = ChunkEmbedder()

    def execute(self, pivot_query: str, attribute_query: str, top_k: int = 30) -> List[Dict]:
        # 1. Perform searches independently
        bm25_hits = self.page_dao.full_text_search(pivot_query, limit=top_k)
        
        query_vec = self.embedder.embed_query(attribute_query)
        vector_hits = self.emb_dao.vector_search(query_vec, limit=top_k)
        
        # 2. Reciprocal Rank Fusion (Python side is fine for small top_k sets)
        final_ids = self._rrf(bm25_hits, vector_hits, k=60)
        
        # 3. Hydrate content in one go
        return self._hydrate_results(final_ids[:top_k])

    def _rrf(self, bm25_hits, vector_hits, k=60) -> List[Dict]:
        scores = {}
        for r, hit in enumerate(bm25_hits):
            scores[hit['id']] = scores.get(hit['id'], 0) + (1 / (k + r + 1))
        for r, hit in enumerate(vector_hits):
            scores[hit['id']] = scores.get(hit['id'], 0) + (1 / (k + r + 1))
        
        # Return sorted IDs
        return sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    def _hydrate_results(self, ids: List[int]) -> List[Dict]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM pages WHERE id = ANY(%s)", (ids,))
            return [dict(zip([column[0] for column in cur.description], row)) for row in cur.fetchall()]
