from typing import List, Dict, Any, Tuple
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from schemas import WriterOutput
from config import llm, MAX_TOKENS_WRITER
from utils.helpers import parse_pydantic_response, extract_token_usage
from utils.logger import logger
from agents.base_agent import BaseAgent

# Initialize the Pydantic parser for WriterOutput
writer_parser = PydanticOutputParser(pydantic_object=WriterOutput)

# Dedicated model binding for Writer (large capacity 3500 tokens to prevent JSON truncation)
writer_llm = llm.bind(options={"num_predict": MAX_TOKENS_WRITER})

# Set up the prompt template
writer_prompt_template = """You are an expert technical writer. Your task is to synthesize the research findings gathered from multiple sub-questions into a cohesive, comprehensive, and well-structured report.

Original Topic/Question: {question}

Research Findings:
{findings}

{format_instructions}

Requirements:
- Structure the report logically into multiple sections (using ReportSection format).
- In the section content, cite your sources inline using markdown brackets like [1], [2], etc., corresponding to the indices of URLs in the citations list.
- Keep the writing clear, professional, and dense with facts from the search findings.
- Return only the raw JSON output matching the format instructions. Do not include any explanations, markdown code blocks, or thinking/reasoning tags.
"""

writer_prompt = PromptTemplate(
    template=writer_prompt_template,
    input_variables=["question", "findings"],
    partial_variables={"format_instructions": writer_parser.get_format_instructions()}
)

class WriterAgent(BaseAgent):
    """Agent responsible for synthesizing research results into a structured final report."""
    
    name: str = "Writer Agent"
    role: str = "Report Synthesizer & Editor"
    
    def run(self, question: str, findings: List[Dict[str, Any]]) -> Tuple[WriterOutput, int]:
        """Executes report synthesis from findings and returns (WriterOutput, tokens)."""
        logger.info("[bold yellow]📝 Synthesizing final report with Writer Agent...[/bold yellow]")
        
        # Format findings into a readable string for the prompt
        formatted_findings = ""
        for idx, f in enumerate(findings, 1):
            sub_q = f.get("sub_question", "")
            formatted_findings += f"\n--- Sub-question {idx}: {sub_q} ---\n"
            sources = f.get("sources", [])
            for s_idx, s in enumerate(sources, 1):
                title = s.get("title", "Unknown Source")
                url = s.get("url", "")
                content = s.get("content", "")
                formatted_findings += f"Source [{s_idx}]: {title} ({url})\nContent: {content}\n\n"

        formatted_prompt = writer_prompt.format(question=question, findings=formatted_findings)
        response = writer_llm.invoke(formatted_prompt)
        parsed_output = parse_pydantic_response(response.content, writer_parser)
        tokens = extract_token_usage(response, formatted_prompt)
        logger.info(f"📝 Report synthesis complete (Tokens used: [yellow]{tokens}[/yellow])")
        return parsed_output, tokens

# Functional wrapper for LangGraph nodes and backward compatibility
def run_writer(question: str, findings: List[Dict[str, Any]]) -> Tuple[WriterOutput, int]:
    agent = WriterAgent()
    return agent.run(question, findings)
