"""Paquet d'esquemes de validació per a l'API."""

from .book import BookBase, BookCreate, BookUpdate, BookResponse, BookSearchResponse
from .availability import AvailabilityBase
from .fetch_request import FetchRequest
from .author_source import AuthorProfileLookup, PublisherRelatedItem
from .central_blog import BookAppearsInList, BookAppearsInResponse, CentralListResponse
