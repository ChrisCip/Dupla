import asyncio
import uuid
from datetime import datetime, timezone
from typing import Tuple

from sqlalchemy import select
from sqlalchemy.exc import ProgrammingError

from app.db.session import AsyncSessionLocal
from app.models.chat_conversation import (
    GENERAL_CONVERSATION_UUID,
    ChatConversation,
    ChatConversationKind,
)
from app.models.module import Module
from app.models.user import User, UserModule, UserRole
from app.security.password import hash_password


_MISSING_SCHEMA_HINT = (
    "No hay tablas en la base de datos. Aplica las migraciones antes del seed:\n"
    "  cd backend && alembic upgrade head\n"
    "Luego vuelve a ejecutar: python -m app.seed"
)

# Demo users: MASTER (admin + tablero lectura), COORDINATOR (tablero y proyectos), WORKER (operario).
SEED_USERS: Tuple[Tuple[str, str, UserRole], ...] = (
    ("master@dupla.demo", "master123", UserRole.MASTER),
    ("tester@dupla.demo", "testpass123", UserRole.COORDINATOR),
    ("worker@dupla.demo", "workerpass123", UserRole.WORKER),
)


async def seed() -> None:
    try:
        await _seed_impl()
    except ProgrammingError as e:
        orig = getattr(e, "orig", None)
        err = str(orig) if orig is not None else str(e)
        orig_name = type(orig).__name__ if orig is not None else ""
        if "does not exist" in err or "UndefinedTable" in orig_name:
            raise RuntimeError(_MISSING_SCHEMA_HINT) from e
        raise


async def _ensure_module(session) -> None:
    mod = await session.execute(select(Module).where(Module.id == 1))
    if mod.scalar_one_or_none() is None:
        session.add(Module(id=1, name="Arquitectura"))


async def _ensure_general_conversation(session) -> None:
    existing = await session.get(ChatConversation, GENERAL_CONVERSATION_UUID)
    if existing is not None:
        return
    session.add(
        ChatConversation(
            id=GENERAL_CONVERSATION_UUID,
            kind=ChatConversationKind.GENERAL,
            title=None,
            created_at=datetime.now(timezone.utc),
            last_message_at=None,
        )
    )


async def _ensure_user(session, email: str, password_plain: str, role: UserRole) -> None:
    result = await session.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none() is not None:
        return
    uid = uuid.uuid4()
    session.add(
        User(
            id=uid,
            email=email,
            password_hash=hash_password(password_plain),
            role=role,
        )
    )
    session.add(UserModule(user_id=uid, module_id=1))


async def _seed_impl() -> None:
    async with AsyncSessionLocal() as session:
        await _ensure_module(session)
        await _ensure_general_conversation(session)
        await session.commit()

    async with AsyncSessionLocal() as session:
        for email, password_plain, role in SEED_USERS:
            await _ensure_user(session, email, password_plain, role)
        await session.commit()


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
