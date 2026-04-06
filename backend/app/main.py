from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import admin, auth, chat, modules, project_lifecycle, projects, tasks, users

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Grupo Dupla — Arquitectura API",
        description=(
            "**Auth:** `POST /api/auth/token` with form fields `username` (email) and `password`. "
            "Use **Authorize** in Swagger with `Bearer <access_token>`."
        ),
        version="0.1.0",
        lifespan=lifespan,
        swagger_ui_parameters={"persistAuthorization": True},
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(modules.router)
    app.include_router(projects.router)
    app.include_router(project_lifecycle.router)
    app.include_router(admin.router)
    app.include_router(chat.router)
    app.include_router(tasks.router)
    return app


app = create_app()
