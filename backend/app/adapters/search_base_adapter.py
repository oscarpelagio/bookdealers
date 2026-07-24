"""Base interface for search adapters."""

from abc import ABC, abstractmethod

from app.schemas import BookBase


class SearchBaseAdapter(ABC):

    @abstractmethod
    def build_search(
        self, title: str | None, author: str | None, max_results: int = 10
    ) -> dict:
        """Build a search request payload for an external provider."""
        raise NotImplementedError

    @abstractmethod
    def response_adapter(self, results: dict) -> list[BookBase]:
        """Parse provider results into the domain model."""
        raise NotImplementedError
