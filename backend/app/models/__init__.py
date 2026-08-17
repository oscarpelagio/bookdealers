"""Paquet de models de dades."""

from .book import Book
from .search_cache import Search, SearchRelation
from .book_establishment import BookEstablishment
from .establishments import Establishment
from .catalogs import Catalog
from .seed_aladi import SeedAladi
from .author_photo import AuthorPhoto
from .author_source import AuthorSource
from .author_source_related import AuthorSourceRelated
from .penguin_author_index import PenguinAuthorIndex
from .asteroide_author_index import AsteroideAuthorIndex
from .central_blog_article import CentralBlogArticle
from .central_blog_article_book import CentralBlogArticleBook

# Models del mòdul d'autenticació (re-exportats perquè create_all/Alembic
# els detectin a través de SQLModel.metadata).
from app.auth.models import (
    EmailVerificationToken,
    PasswordResetToken,
    RefreshToken,
    Role,
    User,
    UserRole,
)

# Models del context social (re-exportats perquè create_all/Alembic els
# detectin a través de SQLModel.metadata). Només s'hi afegeixen nous models;
# no es toca cap dels existents.
from app.profiles.models import (
    PrivacySetting,
    Profile,
    ProfilePreference,
    ReadingGoal,
)

from app.shelves.models import (
    ReadingProgress,
    Shelf,
    ShelfItem,
    UserBook,
)

from app.favorites.models import (
    UserCatalog,
    UserFavoriteEstablishment,
    UserSearchHistory,
)

from app.reviews.models import (
    Rating,
    Review,
    ReviewLike,
)

from app.social.models import (
    Activity,
    Block,
    Follow,
    Mute,
    Report,
)

from app.posts.models import (
    Comment,
    CommentLike,
    Mention,
    Post,
    PostLike,
    PostMedia,
)

from app.lists.models import (
    List,
    ListCollaborator,
    ListItem,
)

from app.notifications.models import (
    Notification,
    NotificationSetting,
    PushQueue,
)
