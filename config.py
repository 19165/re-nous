import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
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

# Initialize Ollama Cloud LLM
llm = ChatOllama(
    base_url=OLLAMA_BASE_URL,
    model=OLLAMA_MODEL,
    temperature=0,
)
