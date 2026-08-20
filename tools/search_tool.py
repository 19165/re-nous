import re
from typing import List, Dict, Any, Union, Optional
from langchain_tavily import TavilySearch
from tools.base_tool import BaseTool
from schemas import SearchSource
from config import TAVILY_CHUNKS_PER_SOURCE, TAVILY_INCLUDE_RAW_CONTENT, MAX_RAW_CONTENT_CHARS
from utils.logger import logger

class TavilySearchTool(BaseTool):
    """Encapsulation adapter for Tavily Web Search with configurable chunks and raw_content extraction."""
    
    name: str = "tavily_search"
    description: str = "Search the web for current facts, articles, and research sources."
    
    def __init__(
        self,
        max_results: int = 3,
        chunks_per_source: int = TAVILY_CHUNKS_PER_SOURCE,
        include_raw_content: Union[bool, str] = TAVILY_INCLUDE_RAW_CONTENT
    ):
        self.max_results = max_results
        self.chunks_per_source = chunks_per_source
        self.include_raw_content = include_raw_content
        self._tool = TavilySearch(
            max_results=max_results,
            chunks_per_source=chunks_per_source,
            include_raw_content=include_raw_content
        )
        
    def invoke(self, query: str, **kwargs: Any) -> List[SearchSource]:
        """Synchronous search invocation."""
        raw_results = self._tool.invoke(query)
        return self._format_results(raw_results)
        
    async def ainvoke(self, query: str, **kwargs: Any) -> List[SearchSource]:
        """Asynchronous search invocation."""
        logger.info(f"🔍 [bold cyan]Searching Tavily for:[/bold cyan] '{query}'")
        raw_results = await self._tool.ainvoke(query)
        sources = self._format_results(raw_results)
        logger.info(f"✅ Found [bold green]{len(sources)}[/bold green] sources for: '{query}'")
        return sources

    @staticmethod
    def _clean_markdown_text(text: str) -> str:
        """Strips excessive newlines and image tags from raw markdown content."""
        if not text:
            return ""
        # Remove markdown image embeds like ![...](...)
        cleaned = re.sub(r"!\[.*?\]\(.*?\)", "", text)
        # Collapse multiple newlines
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()
        
    def _format_results(self, raw_results: Union[Dict[str, Any], List[Any]]) -> List[SearchSource]:
        """Parses and formats raw Tavily results, prioritizing high-signal chunks or cleaned markdown."""
        if isinstance(raw_results, dict) and "results" in raw_results:
            results_list = raw_results["results"]
        elif isinstance(raw_results, list):
            results_list = raw_results
        else:
            results_list = []
            
        sources: List[SearchSource] = []
        for r in results_list:
            if isinstance(r, dict):
                full_raw = r.get("raw_content")
                snippet = r.get("content", "")
                
                if full_raw and isinstance(full_raw, str) and len(full_raw.strip()) > 0:
                    cleaned = self._clean_markdown_text(full_raw)
                    primary_content = cleaned[:MAX_RAW_CONTENT_CHARS]
                else:
                    primary_content = snippet or ""
                    
                sources.append(SearchSource(
                    title=r.get("title", "Untitled Source"),
                    url=r.get("url", ""),
                    content=primary_content,
                    raw_content=full_raw
                ))
        return sources

# Default shared search tool instance with 3 semantic chunks per source
search_tool = TavilySearchTool(
    max_results=3,
    chunks_per_source=TAVILY_CHUNKS_PER_SOURCE,
    include_raw_content=TAVILY_INCLUDE_RAW_CONTENT
)
