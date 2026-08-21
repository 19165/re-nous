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
MAX_TOKENS_PLANNER = int(os.getenv("MAX_TOKENS_PLANNER", "1200"))
MAX_TOKENS_QUERY_OPT = int(os.getenv("MAX_TOKENS_QUERY_OPT", "150"))
MAX_TOKENS_SUPERVISOR = int(os.getenv("MAX_TOKENS_SUPERVISOR", "1500"))
MAX_TOKENS_WRITER = int(os.getenv("MAX_TOKENS_WRITER", "4000"))

# Tavily Search Configuration
TAVILY_CHUNKS_PER_SOURCE = int(os.getenv("TAVILY_CHUNKS_PER_SOURCE", "3"))
TAVILY_INCLUDE_RAW_CONTENT = os.getenv("TAVILY_INCLUDE_RAW_CONTENT", "false").lower() == "true"
MAX_RAW_CONTENT_CHARS = int(os.getenv("MAX_RAW_CONTENT_CHARS", "2500"))

# Default Budget Configuration
default_budget = BudgetConfig(
    max_sub_questions=int(os.getenv("MAX_SUB_QUESTIONS", "3")),
    max_searches_per_sub_question=int(os.getenv("MAX_SEARCHES_PER_SUB_QUESTION", "2")),
    max_sources_per_domain_sub_q=int(os.getenv("MAX_SOURCES_PER_DOMAIN_SUB_Q", "1")),
    max_total_tokens=int(os.getenv("MAX_TOTAL_TOKENS", "16000")),
    wall_clock_timeout_seconds=float(os.getenv("WALL_CLOCK_TIMEOUT_SECONDS", "60.0")),
    max_revisions=int(os.getenv("MAX_REVISIONS", "1")),
)

# Redis Configuration & Persistence (Phase 4)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_CACHE_TTL = int(os.getenv("REDIS_CACHE_TTL", "86400"))  # 24 hours (86400 seconds)

redis_client = None
is_redis_available: bool = False

try:
    import redis
    _client = redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
    _client.ping()
    redis_client = _client
    is_redis_available = True
    logger.info(f"[bold green]✨ Redis persistence & cache connected:[/bold green] [cyan]{REDIS_URL}[/cyan]")
except Exception as e:
    logger.warning(f"[bold yellow]⚠️ Redis connection unavailable ({e}). Falling back to in-memory state & bypassing Redis node cache.[/bold yellow]")
    redis_client = None
    is_redis_available = False

# Database Configuration (Phase 5 - Permanent Storage)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/research_db"
)


