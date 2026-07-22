"""Role-Based Access Control (RBAC) service."""

from typing import List
from dataclasses import dataclass

from app.config import get_settings

settings = get_settings()


@dataclass
class Permission:
    """Permission definition."""
    id: int
    name: str
    display_name: str
    description: str
    resource: str
    action: str
    is_system: bool = False
    is_active: bool = True


@dataclass
class Role:
    """Role definition."""
    id: int
    name: str
    display_name: str
    description: str
    level: int
    is_system: bool = False
    is_active: bool = True
    permissions: List[Permission] = None

    def __post_init__(self):
        if self.permissions is None:
            self.permissions = []


class RBACService:
    """Role-Based Access Control service."""

    # System roles with their levels
    SYSTEM_ROLES = {
        "super_admin": 100,
        "admin": 80,
        "moderator": 50,
        "user": 10,
        "guest": 1,
    }

    # Role hierarchy (higher level inherits lower level permissions)
    ROLE_HIERARCHY = {
        "super_admin": ["admin", "moderator", "user", "guest"],
        "admin": ["moderator", "user", "guest"],
        "moderator": ["user", "guest"],
        "user": ["guest"],
        "guest": [],
    }

    @staticmethod
    def get_role_level(role_name: str) -> int:
        """Get role level."""
        return RBACService.SYSTEM_ROLES.get(role_name, 0)

    @staticmethod
    def has_role_hierarchy(user_role: str, required_role: str) -> bool:
        """Check if user role has hierarchy over required role."""
        user_level = RBACService.get_role_level(user_role)
        required_level = RBACService.get_role_level(required_role)
        return user_level >= required_level

    @staticmethod
    def get_inherited_roles(role_name: str) -> List[str]:
        """Get all roles inherited by a role."""
        return RBACService.ROLE_HIERARCHY.get(role_name, [])

    @staticmethod
    def can_access_resource(user_role: str, resource: str, action: str) -> bool:
        """Check if user role can access a resource with specific action."""
        # Super admin has all permissions
        if user_role == "super_admin":
            return True
        
        # Admin has most permissions
        if user_role == "admin":
            # Admin cannot do everything (e.g., cannot delete super admin)
            restricted_actions = ["users.admin", "admin.access"]
            permission_name = f"{resource}.{action}"
            if permission_name in restricted_actions:
                return False
            return True
        
        # Moderator can moderate content
        if user_role == "moderator":
            allowed_resources = ["searches", "files"]
            if resource in allowed_resources:
                allowed_actions = ["read", "delete", "manage"]
                return action in allowed_actions
            return False
        
        # User can access basic features
        if user_role == "user":
            allowed_permissions = [
                "searches.create",
                "searches.read",
                "searches.delete",
                "files.upload",
                "files.read",
                "files.delete",
            ]
            permission_name = f"{resource}.{action}"
            return permission_name in allowed_permissions
        
        # Guest has minimal access
        if user_role == "guest":
            allowed_permissions = ["searches.create"]
            permission_name = f"{resource}.{action}"
            return permission_name in allowed_permissions
        
        return False

    @staticmethod
    def get_user_permissions(user_role: str, user_permissions: List[str] = None) -> List[str]:
        """Get all permissions for a user role."""
        permissions = set(user_permissions or [])
        
        # Add role-based permissions
        if user_role == "super_admin":
            # All permissions
            permissions.update([
                "users.create", "users.read", "users.update", "users.delete", "users.admin",
                "searches.create", "searches.read", "searches.delete",
                "files.upload", "files.read", "files.delete", "files.manage",
                "analytics.view",
                "admin.access",
            ])
        elif user_role == "admin":
            permissions.update([
                "users.create", "users.read", "users.update", "users.delete",
                "searches.create", "searches.read", "searches.delete",
                "files.upload", "files.read", "files.delete", "files.manage",
                "analytics.view",
            ])
        elif user_role == "moderator":
            permissions.update([
                "searches.read", "searches.delete",
                "files.read", "files.delete",
            ])
        elif user_role == "user":
            permissions.update([
                "searches.create", "searches.read", "searches.delete",
                "files.upload", "files.read", "files.delete",
            ])
        elif user_role == "guest":
            permissions.update([
                "searches.create",
            ])
        
        return list(permissions)

    @staticmethod
    def check_permission(user_role: str, permission: str, user_permissions: List[str] = None) -> bool:
        """Check if user has specific permission."""
        # Super admin has all permissions
        if user_role == "super_admin":
            return True
        
        # Check explicit permissions
        all_permissions = RBACService.get_user_permissions(user_role, user_permissions)
        return permission in all_permissions

    @staticmethod
    def require_permission(permission: str):
        """Dependency factory for permission checking."""
        from fastapi import HTTPException, Request
        from app.services.auth import get_current_user_token_payload
        
        async def permission_checker(request: Request):
            payload = await get_current_user_token_payload(request)
            user_role = payload.get("role", "user")
            user_permissions = payload.get("permissions", [])
            
            if not RBACService.check_permission(user_role, permission, user_permissions):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission required: {permission}"
                )
            
            return payload
        
        return permission_checker

    @staticmethod
    def require_any_permission(permissions: List[str]):
        """Dependency factory for checking any of multiple permissions."""
        from fastapi import HTTPException, Request
        from app.services.auth import get_current_user_token_payload
        
        async def permission_checker(request: Request):
            payload = await get_current_user_token_payload(request)
            user_role = payload.get("role", "user")
            user_permissions = payload.get("permissions", [])
            
            has_permission = any(
                RBACService.check_permission(user_role, perm, user_permissions)
                for perm in permissions
            )
            
            if not has_permission:
                raise HTTPException(
                    status_code=403,
                    detail=f"One of these permissions required: {', '.join(permissions)}"
                )
            
            return payload
        
        return permission_checker

    @staticmethod
    def require_all_permissions(permissions: List[str]):
        """Dependency factory for checking all of multiple permissions."""
        from fastapi import HTTPException, Request
        from app.services.auth import get_current_user_token_payload
        
        async def permission_checker(request: Request):
            payload = await get_current_user_token_payload(request)
            user_role = payload.get("role", "user")
            user_permissions = payload.get("permissions", [])
            
            has_all_permissions = all(
                RBACService.check_permission(user_role, perm, user_permissions)
                for perm in permissions
            )
            
            if not has_all_permissions:
                raise HTTPException(
                    status_code=403,
                    detail=f"All of these permissions required: {', '.join(permissions)}"
                )
            
            return payload
        
        return permission_checker


# Convenience functions for common permission checks
require_admin = RBACService.require_permission("admin.access")
require_user_management = RBACService.require_permission("users.admin")
require_file_management = RBACService.require_permission("files.manage")
require_analytics_access = RBACService.require_permission("analytics.view")