import asyncio
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator
from urllib.parse import urlparse

from fastapi.encoders import jsonable_encoder

from .anakin_client import AnakinClient
from .config import settings
from .llm_filter import llm_filter_tenders
from .models import FinalResult, Tender, TenderIntent


INDIAN_LOCATIONS = [
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
    "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand",
    "karnataka", "kerala", "madhya pradesh", "maharashtra", "manipur",
    "meghalaya", "mizoram", "nagaland", "odisha", "punjab", "rajasthan",
    "sikkim", "tamil nadu", "telangana", "tripura", "uttar pradesh",
    "uttarakhand", "west bengal", "delhi", "ncr", "mumbai", "pune", "nagpur",
    "bengaluru", "bangalore", "mysuru", "mysore", "hyderabad", "chennai",
    "kolkata", "ahmedabad", "surat", "jaipur", "lucknow", "kanpur",
    "indore", "bhopal", "patna", "ranchi", "raipur", "guwahati",
    "thiruvananthapuram", "kochi", "coimbatore",
]

CATEGORY_KEYWORDS = {
    "cctv installation": ["cctv", "surveillance camera", "video surveillance"],
    "housekeeping": ["housekeeping", "cleaning", "sanitation", "janitorial"],
    "solar installation": ["solar", "rooftop solar", "photovoltaic", "pv panel"],
    "catering": ["catering", "canteen", "food service", "mess"],
    "it support": ["it support", "it amc", "computer amc", "desktop amc", "laptop amc"],
    "construction": ["construction", "civil work", "building work"],
    "electrical": ["electrical", "wiring", "electrification"],
    "plumbing": ["plumbing", "sanitary work"],
    "security services": ["security service", "security guard", "manpower security"],
    "manufacturing supply": ["supply of", "manufacturing", "fabrication"],
}


CERT_KEYWORDS = ["gst", "msme", "pan", "iso", "udyam", "startup india"]


def _to_inr_amount(num: float, unit: str) -> int:
    unit = unit.lower()
    if "crore" in unit or "cr" == unit:
        return int(num * 10_000_000)
    if "lakh" in unit or "lac" in unit:
        return int(num * 100_000)
    return int(num)


def _find_amount(text: str, prefix_re: str) -> int | None:
    """Find an amount described by a prefix like 'below|under|upto|max|less than'."""
    pat = rf"{prefix_re}\s*(?:rs\.?|inr|₹)?\s*([\d,.]+)\s*(crore|cr|lakh|lac|lacs|lakhs)?"
    m = re.search(pat, text, re.I)
    if not m:
        return None
    try:
        num = float(m.group(1).replace(",", ""))
    except ValueError:
        return None
    unit = m.group(2) or ""
    return _to_inr_amount(num, unit)


def parse_intent(query: str) -> TenderIntent:
    text = query.lower()

    # Location
    location: str | None = None
    for loc in INDIAN_LOCATIONS:
        if re.search(rf"\b{re.escape(loc)}\b", text):
            location = loc.title()
            break

    # Category
    category: str | None = None
    for canonical, keywords in CATEGORY_KEYWORDS.items():
        if any(k in text for k in keywords):
            category = canonical
            break

    # Max contract value: "below 25 lakh", "under 50 lakh", "less than 1 crore", "upto 25L"
    max_value = _find_amount(
        text,
        r"(?:below|under|upto|up\s*to|less\s*than|max(?:imum)?|not\s*more\s*than|<\s*=?)",
    )

    # Min contract value
    min_value = _find_amount(text, r"(?:above|over|more\s*than|>\s*=?|at\s*least|minimum)")

    # Max EMD
    max_emd = None
    emd_match = re.search(
        r"emd\s*(?:above|below|under|upto|up\s*to|less\s*than|max(?:imum)?|>|<)?\s*"
        r"(?:rs\.?|inr|₹)?\s*([\d,.]+)\s*(crore|cr|lakh|lac|lakhs|lacs)?",
        text,
        re.I,
    )
    if emd_match:
        try:
            num = float(emd_match.group(1).replace(",", ""))
            max_emd = _to_inr_amount(num, emd_match.group(2) or "")
        except ValueError:
            pass

    # Certificates
    certs = [c.upper() for c in CERT_KEYWORDS if re.search(rf"\b{c}\b", text)]

    # Experience
    exp = None
    m = re.search(r"(\d+)\s*\+?\s*years?\s*(?:of\s*)?(?:experience|exp)?", text)
    if m:
        exp = int(m.group(1))

    # Deadline minimum days
    days = None
    m = re.search(r"(?:closing|deadline|after)\s*(?:after\s*)?(\d+)\s*days?", text)
    if m:
        days = int(m.group(1))

    # Turnover
    turnover = _find_amount(text, r"turnover\s*(?:above|over|more\s*than|>)?")

    keywords = [w for w in [category, location] if w]
    return TenderIntent(
        business_category=category,
        location=location,
        max_contract_value=max_value,
        min_contract_value=min_value,
        certificates=certs,
        experience_years=exp,
        deadline_min_days=days,
        max_emd=max_emd,
        turnover_limit=turnover,
        keywords=keywords,
    )


def build_queries(intent: TenderIntent, raw_query: str) -> list[str]:
    """Return up to 3 high-signal queries. Each Anakin search costs credits, keep it lean."""
    category = intent.business_category or "service"
    location = intent.location or "India"
    year = datetime.now().year
    queries = [
        f"{category} tender {location} {year} closing date",
        f"site:eprocure.gov.in {category} {location} tender",
        f"site:gem.gov.in {category} {location} tender",
    ]
    seen, out = set(), []
    for q in queries:
        if q and q.lower() not in seen:
            out.append(q)
            seen.add(q.lower())
    return out[:3]


# --------- Tender extraction from search snippets and scraped pages ---------

AMOUNT_PATTERNS = [
    re.compile(r"(?:rs\.?|inr|₹)\s*([\d,.]+)\s*(crore|cr|lakh|lac|lakhs|lacs)?", re.I),
    re.compile(r"([\d,.]+)\s*(crore|cr|lakh|lac|lakhs|lacs)\b", re.I),
]

MONTH_TO_NUM = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

DATE_PATTERNS = [
    # 18 May 2026 / 18-May-2026 / 18.May.2026
    (re.compile(r"\b(\d{1,2})[\s./-]([A-Za-z]{3,9})[\s./-](\d{2,4})\b"), "dmy_named"),
    # 2026-05-18
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), "iso"),
    # 18/05/2026 or 18-05-26
    (re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b"), "dmy_num"),
]


def _extract_amount(text: str) -> int | None:
    for pat in AMOUNT_PATTERNS:
        m = pat.search(text)
        if m:
            try:
                num = float(m.group(1).replace(",", ""))
            except ValueError:
                continue
            unit = m.group(2) if m.lastindex and m.lastindex >= 2 else ""
            return _to_inr_amount(num, unit or "")
    return None


def _extract_emd(text: str) -> int | None:
    m = re.search(r"emd[^a-z0-9]{0,30}([\d,.]+)\s*(crore|cr|lakh|lac|lakhs|lacs)?", text, re.I)
    if not m:
        return None
    try:
        num = float(m.group(1).replace(",", ""))
    except ValueError:
        return None
    return _to_inr_amount(num, m.group(2) or "")


def _extract_deadline(text: str) -> str | None:
    for pat, _ in DATE_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(0)
    return None


def _parse_deadline_to_iso(text: str) -> str | None:
    """Best-effort parse of any date inside text → 'YYYY-MM-DD'. Returns None on failure."""
    from datetime import date as _date

    for pat, kind in DATE_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        try:
            if kind == "iso":
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            elif kind == "dmy_named":
                d = int(m.group(1))
                mo = MONTH_TO_NUM.get(m.group(2).lower()[:3])
                if mo is None:
                    continue
                y = int(m.group(3))
                if y < 100:
                    y += 2000
            else:  # dmy_num
                d = int(m.group(1))
                mo = int(m.group(2))
                y = int(m.group(3))
                if y < 100:
                    y += 2000
                # Heuristic: if first segment > 12, it's almost certainly day-first;
                # otherwise assume Indian DD/MM/YYYY which we already do.
            _date(y, mo, d)
            return f"{y:04d}-{mo:02d}-{d:02d}"
        except (ValueError, KeyError):
            continue
    return None


def _days_left_from(text: str) -> int | None:
    iso = _parse_deadline_to_iso(text)
    if not iso:
        return None
    from datetime import date as _date
    try:
        target = _date.fromisoformat(iso)
        return (target - _date.today()).days
    except ValueError:
        return None


def _extract_eligibility(text: str) -> list[str]:
    bits: list[str] = []
    if re.search(r"\bgst\b", text, re.I):
        bits.append("GST registration")
    if re.search(r"\bmsme\b|\budyam\b", text, re.I):
        bits.append("MSME eligible")
    if re.search(r"\bpan\b", text, re.I):
        bits.append("PAN required")
    m = re.search(r"(\d+)\s*\+?\s*years?\s*(?:of\s*)?experience", text, re.I)
    if m:
        bits.append(f"{m.group(1)}+ years experience")
    if re.search(r"iso[\s-]?\d+", text, re.I):
        bits.append("ISO certification")
    return bits


_AGGREGATOR_URL_PATTERNS = [
    re.compile(r"karnatakatenders\.in/quicksearch", re.I),
    re.compile(r"tendersontime\.com/[^/]+-tenders/[^/]+/?$", re.I),
    re.compile(r"tenderdetail\.com/[A-Za-z-]+-tenders/", re.I),
    re.compile(r"eprocure\.gov\.in/eprocure/app\?page=FrontEndLatestActiveTenders", re.I),
    re.compile(r"eprocure\.gov\.in/eprocure/app\?component=%24DirectLink&page=FrontEndTendersByOrganisation", re.I),
    re.compile(r"eprocure\.gov\.in/epublish/app\?", re.I),
    re.compile(r"railway-tenders\.co\.in/[a-z-]+\-tender/?$", re.I),
    re.compile(r"tendertiger\.com/[A-Za-z-]+/?$", re.I),
]

_AGGREGATOR_TITLE_PATTERNS = [
    re.compile(r"^\s*\d+\s*$"),  # title is just a number like "1" or "17"
    re.compile(r"^read more$", re.I),
    re.compile(r"\b\d{2,5}\s+[A-Za-z ]+tenders\s+in\b", re.I),  # "279 Cctv tenders in Karnataka"
    re.compile(r"\bactive tenders\b", re.I),
    re.compile(r"\blive\b.*\btenders\b", re.I),
    re.compile(r"\bepublishing system\b", re.I),
    re.compile(r"^\s*procurement of (goods|services)\s*$", re.I),
    re.compile(r"^\s*request for proposal( \(rfp\))?\s*$", re.I),
]


def is_low_signal_tender(t: "Tender") -> tuple[bool, str | None]:
    """Heuristic check for aggregator pages and empty stubs that have no useful info.

    Returns (is_junk, reason). Used both pre-LLM (skip the call) and post-LLM
    (final safety net when the LLM filter is off or partially failed).
    """
    url = t.source_url or ""
    title = (t.title or "").strip()

    for pat in _AGGREGATOR_URL_PATTERNS:
        if pat.search(url):
            return True, "Aggregator/listing page (URL pattern)"
    for pat in _AGGREGATOR_TITLE_PATTERNS:
        if pat.search(title):
            return True, f"Aggregator/generic title: {title[:40]!r}"

    # Empty stub: no title, no value, no deadline, no eligibility, no tender fee.
    has_any_signal = any(
        [
            title and len(title) > 6,
            t.estimated_value,
            t.emd,
            t.deadline,
            t.eligibility,
            t.tender_fee,
        ]
    )
    if not has_any_signal:
        return True, "Empty stub — no extractable tender details"

    return False, None


def _portal_from_url(url: str) -> str | None:
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return None
    host = host.replace("www.", "")
    if not host:
        return None
    if "eprocure" in host:
        return "eProcurement Portal"
    if "gem.gov.in" in host:
        return "GeM"
    return host


def tender_from_search_result(result: dict[str, Any]) -> Tender | None:
    url = result.get("url")
    if not url:
        return None
    title = result.get("title")
    snippet = result.get("snippet") or ""
    blob = f"{title or ''}\n{snippet}"
    deadline_text = _extract_deadline(snippet)
    deadline_iso = _parse_deadline_to_iso(snippet) if deadline_text else None
    days_left = _days_left_from(snippet) if deadline_text else None
    return Tender(
        id=f"tender_{uuid.uuid4().hex[:8]}",
        title=title,
        source_url=url,
        source_portal=_portal_from_url(url),
        location=None,
        estimated_value=_extract_amount(snippet),
        deadline=deadline_text,
        deadline_iso=deadline_iso,
        days_left=days_left,
        emd=_extract_emd(snippet),
        eligibility=_extract_eligibility(blob),
    )


def merge_scraped_into_tender(tender: Tender, page: dict[str, Any]) -> Tender:
    """Fill missing tender fields from a scraped page (markdown + generatedJson.data)."""
    gj = page.get("generatedJson") or {}
    data = gj.get("data") if isinstance(gj, dict) else {}
    data = data or {}
    md = page.get("markdown") or ""

    if not tender.title:
        tender.title = data.get("title") or tender.title
    blob = f"{tender.title or ''}\n{data.get('description') or ''}\n{md[:8000]}"

    if tender.estimated_value is None:
        tender.estimated_value = _extract_amount(blob)
    if tender.emd is None:
        tender.emd = _extract_emd(blob)
    if tender.deadline is None:
        tender.deadline = _extract_deadline(blob)
    if tender.deadline_iso is None and tender.deadline:
        tender.deadline_iso = _parse_deadline_to_iso(blob)
    if tender.days_left is None and tender.deadline_iso:
        tender.days_left = _days_left_from(blob)
    if not tender.eligibility:
        tender.eligibility = _extract_eligibility(blob)

    # Try to capture document/apply links from generatedJson.data.links if present
    links = data.get("links") if isinstance(data, dict) else None
    if isinstance(links, list):
        for link in links[:30]:
            href = (link or {}).get("url") if isinstance(link, dict) else None
            text = ((link or {}).get("text") or "") if isinstance(link, dict) else ""
            if not href:
                continue
            tlow = text.lower()
            if not tender.apply_link and any(k in tlow for k in ["apply", "submit bid", "register"]):
                tender.apply_link = href
    return tender


# --------- Scoring ---------

_AUTO_RISK_PREFIXES = (
    "Estimated value exceeds",
    "EMD above your",
    "Deadline not detected",
    "Tender page may require login",
)


def score_tender(tender: Tender, intent: TenderIntent) -> Tender:
    score = 0
    risks: list[str] = [r for r in tender.risk_flags if not r.startswith(_AUTO_RISK_PREFIXES)]
    hay = " ".join(
        [
            tender.title or "",
            tender.location or "",
            " ".join(tender.eligibility),
            tender.source_portal or "",
            tender.source_url or "",
        ]
    ).lower()

    if intent.business_category and intent.business_category.lower() in hay:
        score += 20
    elif intent.business_category and any(k in hay for k in intent.business_category.split()):
        score += 10

    if intent.location and intent.location.lower() in hay:
        score += 15

    if intent.max_contract_value and tender.estimated_value:
        if tender.estimated_value <= intent.max_contract_value:
            score += 15
        else:
            score -= 10
            risks.append("Estimated value exceeds your budget")

    if intent.max_emd and tender.emd is not None:
        if tender.emd <= intent.max_emd:
            score += 5
        else:
            score -= 10
            risks.append("EMD above your preference")

    if intent.certificates:
        for cert in intent.certificates:
            if cert.lower() in hay:
                score += 5

    if tender.deadline:
        score += 10
    else:
        risks.append("Deadline not detected on page")

    # Login-required heuristic
    if "login" in hay or "sign in" in hay:
        risks.append("Tender page may require login")
        score -= 5

    tender.fit_score = max(0, min(100, score))
    if tender.fit_score >= 80:
        tender.recommendation = "Apply"
    elif tender.fit_score >= 60:
        tender.recommendation = "Maybe Apply"
    elif tender.fit_score >= 40:
        tender.recommendation = "Review Carefully"
    else:
        tender.recommendation = "Skip"
    tender.risk_flags = list(dict.fromkeys(risks))[:6]
    return tender


def build_action_plan(top: Tender | None, intent: TenderIntent) -> list[str]:
    plan = [
        "Today: download the tender document and read it end-to-end.",
        "Within 1 day: verify eligibility (GST, MSME, experience, turnover).",
        "Within 2 days: arrange EMD draft / online payment.",
        "Prepare technical bid: company profile, similar work certificates, OEM/manufacturer authorisations.",
        "Prepare financial bid: BOQ, taxes, validity period.",
    ]
    if top and top.deadline:
        plan.append(f"Submit before deadline: {top.deadline}.")
    else:
        plan.append("Confirm submission deadline from the source page before bidding.")
    if intent.certificates:
        plan.append("Keep digital copies ready: " + ", ".join(intent.certificates) + ".")
    return plan


# --------- Streaming agent ---------

async def run_agent_stream(query: str) -> AsyncGenerator[str, None]:
    client = AnakinClient()

    async def send(event: str, data: dict[str, Any]) -> str:
        return f"event: {event}\ndata: {json.dumps(jsonable_encoder(data))}\n\n"

    yield await send("status", {"message": "Understanding your requirement..."})

    yield await send("tool_call_started", {"tool": "parse_intent"})
    intent = parse_intent(query)
    yield await send("tool_call_completed", {"tool": "parse_intent", "intent": intent.model_dump()})

    yield await send("status", {"message": "Building targeted search queries..."})
    yield await send("tool_call_started", {"tool": "build_queries"})
    queries = build_queries(intent, query)
    yield await send("tool_call_completed", {"tool": "build_queries", "queries": queries})

    yield await send("status", {"message": "Searching tender portals with Anakin..."})
    yield await send("tool_call_started", {"tool": "anakin.search"})

    # Run searches concurrently
    search_tasks = [client.search(q, limit=8) for q in queries]
    search_envelopes = await asyncio.gather(*search_tasks, return_exceptions=True)
    raw_results: list[dict[str, Any]] = []
    search_errors: list[str] = []
    for r in search_envelopes:
        if isinstance(r, dict):
            if r.get("error"):
                search_errors.append(r["error"])
            for item in r.get("results") or []:
                raw_results.append(item)

    # Deduplicate by URL preserving order
    seen, deduped = set(), []
    for r in raw_results:
        u = r.get("url")
        if u and u not in seen:
            deduped.append(r)
            seen.add(u)

    completed_payload: dict[str, Any] = {"tool": "anakin.search", "urls_found": len(deduped)}
    if search_errors and not deduped:
        completed_payload["error"] = search_errors[0]
    yield await send("tool_call_completed", completed_payload)
    for r in deduped[:8]:
        yield await send("source_discovered", {"url": r.get("url"), "title": r.get("title")})

    # Build tenders from snippets and score immediately for fast first paint
    tenders: list[Tender] = []
    junk_dropped = 0
    for r in deduped:
        t = tender_from_search_result(r)
        if not t:
            continue
        is_junk, _reason = is_low_signal_tender(t)
        if is_junk:
            junk_dropped += 1
            continue
        tenders.append(score_tender(t, intent))
    tenders.sort(key=lambda t: t.fit_score, reverse=True)

    if junk_dropped:
        yield await send(
            "tool_call_completed",
            {"tool": "junk_filter", "dropped": junk_dropped, "kept": len(tenders)},
        )
    yield await send("partial_results", {"tenders": [t.model_dump() for t in tenders[:5]]})

    # Pick top candidates by fit score and scrape them for richer details
    top_candidates = tenders[: settings.max_urls]
    urls_to_scrape = [t.source_url for t in top_candidates]

    if urls_to_scrape:
        yield await send("status", {"message": f"Scraping top {len(urls_to_scrape)} tender pages with Anakin..."})
        yield await send("tool_call_started", {"tool": "anakin.url-scraper"})
        pages = await client.scrape_many(urls_to_scrape, use_browser=False, concurrency=4)
        yield await send("tool_call_completed", {"tool": "anakin.url-scraper", "pages": len(pages)})

        url_to_page = {p.get("url"): p for p in pages if p.get("url")}
        for t in top_candidates:
            page = url_to_page.get(t.source_url)
            if page and page.get("status") == "completed":
                t = merge_scraped_into_tender(t, page)
                score_tender(t, intent)

        tenders.sort(key=lambda t: t.fit_score, reverse=True)
        yield await send("partial_results", {"tenders": [t.model_dump() for t in tenders[:5]]})

    # LLM relevance + freshness filter
    if settings.openrouter_api_key and tenders:
        yield await send("status", {"message": f"Filtering with {settings.llm_model.split('/')[-1]}..."})
        yield await send("tool_call_started", {"tool": "llm.filter"})
        before = len(tenders)
        tenders, llm_meta = await llm_filter_tenders(intent, tenders)
        tenders.sort(key=lambda t: t.fit_score, reverse=True)
        yield await send(
            "tool_call_completed",
            {
                "tool": "llm.filter",
                "kept": len(tenders),
                "dropped": before - len(tenders),
                "model": llm_meta.get("model"),
                "used_llm": llm_meta.get("used_llm", False),
                "error": llm_meta.get("error"),
            },
        )
        yield await send("partial_results", {"tenders": [t.model_dump() for t in tenders[:5]]})

    # Hard freshness gate: drop anything where the deadline is in the past, even if
    # the LLM missed it. Tenders with unknown days_left are kept (might be valid).
    before_gate = len(tenders)
    tenders = [t for t in tenders if t.days_left is None or t.days_left >= 0]
    expired_dropped = before_gate - len(tenders)
    if expired_dropped:
        yield await send(
            "tool_call_completed",
            {"tool": "freshness_gate", "dropped": expired_dropped, "kept": len(tenders)},
        )

    # Final safety net: re-run junk filter on the surviving set in case the LLM
    # was off or partially failed. Also drop tenders with score < 30 that have
    # no deadline AND no extracted value — these are noise to the user.
    before_junk2 = len(tenders)
    cleaned: list[Tender] = []
    for t in tenders:
        is_junk, _ = is_low_signal_tender(t)
        if is_junk:
            continue
        if t.fit_score < 30 and t.days_left is None and not t.estimated_value:
            continue
        cleaned.append(t)
    tenders = cleaned
    if before_junk2 != len(tenders):
        yield await send(
            "tool_call_completed",
            {"tool": "junk_filter_post", "dropped": before_junk2 - len(tenders), "kept": len(tenders)},
        )

    top = tenders[0] if tenders else None
    risks: list[str] = []
    for t in tenders[:5]:
        risks.extend(t.risk_flags)

    final = FinalResult(
        summary=(
            f"I found {len(tenders)} tender leads"
            + (f" and ranked top matches for {intent.business_category} in {intent.location}." if intent.business_category and intent.location else ".")
        ),
        top_recommendation=top,
        tenders=tenders[:8],
        sources=[t.source_url for t in tenders[:10]],
        action_plan=build_action_plan(top, intent),
        risk_flags=list(dict.fromkeys(risks))[:8],
    )
    yield await send("final_result", final.model_dump())
