from typing import List
from pydantic import BaseModel


class SerpResult(BaseModel):
    rank: int
    url: str
    title: str
    snippet: str


class PeopleAlsoAsk(BaseModel):
    question: str


class SerpData(BaseModel):
    keyword: str
    results: List[SerpResult]
    people_also_ask: List[PeopleAlsoAsk] = []
