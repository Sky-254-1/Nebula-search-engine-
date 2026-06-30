"""Admin-only routes for system management."""

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.database.repositories.audit import AuditRepository
from app.database.repositories.session import SessionRepository
from app.database.repositories.user import UserRepository
from app.services.auth import require_admin

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


@router.get("/audit-logs", dependencies=[Depends(require_admin)])
async def get_audit_logs(limit: int = 100, db=Depends(get_db)):
    audit = AuditRepository(db)
    logs = await audit.get_recent(limit=limit)
    return {"logs": logs}


@router.get("/users/{user_id}/sessions", dependencies=[Depends(require_admin)])
async def get_user_sessions(user_id: int, limit: int = 50, db=Depends(get_db)):
    sessions = SessionRepository(db)
    rows = await sessions.list_for_user(user_id, limit)
    return {"user_id": user_id, "sessions": rows, "count": len(rows)}


@router.post("/sessions/{session_id}/revoke", dependencies=[Depends(require_admin)])
async def revoke_session(session_id: str, db=Depends(get_db)):
    sessions = SessionRepository(db)
    await sessions.revoke_session_family(session_id, "Revoked by administrator")
    return {"message": f"Session family {session_id} revoked"}


@router.post("/users/{user_id}/role", dependencies=[Depends(require_admin)])
async def update_user_role(user_id: int, role: str, db=Depends(get_db)):
    if role not in ["user", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    users = UserRepository(db)
    await users.update_role(user_id, role)
    return {"message": f"User {user_id} role updated to {role}"}
