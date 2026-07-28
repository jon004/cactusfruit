import os
import logging
from typing import List, Dict, Any
from datastorage.page_dao import PageDAO
from datastorage.embeddings_dao import EmbeddingsDAO
from documentutils.converter import DocumentConverter
from documentutils.chunker import DocumentChunker

logger = logging.getLogger(__name__)

def handle_upsert(conn, file_paths: List[str]) -> Dict[str, Any]:
    """
    Handles the /upsert route by executing the full upsert pipeline 
    directly using updated DAO classes.
    """
    if not file_paths:
        return {"status": "error", "message": "No file paths provided"}

    # Initialize DAOs and utilities
    page_dao = PageDAO(conn)
    embeddings_dao = EmbeddingsDAO(conn)
    converter = DocumentConverter()
    chunker = DocumentChunker()

    try:
        for path in file_paths:
            abs_path = os.path.abspath(os.path.expanduser(path))
            logger.info(f"--- Processing upsert: {abs_path} ---")

            # 1. Idempotency: Clean existing records
            page_dao.delete_by_source(abs_path)
            embeddings_dao.delete_by_source(abs_path)

            # 2. Convert document
            doc_obj = converter.convert_to_obj(abs_path)

            # 3. Store pages
            pages_dict = {
                page.page_no: doc_obj.export_to_markdown(page_no=page.page_no)
                for page in doc_obj.pages.values()
            }
            page_dao.save_pages(abs_path, pages_dict)

            # 4. Chunk, embed, and store
            chunks = chunker.chunk_structured_doc(doc_obj, abs_path)
            embedded_chunks = chunker.embedder.embed_document_chunks(chunks)
            embeddings_dao.append_chunks(embedded_chunks)

            logger.info(f"Upsert complete for: {abs_path}")

        return {
            "status": "success", 
            "message": f"Processed {len(file_paths)} files",
            "files": file_paths
        }
    except Exception as e:
        logger.error(f"Upsert failed: {str(e)}")
        return {"status": "error", "message": str(e)}
