"""LLM-based relevance + freshness filter for tender candidates.

Uses any OpenAI-compatible chat completions endpoint (configured via env).
Default backend: OpenRouter with model openai/gpt-5.5.

The LLM is asked to return strict JSON for each candidate tender:
- keep: bool
- reason_drop: short reason if drop
- deadline_iso: normalized ISO date if known
- days_left: integer days from today (negative if past)
- why_matches: 1-3 short bullet phrases tying tender to the user's intent
- recommendation: one of Apply / Maybe Apply / Review Carefully / Skip
- fit_score: 0-100 integer

Falls back to no-op if no API key is configured or the call fails.
"""

from __future__ import annotations

import asyncio
import json
from datetime import date, datetime
from typing import Any

import httpx

from .config import settings
from .models import Tender, TenderIntent


SYSTEM_PROMPT = """You are TenderFlow's relevance filter for Indian government/private tenders.

You will receive:
- a user intent (what kind of contracts the user wants)
- today's date
- a list of candidate tenders, each with a title, snippet, source URL, and pre-extracted fields

For EACH candidate, decide:
1. keep — true ONLY if ALL of the following are true:
   (a) it is a real tender notice (not a generic listing/index page, not a portal homepage),
   (b) it matches the user's category AND location intent,
   (c) the deadline is today or in the future (i.e. days_left >= 0).
   If you cannot determine the deadline at all, set keep=false with reason_drop="Deadline could not be determined".
2. reason_drop — one short sentence if dropped. Empty string otherwise.
3. deadline_iso — best-guess ISO 8601 date (YYYY-MM-DD) if the snippet/title/url contains one. Null if unknown.
4. days_left — integer days from today's date to deadline_iso. Null if unknown. **MUST be a real calculation, not a guess.** Negative if past.
5. why_matches — 1-3 short bullet phrases tying the tender to the user's intent (category, location, budget, certificates).
6. recommendation — one of Apply / Maybe Apply / Review Carefully / Skip.
7. fit_score — integer 0-100.

CRITICAL DROP RULES (no exceptions):
- If days_left is negative (deadline already passed) → keep=false with reason_drop="Deadline already passed".
- If the snippet/title contains only old years like 2020/2021/2022/2023 with no explicit future date → keep=false with reason_drop="Stale listing — dates indicate prior years".
- If the URL or title is a generic listing/aggregator ("active tenders", "live tenders", "279 tenders in...", "/cctv-tenders/karnataka", category index pages) with NO single-tender details → keep=false with reason_drop="Aggregator/listing page, not a single tender".
- If the deadline is unknown AND the snippet doesn't clearly describe a single ongoing tender → keep=false with reason_drop="Unverified — no single-tender details".

Return ONLY JSON in this exact shape (no markdown, no prose):
{"results": [{"id": "...", "keep": true, "reason_drop": "", "deadline_iso": "2026-05-22", "days_left": 12, "why_matches": ["..."], "recommendation": "Apply", "fit_score": 88}, ...]}
"""


def _summarize_tender(t: Tender) -> dict[str, Any]:
    return {
        "id": t.id,
        "title": (t.title or "")[:240],
        "source_url": t.source_url,
        "source_portal": t.source_portal,
        "estimated_value_inr": t.estimated_value,
        "emd_inr": t.emd,
        "deadline_text": t.deadline,
        "eligibility": t.eligibility[:6],
    }


async def _filter_chunk(
    client: httpx.AsyncClient,
    intent: TenderIntent,
    chunk: list[Tender],
) -> tuple[list[dict[str, Any]], str | None]:
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "today": date.today().isoformat(),
                        "intent": intent.model_dump(),
                        "candidates": [_summarize_tender(t) for t in chunk],
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "response_format": {"type": "json_object"},
        # Stay under the OpenRouter per-key per-request token reservation cap.
        "max_tokens": 1000,
        "temperature": 0.1,
        # Reasoning models (gpt-5.x) think before answering. "low" is plenty for
        # JSON classification and keeps cost + latency predictable.
        "reasoning": {"effort": "low"},
    }
    try:
        res = await client.post(
            f"{settings.llm_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://tenderflow.local",
                "X-Title": "TenderFlow",
            },
            json=payload,
        )
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        return [], str(e)[:200]

    content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
    try:
        parsed = json.loads(content)
        return parsed.get("results") or [], None
    except json.JSONDecodeError as e:
        # Best-effort recovery: extract individual {...} objects from a truncated stream
        salvaged: list[dict[str, Any]] = []
        depth = 0
        start = -1
        for i, ch in enumerate(content):
            if ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and start >= 0:
                    try:
                        obj = json.loads(content[start : i + 1])
                        if isinstance(obj, dict) and obj.get("id"):
                            salvaged.append(obj)
                    except json.JSONDecodeError:
                        pass
                    start = -1
        if salvaged:
            return salvaged, f"recovered {len(salvaged)} of N (truncated: {e.msg})"
        return [], str(e)[:200]


async def llm_filter_tenders(
    intent: TenderIntent,
    tenders: list[Tender],
) -> tuple[list[Tender], dict[str, Any]]:
    """Returns (kept_tenders_in_original_order, meta)."""
    meta: dict[str, Any] = {"used_llm": False, "model": settings.llm_model, "kept": 0, "dropped": 0}
    if not settings.openrouter_api_key or not tenders:
        return tenders, meta

    # Cap and chunk: each chunk must fit in the per-request token reservation.
    # 6 candidates × ~80 tokens of JSON output each ≈ 480 tokens, well under 1000.
    candidates = tenders[:18]
    chunks: list[list[Tender]] = [candidates[i : i + 6] for i in range(0, len(candidates), 6)]
    errors: list[str] = []

    async with httpx.AsyncClient(timeout=120) as client:
        chunk_results = await asyncio.gather(
            *(_filter_chunk(client, intent, c) for c in chunks)
        )

    results: list[dict[str, Any]] = []
    for chunk_verdicts, err in chunk_results:
        results.extend(chunk_verdicts)
        if err:
            errors.append(err)

    by_id: dict[str, dict[str, Any]] = {r.get("id"): r for r in results if isinstance(r, dict) and r.get("id")}

    kept: list[Tender] = []
    dropped = 0
    for t in tenders:
        verdict = by_id.get(t.id)
        if not verdict:
            kept.append(t)
            continue
        if verdict.get("keep") is False:
            dropped += 1
            continue
        # Apply LLM enrichments
        di = verdict.get("deadline_iso")
        if isinstance(di, str) and di:
            t.deadline_iso = di
            try:
                parsed_date = datetime.fromisoformat(di).date()
                t.days_left = (parsed_date - date.today()).days
            except ValueError:
                pass
        dl = verdict.get("days_left")
        if isinstance(dl, int):
            t.days_left = dl
        wm = verdict.get("why_matches") or []
        if isinstance(wm, list):
            t.why_matches = [str(x) for x in wm if isinstance(x, (str, int))][:3]
        rec = verdict.get("recommendation")
        if isinstance(rec, str) and rec in {"Apply", "Maybe Apply", "Review Carefully", "Skip"}:
            t.recommendation = rec
        fs = verdict.get("fit_score")
        if isinstance(fs, int):
            t.fit_score = max(0, min(100, fs))
        # Drop stale-deadline risk if LLM gave a future days_left
        if t.days_left is not None and t.days_left >= 0:
            t.risk_flags = [r for r in t.risk_flags if not r.startswith("Deadline not detected")]
        kept.append(t)

    meta["used_llm"] = bool(by_id)
    meta["kept"] = len(kept)
    meta["dropped"] = dropped
    if errors:
        meta["error"] = "; ".join(errors[:3])
    return kept, meta
