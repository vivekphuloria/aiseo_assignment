# SEO Article Generator

A FastAPI backend that accepts a topic and returns a fully structured, SEO-validated article. It queries the top 10 Google SERP results, extracts keyword intent and competitor patterns via LLM analysis, builds a word-budgeted outline, generates each section independently, then runs 10 programmatic SEO constraint checks — all in a crash-recoverable LangGraph pipeline with async SQLite checkpointing.

**Stack:** FastAPI · LangGraph · Claude Sonnet (claude-sonnet-4-6) · SerpAPI · SQLite

---

## Quick Start

```bash
# From the repo root
cd seo_agent

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # open .env and add your ANTHROPIC_API_KEY
uvicorn main:app --reload --port 8000
```

Interactive API docs: http://localhost:8000/docs

`jobs.db` and `checkpoints.db` are created automatically on first server start — no manual DB setup required.

---

## Pipeline

```
serp_fetch → analyze_serp → build_outline → generate_sections → postprocess → validate_output
```

```mermaid
graph LR
    A[serp_fetch] --> B[analyze_serp]
    B --> C[build_outline]
    C --> D[generate_sections]
    D --> E[postprocess]
    E --> F[validate_output]
    F --> G([END])
```

### Node Reference

Nodes communicate exclusively through `ArticleState` (a LangGraph `TypedDict`). No node calls another node directly.

| Node | Processing Type | State Inputs | State Outputs | LLM (model / temp) | Notes |
|---|---|---|---|---|---|
| `serp_fetch` | Rule-based | `topic`, `use_mock` | `serp_data` (top-10 results + People Also Ask) | — | Calls SerpAPI or returns hardcoded mock; mock contains 10 results + 5 PAA questions |
| `analyze_serp` | LLM + structured output | `serp_data` (titles, URLs, snippets) | `serp_analysis` — `primary_keyword`, `secondary_keywords`, `common_subtopics`, `content_format`, `search_intent`, `competitor_h2_patterns` | claude-sonnet-4-6 / temp=0 | `with_structured_output(SerpAnalysis)`; keyword extraction folded here — no separate parse step |
| `build_outline` | LLM + structured output | `serp_analysis`, `target_word_count`, `language` | `outline` — `h1_title`, `meta_title`, `meta_description`, per-section word budgets, `internal_links`, `external_references` | claude-sonnet-4-6 / temp=0.2 | Word budgets normalised to 93% of target (LLM overshoots by ~7%) |
| `generate_sections` | LLM free-form | `outline` (heading, description, keywords, word budget per section), `serp_analysis` | `generated_sections` — `List[str]`, append reducer | claude-sonnet-4-6 / temp=0.7 | One LLM call per section; `Annotated[List[str], operator.add]` prevents overwrite on checkpoint replay |
| `postprocess` | Rule-based assembly + LLM structured output | `outline`, `serp_analysis`, `generated_sections`, `serp_data` (for PAA) | `article_output` — full `ArticleOutput` with keyword analysis | claude-sonnet-4-6 / temp=0.3 (FAQ only) | Keyword density computed from `serp_analysis.primary_keyword`; FAQ via `with_structured_output(FAQList)` |
| `validate_output` | Rule-based only (no LLM) | `article_output`, `outline`, `target_word_count` | `article_output` (with `validation_results` attached) | — | Regex + arithmetic; 10 deterministic SEO checks |

---

## Architecture

### Two SQLite Databases

| Database | Owner | Purpose |
|---|---|---|
| `jobs.db` | Application | Tracks job status, execution stage, error messages, and stores the final `ArticleOutput` as a JSON blob in `result_json` |
| `checkpoints.db` | LangGraph (`AsyncSqliteSaver`) | Persists full `ArticleState` after each node for crash recovery |

These concerns are kept separate by design. The application queries `jobs.db` for everything it needs to serve API responses — it never reads LangGraph's internal checkpoint schema. On job completion, `run_graph()` deserialises the final state from the checkpoint once, serialises the result to JSON, and writes it to `jobs.db`. All subsequent `/result` calls read from `jobs.db` only.

### AsyncSqliteSaver (not SqliteSaver)

FastAPI runs a single async event loop. The synchronous `SqliteSaver` blocks that loop on every checkpoint write and is not thread-safe under concurrent requests. `AsyncSqliteSaver` uses `aiosqlite` internally and is designed for this context. The saver is held open for the application's lifetime via the FastAPI `lifespan` context manager (not the deprecated `@app.on_event` pattern).

### `operator.add` Reducer on `generated_sections`

LangGraph replays all nodes from the last successful checkpoint when a job is resumed. If `generated_sections` used the default overwrite reducer, a replayed `generate_sections` run would lose all previously written sections. Declaring it as `Annotated[List[str], operator.add]` makes the reducer append-only — replay accumulates sections rather than overwriting them, keeping the step idempotent. This also future-proofs the field for the revision loop extension point.

### 93% Word Budget Scaling

`build_outline_node` scales all section word budgets to 93% of `target_word_count` before writing them into the outline. Empirical testing showed Claude consistently overshoots per-section word count targets by approximately 7%. Correcting at outline time keeps the final word count inside the ±10% tolerance window that `validate_output` checks, without requiring post-hoc truncation.

### `parse_query` Not a Separate Node

Converting the user's natural-language topic into a clean search keyword is a single reasoning step. Folding it into `analyze_serp` saves one LLM call, one round-trip of latency, and one failure point. `primary_keyword` is part of `SerpAnalysis`'s structured output — produced in the same call that extracts subtopics, search intent, and competitor patterns.

### No Per-Section DDGS Search

DuckDuckGo's scraper-based API has aggressive rate limiting and no guaranteed uptime. The SERP analysis already provides topic grounding via 10 real competitor results. Adding per-section DDGS would add ~10 seconds of latency per article, introduce a common failure mode, and require a complex mock path — for marginal content quality gain. Documented as an extension point.

### Crash Recovery via the Resume Endpoint

`POST /jobs/{thread_id}/resume` re-invokes `run_graph()` with the same `thread_id`. LangGraph looks up the checkpoint for that thread ID in `checkpoints.db`, determines the last successfully completed node, and resumes execution from there. No manual state reconstruction is required.

---

## Project Structure

```
seo_agent/
├── main.py                       # FastAPI app — lifespan, 4 endpoints, run_graph()
├── requirements.txt
├── .env.example                  # Environment variable template (copy to .env)
│
├── graph/
│   ├── builder.py                # Wires 6 nodes into a compiled StateGraph
│   ├── state.py                  # ArticleState TypedDict — shared contract between all nodes
│   └── nodes/
│       ├── serp_fetch.py         # Node 1: SerpAPI wrapper or mock
│       ├── analyze_serp.py       # Node 2: LLM → SerpAnalysis (structured output)
│       ├── build_outline.py      # Node 3: LLM → ArticleOutline (structured output)
│       ├── generate_sections.py  # Node 4: LLM free-form, one call per section
│       ├── postprocess.py        # Node 5: assemble article body + FAQ generation
│       └── validate_output.py    # Node 6: 10 SEO checks, no LLM
│
├── models/
│   ├── inputs.py                 # JobRequest, JobResponse, JobStatusResponse
│   ├── serp.py                   # SerpData, SerpResult, PeopleAlsoAsk
│   ├── outline.py                # SerpAnalysis, ArticleOutline, OutlineSection, links
│   └── article.py                # ArticleOutput, KeywordAnalysis, ValidationResult, FAQItem
│
├── prompts/
│   ├── analyze_serp.py           # System + user prompt builders for Node 2
│   ├── build_outline.py          # System + user prompt builders for Node 3
│   └── generate_section.py       # System + user prompt builders for Node 4
│
├── services/
│   └── serp_client.py            # SerpAPI call + 10-result mock with PAA questions
│
├── db/
│   └── jobs.py                   # SQLite helpers: init_jobs_db, create_job, update_job, get_job
│
└── tests/
    ├── test_seo_constraints.py   # 12 SEO validation tests
    └── fixtures/
        └── sample_output.json    # Pre-generated ArticleOutput for offline testing
```

---

## Setup

### Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11+ | |
| Anthropic API key | Requires access to `claude-sonnet-4-6` |
| SerpAPI key | Optional — use `use_mock: true` in requests to skip |

### Installation

```bash
cd seo_agent

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Open .env and fill in your API keys
```

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | **Yes** | API key for Claude (claude-sonnet-4-6) |
| `SERPAPI_KEY` | No\* | SerpAPI key for live Google SERP data |
| `LANGCHAIN_TRACING_V2` | No | Set to `true` to enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | No | LangSmith API key (required if tracing enabled) |
| `LANGCHAIN_PROJECT` | No | LangSmith project name for grouping traces |

\* Not required when `use_mock: true` is set in the job request.

---

## Running the Server

```bash
uvicorn main:app --reload --port 8000
```

Interactive API docs: **http://localhost:8000/docs**

On first startup:
- `jobs.db` is created automatically by `init_jobs_db()` in the lifespan handler
- `checkpoints.db` is created automatically by LangGraph's `AsyncSqliteSaver`

Both files are gitignored and should not be committed.

---

## API Reference

### POST /jobs — Submit a Job

Accepts a topic and generation parameters. Returns a `thread_id` immediately (`202 Accepted`). The pipeline runs in the background via FastAPI `BackgroundTasks`.

**Request body:**

| Field | Type | Default | Description |
|---|---|---|---|
| `topic` | string | required | Article topic or search keyword |
| `target_word_count` | int | `1500` | Target article length |
| `language` | string | `"en"` | ISO 639-1 language code |
| `use_mock` | bool | `false` | Skip SerpAPI; use built-in mock SERP data |

```python
import httpx

response = httpx.post(
    "http://localhost:8000/jobs",
    json={
        "topic": "best productivity tools for remote teams",
        "target_word_count": 1500,
        "language": "en",
        "use_mock": True,   # set False with a real SERPAPI_KEY
    },
)
response.raise_for_status()
data = response.json()
thread_id = data["thread_id"]
print(f"Submitted: {thread_id}  status={data['status']}")
```

Response (`202 Accepted`):
```json
{ "thread_id": "3f8a2c1d-...", "status": "pending" }
```

---

### GET /jobs/{thread_id} — Poll Status

Returns current job status and the name of the pipeline node that most recently completed. Poll this endpoint until `status` is `completed` or `failed`.

**Status lifecycle:** `pending` → `running` → `completed` | `failed`

**`execution_stage` values** (in order): `serp_fetch` · `analyze_serp` · `build_outline` · `generate_sections` · `postprocess` · `validate_output`

The `result_preview` field (first 300 characters of `body_markdown`) becomes populated after `postprocess` completes — useful for confirming the article is generating sensible content before the full result is ready.

```python
import httpx, time

def poll_until_done(thread_id: str, interval: float = 5.0) -> dict:
    url = f"http://localhost:8000/jobs/{thread_id}"
    while True:
        resp = httpx.get(url)
        resp.raise_for_status()
        job = resp.json()
        print(f"  stage={job.get('execution_stage') or '—':25}  status={job['status']}")
        if job["status"] in ("completed", "failed"):
            return job
        time.sleep(interval)

result = poll_until_done(thread_id)
```

Response example (mid-run):
```json
{
  "thread_id": "3f8a2c1d-...",
  "status": "running",
  "execution_stage": "generate_sections",
  "topic": "best productivity tools for remote teams",
  "created_at": "2025-03-10 12:00:00",
  "updated_at": "2025-03-10 12:00:45",
  "error_message": null,
  "result_preview": null
}
```

---

### GET /jobs/{thread_id}/result — Fetch the Article

Returns the full `ArticleOutput` once `status` is `completed`. Returns `409 Conflict` if the job is still running or has failed.

```python
import httpx

resp = httpx.get(f"http://localhost:8000/jobs/{thread_id}/result")
resp.raise_for_status()   # raises 409 if not yet completed
article = resp.json()

print(article["h1"])
print(f"Word count : {article['word_count']}")
print(f"SEO score  : {article['validation_results']['overall_score']}/100")
```

---

### POST /jobs/{thread_id}/resume — Resume a Failed Job

Re-enters the graph from the last LangGraph checkpoint. Valid for jobs with status `failed` or stale `running`. LangGraph determines the resumption point automatically from `checkpoints.db` — no configuration needed.

```python
import httpx

resp = httpx.post(f"http://localhost:8000/jobs/{thread_id}/resume")
resp.raise_for_status()
print(resp.json())   # {"thread_id": "...", "status": "running"}
```

---

### End-to-End Example

```python
import httpx, time

BASE = "http://localhost:8000"

def generate_article(topic: str, word_count: int = 1500, use_mock: bool = True) -> dict:
    # 1. Submit job
    resp = httpx.post(f"{BASE}/jobs", json={
        "topic": topic,
        "target_word_count": word_count,
        "use_mock": use_mock,
    })
    resp.raise_for_status()
    thread_id = resp.json()["thread_id"]
    print(f"Submitted: {thread_id}")

    # 2. Poll until done
    while True:
        resp = httpx.get(f"{BASE}/jobs/{thread_id}")
        resp.raise_for_status()
        job = resp.json()
        print(f"  [{job.get('execution_stage') or '—'}]  {job['status']}")
        if job["status"] == "completed":
            break
        if job["status"] == "failed":
            raise RuntimeError(f"Job failed: {job['error_message']}")
        time.sleep(5)

    # 3. Fetch result
    resp = httpx.get(f"{BASE}/jobs/{thread_id}/result")
    resp.raise_for_status()
    return resp.json()


article = generate_article("best productivity tools for remote teams")
print(f"\nH1    : {article['h1']}")
print(f"Words : {article['word_count']}")
print(f"Score : {article['validation_results']['overall_score']}/100")
```

---

## Output Schema

The `/result` endpoint returns a single `ArticleOutput` object:

| Field | Type | Description |
|---|---|---|
| `thread_id` | string | Job identifier |
| `h1` | string | Article H1 title (contains primary keyword) |
| `meta_title` | string | SEO meta title (50-60 chars) |
| `meta_description` | string | SEO meta description (150-160 chars) |
| `body_markdown` | string | Full article with `##` H2 and `###` H3 headings |
| `word_count` | int | Actual word count of the generated body |
| `keyword_analysis` | object | Primary + secondary keyword density breakdown |
| `internal_links` | array | 3-5 internal link suggestions with anchor text and target topic |
| `external_references` | array | 2-4 citation placements with source name, URL, and section hint |
| `faq` | array | FAQ items generated from People Also Ask questions |
| `validation_results` | object | 10 SEO check results + `overall_score` (0-100) |

```json
{
  "thread_id": "3f8a2c1d-...",
  "h1": "Best Productivity Tools for Remote Teams in 2025",
  "meta_title": "Best Productivity Tools for Remote Teams 2025",
  "meta_description": "Discover the top productivity tools for remote teams — from async communication to project tracking. Reviewed and ranked for distributed workflows in 2025.",
  "body_markdown": "# Best Productivity Tools for Remote Teams in 2025\n\n## Why Remote Teams Need the Right Tools\n\n...",
  "word_count": 1487,
  "keyword_analysis": {
    "primary_keyword": "productivity tools for remote teams",
    "primary_keyword_count": 14,
    "keyword_density": 0.0094,
    "secondary_keywords": [
      {
        "keyword": "remote collaboration software",
        "count": 6,
        "sections_present": ["Communication Tools", "Project Management"]
      }
    ]
  },
  "internal_links": [
    {
      "anchor_text": "async communication guide",
      "suggested_target_topic": "asynchronous communication best practices",
      "context_hint": "mention in the communication section"
    }
  ],
  "external_references": [
    {
      "source_name": "Harvard Business Review",
      "source_url": "https://hbr.org/...",
      "placement_section": "Why Remote Teams Need the Right Tools",
      "relevance_note": "remote work productivity research"
    }
  ],
  "faq": [
    {
      "question": "What tools do remote teams use to stay productive?",
      "answer": "Remote teams typically use a combination of project management platforms..."
    }
  ],
  "validation_results": {
    "passed": true,
    "overall_score": 90,
    "checks": [
      { "check_name": "meta_title_length", "passed": true, "detail": "Meta title is 47 characters (target: 50-60)." }
    ]
  }
}
```

---

## SEO Validation

Node 6 (`validate_output`) runs 10 deterministic SEO checks using only regex and arithmetic — no LLM involved. Results are attached to `validation_results` on the `ArticleOutput`. The test suite validates the same checks against a pre-generated fixture.

| Check | Pass Condition | Method |
|---|---|---|
| `meta_title_length` | 50-60 characters | `len()` |
| `meta_description_length` | 150-160 characters | `len()` |
| `primary_keyword_in_h1` | Keyword appears (case-insensitive) in H1 | `str.lower()` + `in` |
| `word_count_within_10pct` | Within ±10% of `target_word_count` | Arithmetic |
| `single_h1` | Exactly one `# ` heading | `re.findall(r'^# [^\n]+', ..., re.MULTILINE)` |
| `no_h3_without_h2` | No `### ` heading before first `## ` | Line-by-line scan |
| `internal_links_count` | 3-5 links | `len()` |
| `external_references_count` | 2-4 references | `len()` |
| `keyword_density` | 0.5%-2.5% of total words | `primary_count / word_count` |
| `faq_present` | ≥3 FAQ items | `len()` |

`overall_score` = percentage of checks passed (0-100).

---

## Tests

```bash
cd seo_agent
pytest tests/ -v
```

Tests run against `tests/fixtures/sample_output.json` — a pre-generated `ArticleOutput`. No running server or API calls required.

| Test | What It Checks |
|---|---|
| `test_meta_title_length` | Meta title is 50-60 characters |
| `test_meta_description_length` | Meta description is 150-160 characters |
| `test_primary_keyword_in_h1` | Primary keyword appears in H1 |
| `test_keyword_density_in_range` | Keyword density between 0.5%-2.5% |
| `test_single_h1` | Exactly one H1 heading in body |
| `test_no_h3_without_h2` | Valid heading hierarchy (no orphaned H3) |
| `test_internal_links_count` | 3-5 internal link suggestions |
| `test_external_references_count` | 2-4 external references |
| `test_faq_not_empty` | At least 3 FAQ items present |
| `test_faq_items_have_answers` | All FAQ items have non-empty question and answer |
| `test_validation_results_attached` | `validation_results` field is present and not None |
| `test_validation_score_reasonable` | `overall_score` ≥70 |

---

## Extension Points

**Revision loop** — `graph/builder.py` contains a commented-out `add_conditional_edges` call. Replacing the `validate_output → END` edge with a conditional that routes back to `generate_sections` when `overall_score` is below a threshold would enable automatic revision until all SEO checks pass. The `operator.add` reducer on `generated_sections` already makes this idempotent.

**Per-section DDGS search** — `serp_fetch` could be extended with a DuckDuckGo search phase for more targeted per-section content grounding. Currently omitted due to scraper fragility (~10s added latency per article, no uptime guarantee).

**LangSmith tracing** — Set `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` in `.env` to stream full node-level execution traces to LangSmith. No code changes required; the `lifespan` pattern is already compatible.
