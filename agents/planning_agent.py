from typing import Tuple
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from schemas import PlannerOutput
from config import llm, MAX_TOKENS_PLANNER
from utils.helpers import parse_pydantic_response, extract_token_usage
from utils.logger import logger
from agents.base_agent import BaseAgent

# Initialize the Pydantic parser for PlannerOutput
planner_parser = PydanticOutputParser(pydantic_object=PlannerOutput)

# Dedicated model binding with generation ceiling
planner_llm = llm.bind(options={"num_predict": MAX_TOKENS_PLANNER})

# Set up the prompt template
planner_prompt_template = """You are an expert research planner. Break down the user's research question into exactly 3 distinct, specific sub-questions that can be researched independently using a search engine.

Original Research Question: {question}

{format_instructions}

Return only the raw JSON output matching the format instructions. Do not add any explanation, introductory text, markdown code blocks, or thinking/reasoning tags.
"""

planner_prompt = PromptTemplate(
    template=planner_prompt_template,
    input_variables=["question"],
    partial_variables={"format_instructions": planner_parser.get_format_instructions()}
)

class PlanningAgent(BaseAgent):
    """Agent responsible for breaking down a complex query into actionable sub-questions."""
    
    name: str = "Planning Agent"
    role: str = "Research Query Planner & Decomposer"
    
    def run(self, question: str) -> Tuple[PlannerOutput, int]:
        """Executes query decomposition and returns parsed output with token count."""
        logger.info(f"🧭 Planning research sub-tasks for: [cyan]'{question}'[/cyan]")
        formatted_prompt = planner_prompt.format(question=question)
        response = planner_llm.invoke(formatted_prompt)
        parsed_output = parse_pydantic_response(response.content, planner_parser)
        tokens = extract_token_usage(response, formatted_prompt)
        logger.info(f"🧭 Planning complete (Tokens used: [yellow]{tokens}[/yellow])")
        return parsed_output, tokens

# Functional wrapper for LangGraph nodes and backward compatibility
def run_planner(question: str) -> Tuple[PlannerOutput, int]:
    agent = PlanningAgent()
    return agent.run(question)
