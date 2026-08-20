from typing import Any
from schemas import ResearcherOutput
from tools.search_tool import search_tool, TavilySearchTool
from utils.logger import logger
from agents.base_agent import BaseAgent

class ResearchAgent(BaseAgent):
    """Agent responsible for conducting web searches for a specific sub-question."""
    
    name: str = "Research Agent"
    role: str = "Web Researcher & Fact Gatherer"
    
    def __init__(self, tool: TavilySearchTool = search_tool):
        self.tool = tool
        
    def run(self, sub_question: str) -> ResearcherOutput:
        """Synchronous execution (delegates to tool invoke)."""
        sources = self.tool.invoke(sub_question)
        return ResearcherOutput(
            sub_question=sub_question,
            sources=sources
        )
        
    async def arun(self, sub_question: str) -> ResearcherOutput:
        """Asynchronous execution (delegates to tool ainvoke)."""
        logger.info(f"🚀 Initiating async research for: [cyan]'{sub_question}'[/cyan]")
        sources = await self.tool.ainvoke(sub_question)
        return ResearcherOutput(
            sub_question=sub_question,
            sources=sources
        )

# Functional wrapper for LangGraph nodes and backward compatibility
async def run_researcher(sub_question: str) -> ResearcherOutput:
    agent = ResearchAgent()
    return await agent.arun(sub_question)
