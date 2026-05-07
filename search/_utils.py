"""Shared types for the search module."""

from dataclasses import dataclass


@dataclass
class SearchResult:
    """A single search result from any engine."""

    title: str
    url: str
    snippet: str
    content: str = ""
