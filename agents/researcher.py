from schemas import ResearcherOutput, SearchSource
from config import search_tool, logger

async def run_researcher(sub_question: str) -> ResearcherOutput:
    """
    Executes web search for a sub-question asynchronously and returns sources.
    
    Args:
        sub_question (str): The specific question to search.
        
    Returns:
        ResearcherOutput: Structured sources and URLs.
    """
    logger.info(f"Initiating async search for: [cyan]'{sub_question}'[/cyan]")
    
    # Invoke Tavily Search tool asynchronously
    raw_results = await search_tool.ainvoke(sub_question)
    
    sources = []
    
    # Extract search results list
    if isinstance(raw_results, dict) and "results" in raw_results:
        results_list = raw_results["results"]
    elif isinstance(raw_results, list):
        results_list = raw_results
    else:
        results_list = []
        
    for r in results_list:
        if isinstance(r, dict):
            sources.append(SearchSource(
                title=r.get("title", "Untitled Source"),
                url=r.get("url", ""),
                content=r.get("content", "")
            ))
            
    logger.info(f"Completed async search for: [cyan]'{sub_question}'[/cyan] (Found {len(sources)} sources)")
    return ResearcherOutput(
        sub_question=sub_question,
        sources=sources
    )
