"""SerpAPI wrapper with a rich mock for testing (use_mock=True)."""
from __future__ import annotations
import os
from typing import Optional

from models.serp import SerpData, SerpResult, PeopleAlsoAsk


# ── Mock data ──────────────────────────────────────────────────────────────────

_MOCK_RESULTS = [
    SerpResult(rank=1, url="https://example.com/productivity-tools-remote-teams",
               title="15 Best Productivity Tools for Remote Teams in 2025",
               snippet="Remote teams need the right tools to stay connected and productive. "
                       "From project management apps like Asana to communication platforms like Slack, "
                       "these tools streamline collaboration across time zones."),
    SerpResult(rank=2, url="https://example.com/remote-work-software",
               title="Top Remote Work Software for Distributed Teams",
               snippet="Managing a distributed team requires purpose-built software. "
                       "Tools like Notion, Trello, and Monday.com help remote workers "
                       "organize tasks, track progress, and meet deadlines efficiently."),
    SerpResult(rank=3, url="https://example.com/best-apps-remote-workers",
               title="Best Apps for Remote Workers: Communication, Project Mgmt & More",
               snippet="The best apps for remote workers cover every workflow: "
                       "Zoom for video calls, Slack for messaging, Toggl for time tracking, "
                       "and Loom for async video updates."),
    SerpResult(rank=4, url="https://example.com/remote-team-collaboration",
               title="Remote Team Collaboration Tools That Actually Work",
               snippet="Effective remote collaboration hinges on three pillars: communication, "
                       "documentation, and project tracking. Tools like Confluence, Miro, and "
                       "ClickUp cover all three."),
    SerpResult(rank=5, url="https://example.com/productivity-software-2025",
               title="Productivity Software for Remote Teams: 2025 Buyer's Guide",
               snippet="When evaluating productivity software, consider integrations, pricing, "
                       "and ease of onboarding. This guide covers Asana, Monday.com, Linear, "
                       "and Basecamp side by side."),
    SerpResult(rank=6, url="https://example.com/async-work-tools",
               title="Async-First Tools for Global Remote Teams",
               snippet="Async-first companies swear by tools like Loom, Notion, and Linear. "
                       "Reducing meeting load while maintaining alignment is the key productivity "
                       "lever for distributed teams."),
    SerpResult(rank=7, url="https://example.com/time-tracking-remote",
               title="Time Tracking and Accountability Tools for Remote Employees",
               snippet="Time tracking tools like Toggl Track, Harvest, and Clockify help remote "
                       "managers monitor billable hours and identify productivity bottlenecks "
                       "without micromanaging."),
    SerpResult(rank=8, url="https://example.com/remote-team-communication",
               title="Communication Tools for Remote Teams: Beyond Slack",
               snippet="While Slack dominates remote team chat, tools like Discord, Teams, and "
                       "Twist offer unique advantages. Twist's thread-first design reduces "
                       "notification overload for deep-work focused teams."),
    SerpResult(rank=9, url="https://example.com/project-management-remote",
               title="Project Management Tools Ranked for Remote Teams",
               snippet="Asana, ClickUp, and Monday.com are the top-rated project management "
                       "platforms for remote teams. Each offers Kanban boards, Gantt charts, "
                       "and time tracking in a single workspace."),
    SerpResult(rank=10, url="https://example.com/remote-work-stack",
               title="Building the Perfect Remote Work Tech Stack",
               snippet="A lean remote work stack typically includes a communication tool, "
                       "a project manager, a wiki, and a video platform. Avoid tool sprawl "
                       "by choosing platforms with native integrations."),
]

_MOCK_PAA = [
    PeopleAlsoAsk(question="What are the best free productivity tools for remote teams?"),
    PeopleAlsoAsk(question="How do remote teams stay productive?"),
    PeopleAlsoAsk(question="What project management tool is best for remote teams?"),
    PeopleAlsoAsk(question="How do you manage communication in a remote team?"),
    PeopleAlsoAsk(question="What is the best tool for async collaboration?"),
]


def _mock_serp(keyword: str) -> SerpData:
    return SerpData(
        keyword=keyword,
        results=_MOCK_RESULTS,
        people_also_ask=_MOCK_PAA,
    )


# ── Real SerpAPI ───────────────────────────────────────────────────────────────

def _real_serp(keyword: str) -> SerpData:
    from serpapi import GoogleSearch  # type: ignore

    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        raise RuntimeError("SERPAPI_KEY environment variable is not set")

    params = {
        "q": keyword,
        "hl": "en",
        "gl": "us",
        "num": 10,
        "api_key": api_key,
    }
    search = GoogleSearch(params)
    raw = search.get_dict()

    organic = raw.get("organic_results", [])[:10]
    results = [
        SerpResult(
            rank=i + 1,
            url=r.get("link", ""),
            title=r.get("title", ""),
            snippet=r.get("snippet", ""),
        )
        for i, r in enumerate(organic)
    ]

    paa_raw = raw.get("related_questions", [])
    people_also_ask = [
        PeopleAlsoAsk(question=q.get("question", ""))
        for q in paa_raw
        if q.get("question")
    ]

    return SerpData(keyword=keyword, results=results, people_also_ask=people_also_ask)


# ── Public API ─────────────────────────────────────────────────────────────────

def fetch_serp(keyword: str, use_mock: bool = False) -> SerpData:
    """Fetch SERP data for a keyword. Falls back to mock on failure."""
    if use_mock:
        return _mock_serp(keyword)
    try:
        return _real_serp(keyword)
    except Exception as exc:
        raise RuntimeError(f"SerpAPI call failed: {exc}") from exc
