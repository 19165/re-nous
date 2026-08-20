from typing import Any, Tuple, Optional
from langchain_core.prompts import PromptTemplate
from schemas import ResearcherOutput
from config import llm
from tools.search_tool import search_tool, TavilySearchTool
from utils.helpers import extract_token_usage
from utils.logger import logger
from agents.base_agent import BaseAgent

# Query Optimizer Prompt Template
query_opt_prompt_template = """You are an Expert Search Query Optimizer. Your task is to convert a research sub-question into a concise, high-impact search engine query (3 to 8 keywords). 

[CONTEXT]
Main Topic: {main_topic}
Sub-question: {sub_question}

[RULES]
1. Remove all filler words, conversational phrasing, and question formatting.
2. Focus strictly on core entities, concepts, and domain terms.
3. Keep the query grounded in the Main Topic so it does not lose context.
4. Return ONLY the plain search query string. Do not include quotes, markdown code blocks, or any explanations.
"""

query_opt_prompt = PromptTemplate(
    template=query_opt_prompt_template,
    input_variables=["main_topic", "sub_question"]
)

class ResearchAgent(BaseAgent):
    """Agent responsible for optimizing search queries and conducting web research."""
    
    name: str = "Research Agent"
    role: str = "Query Optimizer & Web Researcher"
    
    def __init__(self, tool: TavilySearchTool = search_tool):
        self.tool = tool

    def optimize_query(self, main_topic: str, sub_question: str) -> Tuple[str, int]:
        """Converts conversational sub-question into high-density keywords via LLM."""
        effective_topic = main_topic if main_topic else sub_question
        formatted_prompt = query_opt_prompt.format(
            main_topic=effective_topic,
            sub_question=sub_question
        )
        response = llm.invoke(formatted_prompt)
        raw_query = str(getattr(response, "content", response)).strip()
        # Clean quotes and backticks defensively
        clean_query = raw_query.strip("\"'`").strip()
        tokens = extract_token_usage(response, formatted_prompt)
        return clean_query if clean_query else sub_question, tokens
        
    def run(self, sub_question: str, main_topic: str = "") -> Tuple[ResearcherOutput, int]:
        """Synchronous execution with query optimization."""
        search_query, tokens = self.optimize_query(main_topic, sub_question)
        logger.info(f"🎯 [bold cyan]Optimized Query:[/bold cyan] '{search_query}' (Tokens used: [yellow]{tokens}[/yellow])")
        sources = self.tool.invoke(search_query)
        return ResearcherOutput(
            sub_question=sub_question,
            sources=sources
        ), tokens
        
    async def arun(self, sub_question: str, main_topic: str = "") -> Tuple[ResearcherOutput, int]:
        """Asynchronous execution with query optimization."""
        search_query, tokens = self.optimize_query(main_topic, sub_question)
        logger.info(f"🎯 [bold cyan]Optimized Query:[/bold cyan] '{search_query}' (Tokens used: [yellow]{tokens}[/yellow])")
        sources = await self.tool.ainvoke(search_query)
        return ResearcherOutput(
            sub_question=sub_question,
            sources=sources
        ), tokens

# Functional wrapper for LangGraph nodes and backward compatibility
async def run_researcher(sub_question: str, main_topic: str = "") -> Tuple[ResearcherOutput, int]:
    agent = ResearchAgent()
    return await agent.arun(sub_question, main_topic)
