"""Paquet de clients per a APIs externes."""
from .search_base_client import SearchBaseClient
from .availability_base_client import AvailabilityBaseClient

from .google_client import GoogleBooksClient
from .open_library_client import OpenLibraryClient
from .z3950_client import Z3950Client
from .ebiblio_client import eBiblioClient
from .todostuslibros_client import TodostuslibrosClient
