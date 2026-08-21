import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from api.app import app
from schemas import WriterOutput, ReportSection
from utils.citation_validator import validate_report_citations
from utils.logger import console

@pytest.mark.asyncio
async def test_health_and_root():
    """Test health check and root endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Health endpoint
        res = await client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

        # Root endpoint
        res_root = await client.get("/")
        assert res_root.status_code == 200
        assert "endpoints" in res_root.json()
    console.print("[bold green]✅ Health & Root endpoints passed![/bold green]")

@pytest.mark.asyncio
async def test_submit_and_get_research():
    """Test POST /research, GET /research/{id}, and 404 handling."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Submit research
        post_res = await client.post(
            "/research",
            json={"question": "What is Quantum Machine Learning?", "timeout": 30.0}
        )
        assert post_res.status_code == 202
        data = post_res.json()
        assert "run_id" in data
        assert data["status"] in ["PENDING", "RUNNING"]
        run_id = data["run_id"]

        # 2. Get status immediately
        get_res = await client.get(f"/research/{run_id}")
        assert get_res.status_code == 200
        status_data = get_res.json()
        assert status_data["run_id"] == run_id
        assert status_data["question"] == "What is Quantum Machine Learning?"

        # 3. Get trace (might be empty or have initial steps)
        trace_res = await client.get(f"/research/{run_id}/trace")
        assert trace_res.status_code == 200
        assert isinstance(trace_res.json(), list)

        # 4. Test 404 for non-existent run_id
        not_found_res = await client.get("/research/run-non-existent-9999")
        assert not_found_res.status_code == 404
    console.print("[bold green]✅ Research API endpoints (POST/GET/Trace/404) passed![/bold green]")

def test_citation_validator_logic():
    """Test Citation Validator with matching and mismatched citations."""
    sample_findings = [
        {
            "sub_question": "Quantum ML overview",
            "sources": [
                {"title": "QML Guide", "url": "https://example.com/qml-guide"},
                {"title": "Quantum AI", "url": "https://example.com/quantum-ai"}
            ]
        }
    ]

    # Valid report
    valid_report = WriterOutput(
        title="QML Report",
        summary="A study on quantum algorithms.",
        sections=[
            ReportSection(
                section_title="Introduction",
                section_content="Quantum computing accelerates ML tasks [1]."
            )
        ],
        citations=["https://example.com/qml-guide"]
    )
    validated, warnings = validate_report_citations(valid_report, sample_findings)
    assert len(warnings) == 0

    # Invalid report with hallucinated URL and out-of-bounds citation
    invalid_report = WriterOutput(
        title="Invalid QML Report",
        summary="Summary",
        sections=[
            ReportSection(
                section_title="Section 1",
                section_content="This references an out-of-bound citation [5] and a fake url [1]."
            )
        ],
        citations=["https://fake-hallucinated-site.com/fake"]
    )
    validated_inv, warnings_inv = validate_report_citations(invalid_report, sample_findings)
    assert len(warnings_inv) == 2  # 1 for out of bounds, 1 for unverified URL
    console.print("[bold green]✅ Citation validator unit test passed![/bold green]")

if __name__ == "__main__":
    asyncio.run(test_health_and_root())
    asyncio.run(test_submit_and_get_research())
    test_citation_validator_logic()
