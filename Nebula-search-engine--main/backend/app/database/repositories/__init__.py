"""Data access repositories."""

from app.database.repositories.api_key import APIKeyRepository
from app.database.repositories.audit import AuditRepository
from app.database.repositories.bookmark import BookmarkRepository
from app.database.repositories.chat import ChatRepository
from app.database.repositories.collection import CollectionRepository
from app.database.repositories.document import DocumentRepository
from app.database.repositories.export import ExportRepository
from app.database.repositories.notification import NotificationRepository
from app.database.repositories.saved_search import SavedSearchRepository
from app.database.repositories.search import SearchRepository
from app.database.repositories.search_click import SearchClickRepository
from app.database.repositories.session import SessionRepository
from app.database.repositories.settings import SettingsRepository
from app.database.repositories.social_account import SocialAccountRepository
from app.database.repositories.user import UserRepository

__all__ = [
    "APIKeyRepository",
    "AuditRepository",
    "BookmarkRepository",
    "ChatRepository",
    "CollectionRepository",
    "DocumentRepository",
    "ExportRepository",
    "NotificationRepository",
    "SavedSearchRepository",
    "SearchRepository",
    "SearchClickRepository",
    "SessionRepository",
    "SettingsRepository",
    "SocialAccountRepository",
    "UserRepository",
]
