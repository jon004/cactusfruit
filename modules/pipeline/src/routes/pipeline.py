import os
import sqlite3
import logging
import hashlib
import re
import json
from typing import List, Dict, Any

# Imported the new global clients
from languagemodels.generator import generator 
from languagemodels.reranker import reranker
from commands.retrieve import RetrieveCommand
from utils.sentence_splitter import split_sentences

from configs import (
    FACT_EXTRACTOR_ENDPOINT,
    QUERY_GENERATOR_ENDPOINT,
    FACT_JUDGE_ENDPOINT
)

class PipelineCommand:
    def __init__(self, db_conn: sqlite3.Connection):
        self.db_conn = db_conn
        self.logger = logging.getLogger(__name__)
        
        # Using the global 'generator' instance
        self.llm_client = generator
        self.retrieve_cmd = RetrieveCommand(db_conn)
        self.reranker = reranker

    def _generate_id(self, text: str, prefix: str) -> str:
        hash_val = hashlib.md5(text.encode()).hexdigest()[:12]
        return f"{prefix}_{hash_val}"

    def _parse_queries(self, response_text: str, fallback: str) -> Dict[str, str]:
        def extract(tag):
            match = re.search(f"<{tag}>(.*?)</{tag}>", response_text, re.DOTALL | re.IGNORECASE)
            return match.group(1).strip() if match else None

        return {
            "pivot": extract("pivot") or fallback,
            "attribute": extract("attribute") or fallback,
            "boolean": extract("boolean") or fallback
        }

    def _parse_verdict(self, response_text: str) -> str:
        match = re.search(r"<verdict>\s*(.*?)\s*</verdict>", response_text, re.DOTALL | re.IGNORECASE)
        if match:
            v = match.group(1).strip().lower()
            if "contradiction" in v: return "contradiction"
            if "supported" in v: return "supporting" 
            return "not_mentioned"
        return "not_mentioned"

    def _evaluate_atomic_fact_status(self, judgments: List[Dict[str, Any]]) -> str:
        if not judgments:
            return "insufficient_data"
            
        verdicts = [j['verdict'] for j in judgments]
        if "contradiction" in verdicts:
            return "fail"
        if "supporting" in verdicts:
            return "success"
        return "insufficient_data"

    def execute(
        self, 
        input_text: str, 
        rerank_threshold: float = 0.15,
        top_k: int = 3
    ) -> Dict[str, Any]:
        
        evidence_library = {}
        original_chunks_layer = []  
        sentence_layer = []         
        atomic_fact_layer = []      
        
        all_facts = [] 
        
        raw_sentences = split_sentences(input_text)
        chunk_size = 3 
        
        for i in range(0, len(raw_sentences), chunk_size):
            chunk_sents = raw_sentences[i:i+chunk_size]
            chunk_text = " ".join(chunk_sents)
            c_id = self._generate_id(chunk_text, "chunk")
            
            original_chunks_layer.append({
                "chunk_id": c_id,
                "text": chunk_text,
                "source_name": "global_input"
            })
            
            for s_text in chunk_sents:
                sentence_layer.append({
                    "parent_chunk_id": c_id,
                    "text": s_text,
                    "papertrail": []
                })

        # PHASE 1: Fact Extraction 
        self.logger.info("Starting Phase 1: Fact Extraction")
        for i, s_obj in enumerate(sentence_layer):
            target = s_obj["text"]
            if not target: continue
            
            # Use the generator client method
            raw_response = self.llm_client.fact_extractor(target)
            
            if not raw_response: continue

            facts = re.findall(r"<fact>\s*(.*?)\s*</fact>", raw_response, re.DOTALL | re.IGNORECASE)
            
            if not facts and len(raw_response.strip()) > 5:
                facts = [f.strip() for f in raw_response.split('\n') if len(f.strip()) > 5]

            for f_text in facts:
                all_facts.append({"text": f_text, "sentence_ref": s_obj})

        # PHASE 2: Query Generation 
        self.logger.info("Starting Phase 2: Query Generation")
        for f_obj in all_facts:
            raw_res = self.llm_client.query_generator(f_obj["text"])
            f_obj["queries"] = self._parse_queries(raw_res or "", fallback=f_obj["text"])

        # PHASE 3 & 4: Retrieval & Rerank 
        self.logger.info("Starting Phase 3 & 4: Retrieval & Rerank")
        for f_obj in all_facts:
            candidates = self.retrieve_cmd.execute(
                pivot_query=f_obj["queries"]['pivot'],
                attribute_query=f_obj["queries"]['attribute'],
                top_k=30 
            )
            refined_evidence = self.reranker.sort(f_obj["queries"]['boolean'], candidates, top_k=top_k)
            f_obj["refined_evidence"] = refined_evidence
            f_obj["top_score"] = refined_evidence[0]['rerank_score'] if refined_evidence else 0.0

        # PHASE 5 & 6: Fact Judging 
        self.logger.info("Starting Phase 5 & 6: Fact Judging")
        for f_obj in all_facts:
            judgments = []
            f_obj["evidence_refs"] = []
            
            if f_obj["top_score"] >= rerank_threshold:
                for chunk in f_obj["refined_evidence"]:
                    ev_id = self._generate_id(chunk['raw_text'], "ev")
                    
                    if ev_id not in evidence_library:
                        evidence_library[ev_id] = {
                            "source_link": chunk.get('metadata', {}).get('source', 'unknown'),
                            "text": chunk['raw_text']
                        }

                    f_obj["evidence_refs"].append(ev_id)
                    
                    # Use the generator client method
                    judge_prompt = f"Fact: {f_obj['text']}\n\nRetrieved Text: {chunk['raw_text']}"
                    raw_verdict = self.llm_client.fact_judge(judge_prompt)
                    
                    verdict = self._parse_verdict(raw_verdict or "")
                    judgments.append({"chunk_id": ev_id, "verdict": verdict})

            f_obj["status"] = self._evaluate_atomic_fact_status(judgments)
            atomic_fact_layer.append({
                "text": f_obj["text"],
                "status": f_obj["status"]
            })

        return {
            "evidence_library": list(evidence_library.values()),
            "decomposition": atomic_fact_layer
        }
