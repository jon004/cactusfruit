import re
import sys
import logging
from typing import List
from docling_core.types.doc import SectionHeaderItem, TableItem, PictureItem, DocItemLabel, TextItem
from docling_core.types.doc.document import ListItem
from documentutils.models import Chunk
from languagemodels.embedder import ChunkEmbedder

class DocumentChunker:
    def __init__(self, target_tokens: int = 300, max_tokens: int = 448):
        self.target_tokens = target_tokens
        self.max_tokens = max_tokens
        self.embedder = ChunkEmbedder()
        self.logger = logging.getLogger(__name__)

    def chunk_structured_doc(self, doc, source_path: str) -> List[Chunk]:
        chunks: List[Chunk] = []
        section_titles: List[str] = []
        buffer_blocks: List[str] = []
        buffer_pages = set()

        def get_path() -> str:
            return " > ".join(t for t in section_titles if t) or "Document"

        def flush_buffer():
            if not buffer_blocks:
                return
            raw_text = "\n\n".join(buffer_blocks).strip()
            chunks.append(Chunk(
                raw_text=raw_text,
                metadata={
                    "source": source_path,
                    "section_path": get_path(),
                    "page_start": min(buffer_pages) if buffer_pages else None,
                    "page_end": max(buffer_pages) if buffer_pages else None
                }
            ))
            buffer_blocks.clear()
            buffer_pages.clear()

        for item, _ in doc.iterate_items():
            # 1. Improved Header Hierarchy (Ported from ingest.py)
            # Handles titles and dynamic level extension to prevent index errors
            if isinstance(item, SectionHeaderItem) or (
                isinstance(item, TextItem) and item.label == DocItemLabel.TITLE
            ):
                flush_buffer()
                heading_text = item.text.strip()
                heading_level = item.level if isinstance(item, SectionHeaderItem) else 1

                if heading_level > len(section_titles):
                    section_titles.extend([""] * (heading_level - len(section_titles)))
                section_titles = section_titles[:heading_level]
                section_titles[heading_level - 1] = heading_text
                continue

            # 2. Extract Text with List Item Support
            block_text = self._item_to_text(doc, item)
            if not block_text: continue
            page_no = getattr(item, 'page_no', None) or getattr(item, 'page_number', None)

            # 3. Decision Logic: Buffer, Split, or Flush
            current_tokens = self._get_tokens("\n\n".join(buffer_blocks + [block_text]))

            if current_tokens <= self.target_tokens:
                buffer_blocks.append(block_text)
                if page_no: buffer_pages.add(page_no)
            else:
                if buffer_blocks: flush_buffer()
                
                if self._get_tokens(block_text) > self.max_tokens:
                    safe_page = int(page_no) if page_no is not None else 0
                    sub_chunks = self._split_large_block(block_text, get_path(), source_path, safe_page)
                    chunks.extend(sub_chunks)
                else:
                    buffer_blocks.append(block_text)
                    if page_no: buffer_pages.add(page_no)

        flush_buffer()
        return self._finalize_chunks(chunks)

    def _split_large_block(self, text: str, section: str, path: str, page: int) -> List[Chunk]:
        """Recursive split for huge paragraphs using sentence boundaries."""
        res = []
        sentences = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text).strip())
        buf = []
        
        for sent in sentences:
            candidate = " ".join(buf + [sent])
            if self._get_tokens(candidate) <= self.max_tokens:
                buf.append(sent)
            else:
                if buf:
                    res.append(Chunk(raw_text=" ".join(buf), metadata={"section_path": section, "source": path, "page_start": page, "page_end": page}))
                buf = [sent]
        if buf:
            res.append(Chunk(raw_text=" ".join(buf), metadata={"section_path": section, "source": path, "page_start": page, "page_end": page}))
        return res

    def _item_to_text(self, doc, item) -> str:
        if isinstance(item, ListItem):
            marker = getattr(item, "marker", None)
            text = item.text.strip()
            return f"{marker} {text}" if marker else f"- {text}"
            
        # FIX: Remove the 'item_set={item}' wrapper to avoid hashing the object
        if isinstance(item, (TableItem, PictureItem)):
            try: 
                # doc.export_to_markdown(item) is the correct API usage
                return doc.export_to_markdown(item) 
            except Exception as e: 
                self.logger.error(f"Error exporting item to markdown: {e}")
                return ""
            
        return item.text.strip() if hasattr(item, 'text') else ""

    def _finalize_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        """Injects context and flattens metadata."""
        from collections import Counter
        path_counts = Counter(c.metadata["section_path"] for c in chunks)
        current_counts = {}

        for idx, c in enumerate(chunks):
            path = c.metadata["section_path"]
            current_counts[path] = current_counts.get(path, 0) + 1
            
            c.metadata.update({
                "section_index": current_counts[path],
                "section_total": path_counts[path],
                "global_index": idx
            })
            
            # Formats prefix using the logic from ingest.py
            prefix = f"Section: {path}"
            if c.metadata["section_total"] > 1:
                prefix += f" (part {c.metadata['section_index']} of {c.metadata['section_total']})"
            
            c.prefixed_text = f"{prefix}\n\n{c.raw_text}"
            c.token_count = self._get_tokens(c.prefixed_text)
        return chunks

    def _get_tokens(self, text: str) -> int:
        """Get exact token count from llmserver using ChunkEmbedder."""
        count = self.embedder.token_count(text)
        return count
