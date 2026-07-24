"""Base interface for availability adapters."""

from abc import ABC, abstractmethod

from app.models import Book, Catalog
from app.schemas import AvailabilityBase, FetchRequest


class AvailabilityBaseAdapter(ABC):

    @abstractmethod
    def build_search(self, book: Book, catalog: Catalog) -> FetchRequest:
        """Build a request for an availability lookup."""
        raise NotImplementedError

    @abstractmethod
    def response_adapter(
        self, book: Book, catalog: Catalog, response: object
    ) -> list[AvailabilityBase]:
        """Parse an availability response into the domain model."""
        raise NotImplementedError
