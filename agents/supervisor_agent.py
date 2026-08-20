from typing import List, Dict, Any, Optional, Tuple
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from schemas import SupervisorOutput, BudgetConfig
from config import llm, default_budget, MAX_TOKENS_SUPERVISOR
from utils.helpers import parse_pydantic_response, extract_token_usage
from utils.logger import logger
from agents.base_agent import BaseAgent

# Initialize Pydantic Parser for SupervisorOutput
supervisor_parser = PydanticOutputParser(pydantic_object=SupervisorOutput)

# Dedicated model binding for Supervisor evaluation
supervisor_llm = llm.bind(num_predict=MAX_TOKENS_SUPERVISOR)

# User-defined Supervisor Prompt Template
supervisor_prompt_template = """You are a rigorous Research Supervisor and Quality Assurance Evaluator.
Your goal is to evaluate if the research findings sufficiently answer the planned sub-questions and decide if a revision is necessary.

[INPUT DATA]
* Original Topic: {question}
* Current Revision Count: {revision_count}
* Sub-Questions & Findings: 
{findings_context}

[EVALUATION CRITERIA]
1. Completeness: Are the sub-questions answered with factual, meaningful information?
2. Source Quality: Are the search sources valid, relevant, and non-empty?
3. Revision Decision: Is a second research pass strictly justified? (Only request a revision if critical gaps exist and the revision count allows it).
4. Actionable Feedback: If a revision is needed, provide a concise, highly targeted refined search query.

[OUTPUT INSTRUCTIONS]
{format_instructions}
Return ONLY valid JSON matching the exact schema. Do not include markdown formatting (such as ```json), reasoning tags, or any conversational text outside the JSON object.
"""

supervisor_prompt = PromptTemplate(
    template=supervisor_prompt_template,
    input_variables=["question", "revision_count", "findings_context"],
    partial_variables={"format_instructions": supervisor_parser.get_format_instructions()}
)

class SupervisorAgent(BaseAgent):
    """Quality Assurance and Budget Gatekeeper Agent."""
    
    name: str = "Supervisor Agent"
    role: str = "Research QA & Budget Gatekeeper"
    
    def evaluate(
        self,
        question: str,
        findings: List[Dict[str, Any]],
        revision_count: int = 0,
        elapsed_time: float = 0.0,
        current_tokens: int = 0,
        budget: Optional[BudgetConfig] = None
    ) -> Tuple[SupervisorOutput, int]:
        """
        Performs hybrid evaluation: checks hard budget constraints before invoking LLM critic.
        Returns Tuple of (SupervisorOutput, tokens_used).
        """
        active_budget = budget or default_budget
        
        # --- Layer 1: Deterministic Hard Budget Gate ---
        if revision_count >= active_budget.max_revisions:
            logger.info(f"🛡️ [bold yellow]Supervisor Budget Gate:[/bold yellow] Max revision count ({active_budget.max_revisions}) reached. Passing to Writer.")
            return SupervisorOutput(
                approved=True,
                reasoning=f"Max revision limit ({active_budget.max_revisions}) reached. No further pass allowed."
            ), 0
            
        if elapsed_time >= active_budget.wall_clock_timeout_seconds:
            logger.info(f"🛡️ [bold yellow]Supervisor Budget Gate:[/bold yellow] Wall-clock timeout exceeded ({elapsed_time:.1f}s >= {active_budget.wall_clock_timeout_seconds}s). Passing to Writer.")
            return SupervisorOutput(
                approved=True,
                reasoning=f"Wall-clock timeout of {active_budget.wall_clock_timeout_seconds}s exceeded. Passing to Writer."
            ), 0
            
        if current_tokens >= active_budget.max_total_tokens:
            logger.info(f"🛡️ [bold yellow]Supervisor Budget Gate:[/bold yellow] Token ceiling exceeded ({current_tokens} >= {active_budget.max_total_tokens}). Passing to Writer.")
            return SupervisorOutput(
                approved=True,
                reasoning=f"Token ceiling ({active_budget.max_total_tokens}) exceeded. Passing to Writer."
            ), 0

        # --- Layer 2: LLM Evaluation ---
        logger.info(f"🛡️ [bold yellow]Supervisor Agent:[/bold yellow] Evaluating research quality (Revision {revision_count})...")
        
        # Format findings context
        findings_context = ""
        for idx, f in enumerate(findings, 1):
            sub_q = f.get("sub_question", "Unknown")
            sources = f.get("sources", [])
            findings_context += f"\n--- Sub-question {idx}: {sub_q} ---\n"
            findings_context += f"Total Sources Found: {len(sources)}\n"
            for s_idx, s in enumerate(sources, 1):
                title = s.get("title", "Untitled")
                url = s.get("url", "")
                content = s.get("content", "")
                findings_context += f"Source [{s_idx}]: {title} ({url})\nContent: {content}\n"
                
        formatted_prompt = supervisor_prompt.format(
            question=question,
            revision_count=revision_count,
            findings_context=findings_context
        )
        
        response = supervisor_llm.invoke(formatted_prompt)
        parsed_output: SupervisorOutput = parse_pydantic_response(response.content, supervisor_parser)
        tokens = extract_token_usage(response, formatted_prompt)
        
        status_style = "bold green" if parsed_output.approved else "bold magenta"
        status_text = "APPROVED" if parsed_output.approved else "REVISION REQUESTED"
        logger.info(f"🛡️ Supervisor Decision: [{status_style}]{status_text}[/{status_style}] (Tokens used: [yellow]{tokens}[/yellow])")
        logger.info(f"Supervisor Reasoning: [cyan]{parsed_output.reasoning}[/cyan]")
        return parsed_output, tokens

    def run(self, *args: Any, **kwargs: Any) -> Tuple[SupervisorOutput, int]:
        """Sync run wrapper delegating to evaluate."""
        return self.evaluate(*args, **kwargs)

# Functional wrapper for LangGraph orchestrator
def run_supervisor(
    question: str,
    findings: List[Dict[str, Any]],
    revision_count: int = 0,
    elapsed_time: float = 0.0,
    current_tokens: int = 0,
    budget: Optional[BudgetConfig] = None
) -> Tuple[SupervisorOutput, int]:
    agent = SupervisorAgent()
    return agent.evaluate(
        question=question,
        findings=findings,
        revision_count=revision_count,
        elapsed_time=elapsed_time,
        current_tokens=current_tokens,
        budget=budget
    )
