import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.exc import ProgrammingError

from app.db.session import AsyncSessionLocal
from app.models.module import Module
from app.models.user import User, UserModule, UserRole
from app.security.password import hash_password


_MISSING_SCHEMA_HINT = (
    "No hay tablas en la base de datos. Aplica las migraciones antes del seed:\n"
    "  cd backend && alembic upgrade head\n"
    "Luego vuelve a ejecutar: python -m app.seed"
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


async def _seed_impl() -> None:
    async with AsyncSessionLocal() as session:
        mod = await session.execute(select(Module).where(Module.id == 1))
        if mod.scalar_one_or_none() is None:
            session.add(Module(id=1, name="Arquitectura"))
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == "master@dupla.demo"))
        if result.scalar_one_or_none() is not None:
            return
        uid = uuid.uuid4()
        user = User(
            id=uid,
            email="master@dupla.demo",
            password_hash=hash_password("master123"),
            role=UserRole.MASTER,
        )
        session.add(user)
        session.add(UserModule(user_id=uid, module_id=1))
        await session.commit()


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
