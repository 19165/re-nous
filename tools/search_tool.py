from typing import List, Dict, Any, Union
from langchain_tavily import TavilySearch
from tools.base_tool import BaseTool
from schemas import SearchSource
from utils.logger import logger

class TavilySearchTool(BaseTool):
    """Encapsulation adapter for Tavily Web Search."""
    
    name: str = "tavily_search"
    description: str = "Search the web for current facts, articles, and research sources."
    
    def __init__(self, max_results: int = 3):
        self.max_results = max_results
        self._tool = TavilySearch(max_results=max_results)
        
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
        
    def _format_results(self, raw_results: Union[Dict[str, Any], List[Any]]) -> List[SearchSource]:
        """Parses and formats raw Tavily results into typed SearchSource objects."""
        if isinstance(raw_results, dict) and "results" in raw_results:
            results_list = raw_results["results"]
        elif isinstance(raw_results, list):
            results_list = raw_results
        else:
            results_list = []
            
        sources: List[SearchSource] = []
        for r in results_list:
            if isinstance(r, dict):
                sources.append(SearchSource(
                    title=r.get("title", "Untitled Source"),
                    url=r.get("url", ""),
                    content=r.get("content", "")
                ))
        return sources

# Default shared search tool instance
search_tool = TavilySearchTool(max_results=3)
