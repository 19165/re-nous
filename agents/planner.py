from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from schemas import PlannerOutput
from config import llm
from agents.utils import parse_pydantic_response

# Initialize the Pydantic parser for PlannerOutput
planner_parser = PydanticOutputParser(pydantic_object=PlannerOutput)

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

def run_planner(question: str) -> PlannerOutput:
    """
    Executes the planner agent to split the main question into sub-questions.
    
    Args:
        question (str): The primary research question.
        
    Returns:
        PlannerOutput: Structured object containing original question and sub-questions.
    """
    # Format the prompt
    formatted_prompt = planner_prompt.format(question=question)
    
    # Invoke LLM
    response = llm.invoke(formatted_prompt)
    
    # Parse output using our robust helper
    parsed_output = parse_pydantic_response(response.content, planner_parser)
    return parsed_output
