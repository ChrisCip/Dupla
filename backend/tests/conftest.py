import os
import socket
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.module import Module
from app.models.task_board import TaskList
from app.models.user import User, UserModule, UserRole
from app.security.password import hash_password


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def database_url() -> str:
    return os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://dupla:dupla@127.0.0.1:5432/dupla")


def _postgres_reachable(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


@pytest_asyncio.fixture(scope="session")
async def engine(database_url: str):
    if not _postgres_reachable("127.0.0.1", 5432):
        pytest.skip("PostgreSQL not reachable on 127.0.0.1:5432 (start docker compose postgres)")
    eng = create_async_engine(database_url, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture()
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as s:
        await s.execute(
            text(
                "TRUNCATE chat_messages, task_cards, task_lists, user_modules, "
                "project_architecture_data, projects, users, modules RESTART IDENTITY CASCADE"
            )
        )
        await s.commit()

        s.add(Module(id=1, name="Arquitectura"))
        s.add(
            TaskList(
                id=uuid.UUID("a0000001-0000-4000-8000-000000000001"),
                title="Por hacer",
                position=0,
            )
        )
        s.add(
            TaskList(
                id=uuid.UUID("a0000001-0000-4000-8000-000000000002"),
                title="En progreso",
                position=1,
            )
        )
        s.add(
            TaskList(
                id=uuid.UUID("a0000001-0000-4000-8000-000000000003"),
                title="Hecho",
                position=2,
            )
        )
        uid = uuid.uuid4()
        s.add(
            User(
                id=uid,
                email="tester@dupla.demo",
                password_hash=hash_password("testpass123"),
                role=UserRole.MASTER,
            )
        )
        s.add(UserModule(user_id=uid, module_id=1))
        worker_id = uuid.uuid4()
        s.add(
            User(
                id=worker_id,
                email="worker@dupla.demo",
                password_hash=hash_password("workerpass123"),
                role=UserRole.WORKER,
            )
        )
        s.add(UserModule(user_id=worker_id, module_id=1))
        await s.commit()
        yield s


@pytest_asyncio.fixture()
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def auth_headers_async(client: AsyncClient) -> dict[str, str]:
    res = await client.post(
        "/api/auth/token",
        data={"username": "tester@dupla.demo", "password": "testpass123"},
    )
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
