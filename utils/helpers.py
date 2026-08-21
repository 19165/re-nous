import re
from typing import TypeVar, Any
from pydantic import BaseModel
from langchain_core.output_parsers import PydanticOutputParser
import tiktoken

T = TypeVar("T", bound=BaseModel)

def clean_json_string(text: str) -> str:
    """
    Cleans raw LLM text by removing reasoning/thinking blocks and extracting
    JSON content from markdown code blocks or raw brackets.
    """
    # 1. Remove reasoning/thinking tags (e.g., <think>...</think>) if present
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = text.strip()
    
    # 2. Extract JSON from markdown code blocks (e.g., ```json ... ``` or ``` ... ```)
    markdown_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if markdown_match:
        return markdown_match.group(1).strip()
    
    # 3. Fallback: Find the first '{' and last '}' to extract raw JSON
    brace_match = re.search(r"(\{.*\})", text, re.DOTALL)
    if brace_match:
        return brace_match.group(1).strip()
    
    return text

def parse_pydantic_response(text: str, parser: PydanticOutputParser[T]) -> T:
    """
    Helper to clean raw LLM output and parse it using PydanticOutputParser.
    """
    cleaned_text = clean_json_string(text)
    return parser.parse(cleaned_text)

def count_tokens_text(text: str, model: str = "cl100k_base") -> int:
    """
    Computes token count of a given text string using tiktoken with fallback.
    """
    try:
        encoding = tiktoken.get_encoding(model)
        return len(encoding.encode(text))
    except Exception:
        return max(1, len(text) // 4)

def extract_token_usage(response: Any, prompt_text: str = "") -> int:
    """
    Extracts exact token count from LangChain/Ollama AIMessage response metadata.
    Falls back to tiktoken or character count heuristic if metadata is missing.
    """
    # 1. Check LangChain standardized usage_metadata
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        total = response.usage_metadata.get("total_tokens")
        if total:
            return int(total)
        input_tokens = response.usage_metadata.get("input_tokens", 0)
        output_tokens = response.usage_metadata.get("output_tokens", 0)
        if input_tokens or output_tokens:
            return int(input_tokens + output_tokens)

    # 2. Check Ollama-specific response_metadata
    if hasattr(response, "response_metadata") and response.response_metadata:
        meta = response.response_metadata
        prompt_eval = meta.get("prompt_eval_count", 0)
        eval_count = meta.get("eval_count", 0)
        if prompt_eval or eval_count:
            return int(prompt_eval + eval_count)
        if "token_usage" in meta and isinstance(meta["token_usage"], dict):
            total = meta["token_usage"].get("total_tokens")
            if total:
                return int(total)

    # 3. Fallback: tiktoken estimation on prompt + response content
    content_str = str(getattr(response, "content", response))
    full_text = f"{prompt_text}\n{content_str}"
    return count_tokens_text(full_text)
