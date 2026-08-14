from pydantic import BaseModel, Field
from typing import List

# --- Planner Schema ---
class PlannerOutput(BaseModel):
    original_question: str = Field(description="The original user query")
    sub_questions: List[str] = Field(description="List of exactly 3 distinct, specific sub-questions to investigate")

# --- Researcher Schema (Programmatic) ---
class SearchSource(BaseModel):
    title: str = Field(description="Title of the source webpage")
    url: str = Field(description="URL of the source webpage")
    content: str = Field(description="Relevant text snippet from the webpage")

class ResearcherOutput(BaseModel):
    sub_question: str = Field(description="The sub-question that was researched")
    sources: List[SearchSource] = Field(description="List of search result sources containing content and URLs")

# --- Writer Schema ---
class ReportSection(BaseModel):
    section_title: str = Field(description="Title of this section")
    section_content: str = Field(description="Content of this section with inline markdown citations like [1], [2] pointing to references in the citations list")

class WriterOutput(BaseModel):
    title: str = Field(description="Title of the research report")
    summary: str = Field(description="A brief executive summary of the entire report")
    sections: List[ReportSection] = Field(description="List of detailed sections containing content and citations")
    citations: List[str] = Field(description="List of all unique source URLs referenced in the sections. The index corresponds to the inline citations [1], [2], etc.")
