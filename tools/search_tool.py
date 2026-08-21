import re
import asyncio
import urllib.parse
from typing import List, Dict, Any, Union, Optional, Tuple
from langchain_tavily import TavilySearch
from tools.base_tool import BaseTool
from schemas import SearchSource, SearchStatus
from config import (
    TAVILY_CHUNKS_PER_SOURCE,
    TAVILY_INCLUDE_RAW_CONTENT,
    MAX_RAW_CONTENT_CHARS,
    default_budget,
)
from utils.logger import logger

def extract_domain(url: str) -> str:
    """Extracts base normalized domain from URL (e.g. 'en.wikipedia.org' -> 'wikipedia.org')."""
    if not url:
        return ""
    try:
        netloc = urllib.parse.urlparse(url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""

class TavilySearchTool(BaseTool):
    """Encapsulation adapter for Tavily Web Search with domain capping and resilient failure handling."""
    
    name: str = "tavily_search"
    description: str = "Search the web for current facts, articles, and research sources."
    
    def __init__(
        self,
        max_results: int = 3,
        chunks_per_source: int = TAVILY_CHUNKS_PER_SOURCE,
        include_raw_content: Union[bool, str] = TAVILY_INCLUDE_RAW_CONTENT,
        max_sources_per_domain: int = default_budget.max_sources_per_domain_sub_q
    ):
        self.max_results = max_results
        self.chunks_per_source = chunks_per_source
        self.include_raw_content = include_raw_content
        self.max_sources_per_domain = max_sources_per_domain
        self._tool = TavilySearch(
            max_results=max_results,
            chunks_per_source=chunks_per_source,
            include_raw_content=include_raw_content
        )
        
    def invoke(self, query: str, **kwargs: Any) -> Tuple[List[SearchSource], SearchStatus, Optional[str]]:
        """Synchronous search invocation with structured failure handling."""
        try:
            raw_results = self._tool.invoke(query)
            sources = self._format_results(raw_results)
            if not sources:
                return [], SearchStatus.NO_RESULTS, "No relevant search sources found."
            return sources, SearchStatus.SUCCESS, None
        except Exception as e:
            return self._handle_exception(e, query)
        
    async def ainvoke(self, query: str, **kwargs: Any) -> Tuple[List[SearchSource], SearchStatus, Optional[str]]:
        """Asynchronous search invocation with structured failure handling."""
        logger.info(f"🔍 [bold cyan]Searching Tavily for:[/bold cyan] '{query}'")
        try:
            raw_results = await self._tool.ainvoke(query)
            sources = self._format_results(raw_results)
            if not sources:
                logger.warning(f"⚠️ No results returned for query: '{query}'")
                return [], SearchStatus.NO_RESULTS, "No search results returned from provider."
                
            logger.info(f"✅ Found [bold green]{len(sources)}[/bold green] sources (domain capped) for: '{query}'")
            return sources, SearchStatus.SUCCESS, None
        except Exception as e:
            return self._handle_exception(e, query)

    def _handle_exception(self, e: Exception, query: str) -> Tuple[List[SearchSource], SearchStatus, str]:
        """Maps runtime and network exceptions to structured SearchStatus."""
        err_msg = str(e).lower()
        if "timeout" in err_msg or isinstance(e, (asyncio.TimeoutError, TimeoutError)):
            status = SearchStatus.TIMED_OUT
            logger.warning(f"⏱️ [bold red]Search Timed Out:[/bold red] '{query}' -> {e}")
        elif "429" in err_msg or "rate limit" in err_msg or "too many requests" in err_msg:
            status = SearchStatus.RATE_LIMITED
            logger.warning(f"🚫 [bold red]Search Rate Limited:[/bold red] '{query}' -> {e}")
        elif "403" in err_msg or "401" in err_msg or "paywall" in err_msg or "forbidden" in err_msg:
            status = SearchStatus.PAYWALLED
            logger.warning(f"🔒 [bold red]Search Access Forbidden/Paywalled:[/bold red] '{query}' -> {e}")
        else:
            status = SearchStatus.ERROR
            logger.error(f"❌ [bold red]Search Error:[/bold red] '{query}' -> {e}")
            
        return [], status, str(e)

    @staticmethod
    def _clean_markdown_text(text: str) -> str:
        """Strips excessive newlines and image tags from raw markdown content."""
        if not text:
            return ""
        cleaned = re.sub(r"!\[.*?\]\(.*?\)", "", text)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()
        
    def _format_results(self, raw_results: Union[Dict[str, Any], List[Any]]) -> List[SearchSource]:
        """Parses and formats raw Tavily results, enforcing per-domain capping and URL deduplication."""
        if isinstance(raw_results, dict) and "results" in raw_results:
            results_list = raw_results["results"]
        elif isinstance(raw_results, list):
            results_list = raw_results
        else:
            results_list = []
            
        sources: List[SearchSource] = []
        seen_urls = set()
        domain_counts: Dict[str, int] = {}
        
        for r in results_list:
            if not isinstance(r, dict):
                continue
                
            url = r.get("url", "")
            if not url or url in seen_urls:
                continue
                
            domain = extract_domain(url)
            current_domain_count = domain_counts.get(domain, 0)
            if domain and current_domain_count >= self.max_sources_per_domain:
                logger.info(f"🛡️ [dim]Domain Cap:[/dim] Skipping extra source from '[dim]{domain}[/dim]'")
                continue
                
            full_raw = r.get("raw_content")
            snippet = r.get("content", "")
            
            if full_raw and isinstance(full_raw, str) and len(full_raw.strip()) > 0:
                cleaned = self._clean_markdown_text(full_raw)
                primary_content = cleaned[:MAX_RAW_CONTENT_CHARS]
            else:
                primary_content = snippet or ""
                
            seen_urls.add(url)
            if domain:
                domain_counts[domain] = current_domain_count + 1
                
            sources.append(SearchSource(
                title=r.get("title", "Untitled Source"),
                url=url,
                content=primary_content,
                raw_content=full_raw
            ))
            
        return sources

# Default shared search tool instance with domain capping and semantic chunks enabled
search_tool = TavilySearchTool(
    max_results=3,
    chunks_per_source=TAVILY_CHUNKS_PER_SOURCE,
    include_raw_content=TAVILY_INCLUDE_RAW_CONTENT,
    max_sources_per_domain=default_budget.max_sources_per_domain_sub_q
)
