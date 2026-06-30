"""Data access repositories."""

from app.database.repositories.bookmark import BookmarkRepository
from app.database.repositories.chat import ChatRepository
from app.database.repositories.collection import CollectionRepository
from app.database.repositories.notification import NotificationRepository
from app.database.repositories.saved_search import SavedSearchRepository
from app.database.repositories.search import SearchRepository
from app.database.repositories.session import SessionRepository
from app.database.repositories.user import UserRepository

__all__ = [
    "BookmarkRepository",
    "ChatRepository",
    "CollectionRepository",
    "NotificationRepository",
    "SavedSearchRepository",
    "SearchRepository",
    "SessionRepository",
    "UserRepository",
]
