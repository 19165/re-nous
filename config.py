import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from schemas import BudgetConfig
from utils.logger import logger

# Load environment variables from .env
load_dotenv()

# Configuration variables
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Validate Tavily API Key
if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY environment variable is not set in your .env file!")

# Base Ollama LLM instance
llm = ChatOllama(
    base_url=OLLAMA_BASE_URL,
    model=OLLAMA_MODEL,
    temperature=0,
)

# Role-Based Generation Token Limits (num_predict)
MAX_TOKENS_PLANNER = int(os.getenv("MAX_TOKENS_PLANNER", "350"))
MAX_TOKENS_QUERY_OPT = int(os.getenv("MAX_TOKENS_QUERY_OPT", "60"))
MAX_TOKENS_SUPERVISOR = int(os.getenv("MAX_TOKENS_SUPERVISOR", "800"))
MAX_TOKENS_WRITER = int(os.getenv("MAX_TOKENS_WRITER", "3500"))

# Raw Content Extraction Limits (characters per source)
MAX_RAW_CONTENT_CHARS = int(os.getenv("MAX_RAW_CONTENT_CHARS", "2500"))

# Default Budget Configuration
default_budget = BudgetConfig(
    max_sub_questions=int(os.getenv("MAX_SUB_QUESTIONS", "3")),
    max_searches_per_sub_question=int(os.getenv("MAX_SEARCHES_PER_SUB_QUESTION", "2")),
    max_total_tokens=int(os.getenv("MAX_TOTAL_TOKENS", "12000")),
    wall_clock_timeout_seconds=float(os.getenv("WALL_CLOCK_TIMEOUT_SECONDS", "60.0")),
    max_revisions=int(os.getenv("MAX_REVISIONS", "1")),
)
