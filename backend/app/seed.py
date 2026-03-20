import asyncio
import uuid

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.module import Module
from app.models.user import User, UserModule, UserRole
from app.security.password import hash_password


async def seed() -> None:
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
