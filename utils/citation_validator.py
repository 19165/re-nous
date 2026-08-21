import re
from typing import List, Dict, Any, Tuple
from schemas import WriterOutput
from utils.logger import logger

def validate_report_citations(
    report: WriterOutput, findings: List[Dict[str, Any]]
) -> Tuple[WriterOutput, List[str]]:
    """
    Validates citation indices [1], [2] within report sections against the citations list
    and verifies that each cited URL was genuinely discovered by the Researcher agents.
    """
    warnings: List[str] = []
    
    # 1. Collect all authoritative URLs found in researcher findings
    discovered_urls = set()
    for item in findings or []:
        for src in item.get("sources", []):
            url = src.get("url")
            if url:
                discovered_urls.add(url.strip())

    total_citations = len(report.citations)
    cited_indices_in_text = set()

    # 2. Inspect citations in each section
    for section in report.sections:
        matches = re.findall(r"\[(\d+)\]", section.section_content)
        for match in matches:
            idx = int(match)
            cited_indices_in_text.add(idx)
            
            # Check 1: Index bounds
            if idx < 1 or idx > total_citations:
                msg = f"Citation [{idx}] in section '{section.section_title}' is out of bounds (Total citations: {total_citations})."
                warnings.append(msg)
                logger.warning(f"⚠️ {msg}")
            else:
                # Check 2: Existence in discovered findings
                cited_url = report.citations[idx - 1].strip()
                if cited_url not in discovered_urls:
                    msg = f"Citation [{idx}] ({cited_url}) in section '{section.section_title}' was not found in verified research sources."
                    warnings.append(msg)
                    logger.warning(f"⚠️ {msg}")

    # Check 3: Any citations listed but never referenced in text
    for i in range(1, total_citations + 1):
        if i not in cited_indices_in_text:
            url = report.citations[i - 1]
            logger.debug(f"ℹ️ Citation [{i}] ({url}) is listed in bibliography but not referenced inline.")

    # Attach warnings to WriterOutput
    report.validation_warnings = warnings
    if warnings:
        logger.warning(f"⚠️ Citation validation completed with {len(warnings)} warning(s).")
    else:
        logger.info("✅ [bold green]All citations in report successfully validated against source findings![/bold green]")

    return report, warnings
