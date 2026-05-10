# TenderFlow — AI Context

## 1. Project Summary

**TenderFlow** is an AI-native tender discovery and bid-prep agent for small and medium businesses in India.

Users type what kind of government/private contract they want in plain English. TenderFlow uses Anakin.io to search, scrape, crawl, and extract tender information from public tender portals and websites. It then ranks opportunities by business fit and generates a clear action plan/checklist for applying.

### One-line pitch

> TenderFlow lets Indian SMBs type the contracts they want, then finds relevant tenders, extracts eligibility/deadlines/fees/documents, and creates a bid action plan.

### Simple analogy

FlowPay was:  
> “Type a payment ops task → agent handles Razorpay, Sheets, emails, follow-ups.”

TenderFlow is:  
> “Type a contract opportunity you want → agent handles tender search, scraping, extraction, ranking, and bid-prep checklist.”

---

## 2. Hackathon Context

This project is for the **Build With Anakin - Mini Hackathon**.

The event focuses on building real projects using **Anakin.io**, especially around:

- web scraping
- crawling
- data extraction
- turning messy websites into structured Markdown/JSON
- agentic web workflows

Judging criteria:

- **40% Idea**
- **30% Real-world use case**
- **30% Development**

TenderFlow is designed to score well because:

- Idea is specific and agentic, not just a generic scraper.
- Real-world value is clear for Indian SMBs, contractors, vendors, agencies, and service providers.
- Development is feasible in hackathon time using Anakin search/scrape/crawl APIs.

---

## 3. Problem

Small Indian businesses often miss government and institutional tender opportunities because tender portals are messy, fragmented, and hard to understand.

Common pain points:

1. Tenders are spread across multiple portals.
2. Tender pages are difficult to read.
3. Eligibility requirements are buried in PDFs or long pages.
4. Deadlines, EMD, tender fees, and required documents are unclear.
5. SMBs do not know which tenders are worth applying for.
6. Many businesses waste time on tenders they are not eligible for.
7. Manual tender discovery is repetitive and boring.

TenderFlow converts this messy discovery process into a plain-English agent workflow.

---

## 4. Target Users

Primary users:

- CCTV installation vendors
- housekeeping/cleaning agencies
- catering businesses
- IT support companies
- construction contractors
- electrical/plumbing contractors
- solar installation companies
- security service providers
- small manufacturing suppliers
- MSMEs looking for government contracts

Secondary users:

- consultants who help businesses apply for tenders
- procurement teams
- local agencies
- startup founders applying for grants/contracts

---

## 5. Core User Experience

The user does not fill a complex form. They type in natural language.

Example:

```txt
Find CCTV installation tenders in Karnataka below 25 lakh. I am an MSME vendor with GST and 2 years experience. Only show tenders closing after 7 days.
```

TenderFlow returns:

```txt
Found 6 relevant tenders.

Top Recommendation:
CCTV Installation for Govt School, Mysuru
Fit Score: 88/100
Estimated Value: ₹18.5L
Deadline: 18 May 2026
EMD: ₹35,000
Eligibility: GST, MSME allowed, 2+ years experience

Why this matches:
- Location matches Karnataka
- Budget is below ₹25L
- Deadline is 8+ days away
- MSME can apply
- Experience requirement matches user profile

Required Documents:
- GST certificate
- PAN card
- MSME certificate
- Company registration
- Work completion certificates
- Technical bid
- Financial bid

Action Plan:
Today: Download tender documents
Tomorrow: Prepare past work proof
Next 2 days: Arrange EMD
Before 17 May: Submit bid online
```

---

## 6. Natural Language Inputs

The product should support prompts like:

```txt
Find housekeeping tenders in Bangalore under 15 lakh where MSME can apply.
```

```txt
Find government tenders in Karnataka for CCTV installation under 25 lakh. Only show ones closing after 7 days.
```

```txt
Find catering tenders in Mumbai closing this month. I can handle orders up to 500 people.
```

```txt
Show me IT support tenders in Gujarat below 10 lakh where turnover requirement is not more than 50 lakh.
```

```txt
Find solar panel installation tenders in Maharashtra. Skip tenders with EMD above 1 lakh.
```

```txt
Compare these 3 tender URLs and tell me which one I should apply for first.
```

```txt
Track new cleaning tenders in Bengaluru and prepare a checklist for each.
```

```txt
I have GST, MSME, PAN, and 3 years experience. Find tenders I am eligible for in Karnataka.
```

---

## 7. Expected Output Structure

TenderFlow should output results in a simple, decision-oriented format.

### 7.1 Search Summary

```txt
I found 8 possible tenders and shortlisted 3 that match your business profile.
```

### 7.2 Tender Card

Each tender should be shown as a card:

```txt
Tender: CCTV Installation at Government School, Mysuru
Department: Department of Education, Karnataka
Location: Mysuru, Karnataka
Estimated Value: ₹18.5L
Deadline: 18 May 2026
EMD: ₹35,000
Tender Fee: ₹500
Apply Link: https://...
Source: eprocurement portal
Fit Score: 88/100
Recommendation: Apply
```

### 7.3 Why It Matches

```txt
Why this matches:
- Category matches CCTV installation
- Location matches Karnataka
- Estimated value is below ₹25L
- Deadline is more than 7 days away
- MSME appears eligible
```

### 7.4 Eligibility

```txt
Eligibility:
- GST registration required
- PAN required
- Minimum 2 years experience
- Similar work completion certificate required
- MSME vendors allowed/preferred
```

### 7.5 Required Documents

```txt
Documents needed:
- GST certificate
- PAN card
- MSME certificate
- Company registration
- Work completion certificates
- Technical proposal
- Financial bid
- EMD proof
```

### 7.6 Risk Flags

```txt
Risk flags:
- Deadline is close: 4 days left
- EMD is high compared to tender value
- Eligibility mentions 3 years experience but user has 2 years
- Tender document link may require login
```

### 7.7 Action Plan

```txt
Action plan:
1. Download tender document today.
2. Check whether 2-year experience is accepted.
3. Arrange EMD before 15 May.
4. Prepare technical bid and financial bid.
5. Submit before 17 May 5:00 PM.
```

---

## 8. Anakin.io Usage

TenderFlow should visibly use Anakin.io as the core data engine.

### 8.1 Search API

Use Anakin Search API to discover tender pages from a natural-language query.

Example queries generated from user prompt:

```txt
CCTV installation tender Karnataka under 25 lakh closing May 2026
site:eprocure.gov.in CCTV Karnataka tender
site:gem.gov.in CCTV installation Karnataka tender
site:*.gov.in CCTV installation tender Karnataka MSME
```

Endpoint concept:

```http
POST https://api.anakin.io/v1/search
```

Request body:

```json
{
  "prompt": "CCTV installation tender Karnataka under 25 lakh closing after 7 days",
  "limit": 10
}
```

### 8.2 URL Scraper

Use Anakin URL Scraper to scrape individual tender pages.

Endpoint concept:

```http
POST https://api.anakin.io/v1/url-scraper
```

Request body:

```json
{
  "url": "https://example-tender-page.gov.in/...",
  "country": "in",
  "useBrowser": true,
  "generateJson": true
}
```

Fields to extract:

- tender title
- department
- location
- estimated value
- deadline
- EMD
- tender fee
- eligibility criteria
- required documents
- apply link
- document download links
- contact details if public
- corrigendum links
- submission portal

### 8.3 Map API

Use Anakin Map when a tender page has many links and the app needs to find related tender documents, corrigendum pages, or PDF links.

Endpoint concept:

```http
POST https://api.anakin.io/v1/map
```

Request body:

```json
{
  "url": "https://example-tender-page.gov.in/...",
  "includeSubdomains": false,
  "limit": 100,
  "search": "tender",
  "useBrowser": true
}
```

### 8.4 Crawl API

Use Anakin Crawl when a tender source has multiple pages that need to be explored.

Endpoint concept:

```http
POST https://api.anakin.io/v1/crawl
```

Request body:

```json
{
  "url": "https://example-tender-portal.gov.in/...",
  "maxPages": 10,
  "includePatterns": ["*tender*", "*bid*", "*notice*"],
  "excludePatterns": ["*login*", "*admin*"],
  "country": "in",
  "useBrowser": true
}
```

### 8.5 Browser Sessions / Authenticated Pages

If a portal requires login, the MVP can show:

```txt
This tender appears to require login. Connect a browser session to continue.
```

For hackathon MVP, public pages should be prioritized.

---

## 9. Agent Tool Flow

The agent should follow this flow:

### Step 1: Parse intent

Input:

```txt
Find CCTV installation tenders in Karnataka below 25 lakh. I am an MSME vendor with GST and 2 years experience.
```

Parsed intent:

```json
{
  "business_category": "CCTV installation",
  "location": "Karnataka",
  "max_contract_value": 2500000,
  "certificates": ["GST", "MSME"],
  "experience_years": 2,
  "deadline_min_days": 7,
  "max_emd": null
}
```

### Step 2: Generate search queries

```json
[
  "CCTV installation tender Karnataka under 25 lakh MSME",
  "site:eprocure.gov.in CCTV installation Karnataka tender",
  "site:gem.gov.in CCTV installation Karnataka tender",
  "Karnataka CCTV tender government school 2026"
]
```

### Step 3: Search web using Anakin

Call Anakin Search API for each query.

### Step 4: Deduplicate URLs

Remove duplicate URLs and irrelevant pages.

### Step 5: Scrape top candidate pages

Use Anakin URL Scraper with `generateJson: true` and `useBrowser: true`.

### Step 6: Extract tender schema

Convert scraped Markdown/JSON into normalized tender objects.

### Step 7: Score tender fit

Use a deterministic scoring system.

### Step 8: Produce final answer

Show best tenders, reasons, risks, and action plan.

---

## 10. Tender Data Schema

Each tender should be represented internally like this:

```json
{
  "id": "tender_001",
  "title": "CCTV Installation for Government School, Mysuru",
  "department": "Department of Education, Karnataka",
  "source_portal": "eProcurement Karnataka",
  "source_url": "https://...",
  "location": "Mysuru, Karnataka",
  "category": "CCTV installation",
  "estimated_value": 1850000,
  "currency": "INR",
  "deadline": "2026-05-18T17:00:00+05:30",
  "days_left": 8,
  "emd": 35000,
  "tender_fee": 500,
  "eligibility": [
    "GST registration required",
    "PAN required",
    "Minimum 2 years similar work experience",
    "MSME vendors allowed"
  ],
  "required_documents": [
    "GST certificate",
    "PAN card",
    "MSME certificate",
    "Company registration",
    "Work completion certificate",
    "Technical bid",
    "Financial bid"
  ],
  "apply_link": "https://...",
  "document_links": ["https://...pdf"],
  "contact": {
    "name": null,
    "email": null,
    "phone": null
  },
  "risk_flags": [
    "Tender document may require portal login"
  ],
  "fit_score": 88,
  "recommendation": "Apply"
}
```

---

## 11. Fit Score Logic

Fit score should be easy to understand and explain.

Start at 0 and add/subtract points.

### Positive signals

```txt
+20 category matches user business
+15 location matches user target location
+15 budget/value within user preference
+15 deadline is more than 7 days away
+10 user has required certificate
+10 user has enough experience
+10 MSME/startup eligibility or preference
+5 EMD is affordable
```

### Negative signals

```txt
-20 deadline already passed or less than 2 days away
-15 EMD above user preference
-15 required experience higher than user experience
-15 turnover requirement appears too high
-10 tender page is incomplete or unclear
-10 tender requires login and document is not public
-10 category match is weak
```

### Recommendation labels

```txt
80–100: Apply
60–79: Maybe Apply
40–59: Review Carefully
0–39: Skip
```

---

## 12. MVP Scope

The hackathon MVP should focus on:

1. Plain-English input
2. Intent parsing
3. Anakin Search API integration
4. Anakin URL Scraper integration
5. Tender field extraction
6. Fit scoring
7. Checklist/action plan generation
8. Clean UI with result cards

Avoid spending time on:

- full user authentication
- paid subscriptions
- automatic tender submission
- full CRM
- complex PDF parsing unless necessary
- email alerts unless there is extra time

---

## 13. Stretch Features

If the MVP is done early, add:

### 13.1 Tender comparison

User input:

```txt
Compare these 3 tender links and tell me which one is easiest to apply for.
```

Output:

```txt
Tender A: Best fit, low EMD, simple documents
Tender B: Good value but high eligibility requirement
Tender C: Skip, deadline too close
```

### 13.2 Daily monitoring

User input:

```txt
Track new solar tenders in Maharashtra and show me a daily digest.
```

### 13.3 Document checklist export

Generate downloadable checklist as Markdown/CSV/PDF.

### 13.4 Bid calendar

Show important dates:

- document download deadline
- pre-bid meeting
- clarification deadline
- submission deadline
- bid opening date

### 13.5 Email draft

Generate a draft email to the business owner/team:

```txt
Subject: 3 CCTV tenders to review this week
```

---

## 14. UI Concept

### Main screen

```txt
TenderFlow
Find contracts you can actually apply for.

[ I am a CCTV vendor in Karnataka with GST/MSME. Find tenders below 25 lakh closing after 7 days. ]

[ Find Tenders ]
```

### Loading states

Show agent steps:

```txt
Understanding your business requirement...
Searching tender portals with Anakin...
Scraping tender pages...
Extracting eligibility and deadlines...
Ranking opportunities...
Preparing bid checklist...
```

### Results page

Sections:

1. Search summary
2. Best tender recommendation
3. Tender cards
4. Checklist
5. Risk flags
6. Sources

---

## 15. Demo Script

### Demo prompt

```txt
Find CCTV installation tenders in Karnataka below 25 lakh. I am an MSME vendor with GST and 2 years experience. Only show tenders closing after 7 days.
```

### Demo narration

1. “Tender portals are messy and SMBs miss opportunities.”
2. “With TenderFlow, they just type what contract they want.”
3. “Our agent uses Anakin Search to discover tender pages.”
4. “Then it uses Anakin Scraper/Crawl to extract details from messy pages.”
5. “Finally, it ranks tenders by fit and creates a bid checklist.”
6. “This turns tender discovery from hours of manual work into a 30-second workflow.”

### Closing line

> Anakin turns websites into structured data. TenderFlow turns that data into contracts Indian SMBs can actually apply for.

---

## 16. Technical Architecture

### Frontend

Recommended:

- Next.js
- Tailwind CSS
- shadcn/ui
- simple chat/input interface
- result cards

### Backend

Recommended:

- Next.js API routes or Express
- Anakin API wrapper
- LLM parser/extractor if available
- deterministic scoring function

### Main backend functions

```ts
parseUserIntent(prompt: string): TenderIntent
buildSearchQueries(intent: TenderIntent): string[]
searchTenders(queries: string[]): Promise<SearchResult[]>
deduplicateUrls(results: SearchResult[]): string[]
scrapeTender(url: string): Promise<ScrapedPage>
extractTenderFields(scraped: ScrapedPage): Promise<Tender>
scoreTender(tender: Tender, intent: TenderIntent): ScoredTender
generateActionPlan(tender: ScoredTender): ActionPlan
analyzeTenderPrompt(prompt: string): Promise<TenderFlowResult>
```

### Environment variables

```env
ANAKIN_API_KEY=
OPENAI_API_KEY=
# or other LLM key if needed
```

---

## 17. API Wrapper Pseudocode

```ts
async function anakinSearch(prompt: string, limit = 10) {
  const res = await fetch("https://api.anakin.io/v1/search", {
    method: "POST",
    headers: {
      "X-API-Key": process.env.ANAKIN_API_KEY!,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ prompt, limit })
  });

  return res.json();
}
```

```ts
async function anakinScrape(url: string) {
  const submit = await fetch("https://api.anakin.io/v1/url-scraper", {
    method: "POST",
    headers: {
      "X-API-Key": process.env.ANAKIN_API_KEY!,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      url,
      country: "in",
      useBrowser: true,
      generateJson: true
    })
  });

  const job = await submit.json();
  return pollAnakinJob(job.jobId);
}
```

```ts
async function pollAnakinJob(jobId: string) {
  for (let i = 0; i < 20; i++) {
    const res = await fetch(`https://api.anakin.io/v1/url-scraper/${jobId}`, {
      headers: {
        "X-API-Key": process.env.ANAKIN_API_KEY!
      }
    });

    const data = await res.json();
    if (data.status === "completed" || data.status === "failed") {
      return data;
    }

    await new Promise(resolve => setTimeout(resolve, 2000));
  }

  throw new Error("Anakin job timed out");
}
```

---

## 18. AI Extraction Prompt

Use this prompt to convert scraped page content into structured tender JSON:

```txt
You are TenderFlow, an AI tender extraction agent for Indian SMBs.

Extract tender information from the following scraped page content.

Return strict JSON only.

Schema:
{
  "title": string | null,
  "department": string | null,
  "source_portal": string | null,
  "location": string | null,
  "category": string | null,
  "estimated_value": number | null,
  "deadline": string | null,
  "emd": number | null,
  "tender_fee": number | null,
  "eligibility": string[],
  "required_documents": string[],
  "apply_link": string | null,
  "document_links": string[],
  "contact": {
    "name": string | null,
    "email": string | null,
    "phone": string | null
  },
  "risk_flags": string[]
}

Rules:
- Use null if the field is not found.
- Do not guess numbers.
- Convert INR amounts to plain numbers where possible.
- Keep original source links if available.
- Add risk_flags for missing deadline, missing eligibility, login requirement, unclear EMD, or expired tender.

Content:
{{SCRAPED_MARKDOWN_OR_JSON}}
```

---

## 19. Intent Parsing Prompt

Use this prompt to parse user input:

```txt
Parse the user's tender search request into structured JSON.

Return strict JSON only.

Schema:
{
  "business_category": string | null,
  "location": string | null,
  "max_contract_value": number | null,
  "min_contract_value": number | null,
  "certificates": string[],
  "experience_years": number | null,
  "deadline_min_days": number | null,
  "max_emd": number | null,
  "turnover_limit": number | null,
  "keywords": string[]
}

User request:
{{USER_PROMPT}}
```

---

## 20. Example End-to-End Input/Output

### Input

```txt
Find solar panel installation tenders in Maharashtra below 50 lakh. I have GST, MSME, and 4 years experience. Skip EMD above 1 lakh.
```

### Parsed intent

```json
{
  "business_category": "solar panel installation",
  "location": "Maharashtra",
  "max_contract_value": 5000000,
  "min_contract_value": null,
  "certificates": ["GST", "MSME"],
  "experience_years": 4,
  "deadline_min_days": null,
  "max_emd": 100000,
  "turnover_limit": null,
  "keywords": ["solar", "installation", "Maharashtra", "MSME"]
}
```

### Final output

```txt
I found 5 solar installation tenders and shortlisted 2 strong matches.

1. Solar Rooftop Installation for Municipal Building, Pune
Fit Score: 91/100 — Apply
Estimated Value: ₹42L
Deadline: 22 May 2026
EMD: ₹80,000
Department: Pune Municipal Corporation

Why it matches:
- Solar installation category matches
- Maharashtra location matches
- Contract value is below ₹50L
- EMD is below your ₹1L limit
- GST/MSME accepted
- Experience requirement appears to be 3 years; you have 4

Documents needed:
- GST certificate
- MSME certificate
- PAN
- Company registration
- Similar work completion certificate
- Technical bid
- Financial bid

Action plan:
- Today: Download tender documents
- Tomorrow: Verify experience certificate format
- Within 2 days: Arrange EMD
- Before deadline: Submit technical and financial bid

Risk flags:
- Tender document has corrigendum link; review before applying.

Source:
https://...
```

---

## 21. What Not To Build

Avoid turning TenderFlow into a generic scraper dashboard.

Do not focus on:

- “Enter URL and scrape it” as the main product
- generic CSV export only
- generic lead generation
- random tender listing without ranking
- complex vendor onboarding

The product should feel like an **AI ops agent**:

```txt
User says what they want → agent searches/scrapes/extracts/ranks → user gets a decision and action plan.
```

---

## 22. Final Product Positioning

TenderFlow is not a tender search engine.

It is a **bid-prep operating agent** for SMBs.

Better framing:

```txt
Bad: Search tenders with AI.
Good: Type the contract you want. TenderFlow finds matching tenders and tells you exactly what to do next.
```

Best closing line:

> TenderFlow helps Indian SMBs discover contracts they can actually win, not just tenders they can search.
