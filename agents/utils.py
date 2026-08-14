import re
from langchain_core.output_parsers import PydanticOutputParser

def clean_json_string(text: str) -> str:
    """
    Cleans raw LLM text by removing reasoning/thinking blocks and extracting
    JSON content from markdown code blocks or brackets.
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

def parse_pydantic_response(text: str, parser: PydanticOutputParser):
    """
    Helper to clean raw LLM output and parse it using PydanticOutputParser.
    """
    cleaned_text = clean_json_string(text)
    return parser.parse(cleaned_text)
