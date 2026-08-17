"""Main API routes."""

from fastapi import APIRouter
from app.auth.router import router as auth_router
from app.router.endpoints import search_router, import_router, availability_router, books_router, author_photo_router, author_profile_router, thumb_router, central_blog_router, source_list_router
from app.profiles.router import router as profiles_router
from app.shelves.router import router as shelves_router
from app.reviews.router import router as reviews_router
from app.social.router import router as social_router
from app.feed.router import router as feed_router
from app.posts.router import router as posts_router
from app.lists.router import router as lists_router
from app.notifications.router import router as notifications_router
from app.stats.router import router as stats_router
from app.search.router import router as search_social_router
from app.favorites.router import router as favorites_router
from app.recommendations.router import (
    router as recommendations_router,
    popular_router,
)

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(search_router, prefix="/search", tags=["Search"])
api_router.include_router(import_router, prefix="/import", tags=["Import"])
api_router.include_router(availability_router, prefix="/availability", tags=["Availability"])
api_router.include_router(books_router, prefix="/books", tags=["Books"])
api_router.include_router(author_photo_router, prefix="/author-photo", tags=["Authors"])
api_router.include_router(author_profile_router, prefix="/author-profile", tags=["Authors"])
api_router.include_router(thumb_router, prefix="/thumb", tags=["Images"])
api_router.include_router(central_blog_router, prefix="/blog-articles", tags=["La Central"])
api_router.include_router(source_list_router, prefix="/source-lists", tags=["Source Lists"])
api_router.include_router(profiles_router, prefix="/profiles", tags=["Profiles"])
api_router.include_router(shelves_router, tags=["Shelves", "Library"])
api_router.include_router(reviews_router, tags=["Reviews"])
api_router.include_router(social_router, tags=["Social"])
api_router.include_router(feed_router, tags=["Feed"])
api_router.include_router(posts_router, tags=["Posts"])
api_router.include_router(lists_router, tags=["Lists"])
api_router.include_router(notifications_router, tags=["Notifications"])
api_router.include_router(stats_router, tags=["Stats"])
api_router.include_router(favorites_router, tags=["Favorites"])
api_router.include_router(search_social_router, tags=["Search Social"])
api_router.include_router(recommendations_router, tags=["Recommendations"])
api_router.include_router(popular_router, tags=["Recommendations"])
