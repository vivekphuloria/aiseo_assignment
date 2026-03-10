"""FastAPI application — SEO Article Generator."""
from __future__ import annotations
import asyncio
import os
from contextlib import asynccontextmanager
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException

from db.jobs import init_jobs_db, create_job, update_job, get_job
from graph.builder import build_graph
from models.article import ArticleOutput
from models.inputs import JobRequest, JobResponse, JobStatusResponse

load_dotenv()

# Node names emitted by LangGraph astream_events
_NODE_STAGES = [
    "serp_fetch",
    "analyze_serp",
    "build_outline",
    "generate_sections",
    "postprocess",
    "validate_output",
]


# ── Lifespan — initialise DBs and build graph ──────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    db_path = os.path.join(os.path.dirname(__file__), "checkpoints.db")
    async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
        await asyncio.to_thread(init_jobs_db)
        app.state.graph = build_graph(checkpointer)
        yield


app = FastAPI(title="SEO Article Generator", lifespan=lifespan)


# ── Background task ────────────────────────────────────────────────────────────

async def run_graph(thread_id: str, request: JobRequest, graph) -> None:
    await asyncio.to_thread(update_job, thread_id, status="running")

    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "topic": request.topic,
        "target_word_count": request.target_word_count,
        "language": request.language,
        "use_mock": request.use_mock,
        "generated_sections": [],
        "error": None,
    }

    try:
        async for event in graph.astream_events(initial_state, config=config, version="v2"):
            event_name = event.get("name", "")
            if event["event"] == "on_chain_end" and event_name in _NODE_STAGES:
                await asyncio.to_thread(
                    update_job, thread_id, execution_stage=event_name
                )

        # Retrieve final state from checkpoint
        snapshot = await graph.aget_state(config)
        article_output: ArticleOutput | None = snapshot.values.get("article_output")

        if article_output is None:
            error = snapshot.values.get("error") or "Graph completed with no article output"
            await asyncio.to_thread(
                update_job, thread_id, status="failed", error_message=error
            )
            return

        # Set the thread_id on the output (postprocess node doesn't have access to it)
        if hasattr(article_output, "thread_id"):
            article_output.thread_id = thread_id

        # Validate: might be a plain dict if LangGraph deserialised from checkpoint
        if isinstance(article_output, dict):
            article_output = ArticleOutput.model_validate(article_output)

        result_json = article_output.model_dump_json()
        result_preview = article_output.body_markdown[:300]

        await asyncio.to_thread(
            update_job,
            thread_id,
            status="completed",
            result_json=result_json,
            result_preview=result_preview,
        )

    except Exception as exc:
        await asyncio.to_thread(
            update_job, thread_id, status="failed", error_message=str(exc)
        )


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.post("/jobs", response_model=JobResponse, status_code=202)
async def submit_job(request: JobRequest, background_tasks: BackgroundTasks):
    """Submit a new SEO article generation job."""
    thread_id = str(uuid4())
    await asyncio.to_thread(create_job, thread_id, request.topic)
    background_tasks.add_task(run_graph, thread_id, request, app.state.graph)
    return JobResponse(thread_id=thread_id, status="pending")


@app.get("/jobs/{thread_id}", response_model=JobStatusResponse)
async def get_job_status(thread_id: str):
    """Poll job status and execution stage."""
    job = await asyncio.to_thread(get_job, thread_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(
        thread_id=job["thread_id"],
        status=job["status"],
        execution_stage=job.get("execution_stage"),
        topic=job.get("topic"),
        created_at=str(job["created_at"]),
        updated_at=str(job["updated_at"]),
        error_message=job.get("error_message"),
        result_preview=job.get("result_preview"),
    )


@app.get("/jobs/{thread_id}/result", response_model=ArticleOutput)
async def get_job_result(thread_id: str):
    """Fetch the full article output once the job is completed."""
    job = await asyncio.to_thread(get_job, thread_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Job is not yet completed (current status: {job['status']})",
        )
    result_json = job.get("result_json")
    if not result_json:
        raise HTTPException(status_code=500, detail="Result data missing from completed job")
    return ArticleOutput.model_validate_json(result_json)


@app.post("/jobs/{thread_id}/resume", response_model=JobResponse, status_code=202)
async def resume_job(thread_id: str, background_tasks: BackgroundTasks):
    """Resume a failed or interrupted job from its last checkpoint."""
    job = await asyncio.to_thread(get_job, thread_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] not in ("failed", "running"):
        raise HTTPException(
            status_code=409,
            detail=f"Only failed or stale running jobs can be resumed (status: {job['status']})",
        )

    # Re-create a minimal JobRequest from the stored topic
    resume_request = JobRequest(
        topic=job["topic"] or "",
        use_mock=False,
    )
    await asyncio.to_thread(
        update_job, thread_id, status="running", error_message=None
    )
    background_tasks.add_task(run_graph, thread_id, resume_request, app.state.graph)
    return JobResponse(thread_id=thread_id, status="running")
