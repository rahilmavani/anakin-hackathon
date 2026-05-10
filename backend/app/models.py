from typing import Any
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    query: str = Field(min_length=5)


class TenderIntent(BaseModel):
    business_category: str | None = None
    location: str | None = None
    max_contract_value: int | None = None
    min_contract_value: int | None = None
    certificates: list[str] = []
    experience_years: int | None = None
    deadline_min_days: int | None = None
    max_emd: int | None = None
    turnover_limit: int | None = None
    keywords: list[str] = []


class Tender(BaseModel):
    id: str
    title: str | None = None
    source_url: str
    source_portal: str | None = None
    location: str | None = None
    estimated_value: int | None = None
    deadline: str | None = None
    deadline_iso: str | None = None
    days_left: int | None = None
    emd: int | None = None
    tender_fee: int | None = None
    eligibility: list[str] = []
    required_documents: list[str] = []
    apply_link: str | None = None
    risk_flags: list[str] = []
    why_matches: list[str] = []
    fit_score: int = 0
    recommendation: str = "Review Carefully"


class FinalResult(BaseModel):
    summary: str
    top_recommendation: Tender | None = None
    tenders: list[Tender] = []
    sources: list[str] = []
    action_plan: list[str] = []
    risk_flags: list[str] = []


class AgentState(BaseModel):
    user_query: str
    intent: TenderIntent | None = None
    search_queries: list[str] = []
    candidate_urls: list[str] = []
    scraped_pages: list[dict[str, Any]] = []
    tenders: list[Tender] = []
    sources: list[str] = []
    attempt_count: int = 0
    done: bool = False
