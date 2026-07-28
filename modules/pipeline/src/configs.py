import os

# Base directory matching your mac_installer.sh
BASE_MODEL_DIR = os.path.expanduser("~/.localdoby/models")

# --- Model Paths (Mapped to mac_installer.sh) ---
LLM_SERVER_URL = "http://localhost:8080"

# Embedder
EMBEDDER_MODEL_PATH = os.path.join(BASE_MODEL_DIR, "all-MiniLM-L6-v2.gguf")

# Generator/Task Models
# These now point to the specific model folder paths
FACT_EXTRACTOR_MODEL = os.path.join(BASE_MODEL_DIR, "fact-extractor-1.7b.gguf")
QUERY_GEN_MODEL = os.path.join(BASE_MODEL_DIR, "query-generator-1.5b.gguf")
FACT_JUDGE_MODEL = os.path.join(BASE_MODEL_DIR, "fact-judge-1.7b.gguf")

# Re-Ranker (Cross-Encoder)
# Note: The code will load from this directory automatically
RERANKER_MODEL_PATH = os.path.join(BASE_MODEL_DIR, "ms-marco-MiniLM-L6-v2")

# Default Fallback (Keeping for legacy compatibility)
DEFAULT_MODEL_PATH = FACT_EXTRACTOR_MODEL
DEFAULT_CHAT_TEMPLATE = "chatml" 

# --- Index Configuration ---
DEFAULT_TARGET_TOKENS = 60  
DEFAULT_MAX_TOKENS = 120

# Thresholds and Scoring
DEFAULT_CLUSTER_SIMILARITY_SCORE = 0.94284
DEFAULT_SIMILARITY_SCORE_FOR_SEARCH_THRESHOLD = 0.555
DEFAULT_SEARCH_LIMIT = 10
DEFAULT_SLIDING_PROMPT_SIMILARITY_SCORE = 0.62
DEFAULT_GRANULAR_SIMILARITY_SCORE = 0.51
DEFAULT_RERANK_THRESHOLD = 0.15

DB_DIR = os.path.expanduser("~/.localdoby/db")
DB_PATH = os.path.join(DB_DIR, "document_data.db")
