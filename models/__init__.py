from .inputs import JobRequest, JobResponse, JobStatusResponse
from .serp import SerpData, SerpResult, PeopleAlsoAsk
from .outline import SerpAnalysis, ArticleOutline, OutlineSection, InternalLinkSuggestion, ExternalReference
from .article import ArticleOutput, KeywordAnalysis, KeywordOccurrence, FAQItem, ValidationResult, SEOCheck

__all__ = [
    "JobRequest", "JobResponse", "JobStatusResponse",
    "SerpData", "SerpResult", "PeopleAlsoAsk",
    "SerpAnalysis", "ArticleOutline", "OutlineSection",
    "InternalLinkSuggestion", "ExternalReference",
    "ArticleOutput", "KeywordAnalysis", "KeywordOccurrence",
    "FAQItem", "ValidationResult", "SEOCheck",
]
