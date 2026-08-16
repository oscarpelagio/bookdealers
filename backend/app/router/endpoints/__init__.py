"""API v1 endpoints package."""

from .search_router import router as search_router
from .import_router import router as import_router
from .availability_router import router as availability_router
from .books_router import router as books_router
from .author_photo_router import router as author_photo_router
from .anagrama_router import router as anagrama_router
from .author_profile_router import router as author_profile_router
from .thumb_router import router as thumb_router
from .central_blog_router import router as central_blog_router
