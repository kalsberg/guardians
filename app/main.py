from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated, Dict, Optional

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import TokenResponse, User, authenticate_user, create_access_token, get_current_user, is_admin
from .database import get_db, get_default_database_url, make_engine, make_session_factory
from .models import Base, Project
from .schemas import ProjectCreate, ProjectRead, ProjectUpdate


def create_app(database_url: Optional[str] = None) -> FastAPI:
    url = database_url or get_default_database_url()
    engine = make_engine(url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.engine = engine
        app.state.session_factory = make_session_factory(engine)
        Base.metadata.create_all(bind=app.state.engine)
        yield

    app = FastAPI(title="Project Registry API", version="1.0.0", lifespan=lifespan)

    @app.get("/health", tags=["health"])
    def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.post("/auth/token", response_model=TokenResponse, tags=["auth"])
    def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> TokenResponse:
        user = authenticate_user(form_data.username, form_data.password)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return TokenResponse(access_token=create_access_token(user))

    @app.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED, tags=["projects"])
    def create_project(
        payload: ProjectCreate,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> Project:
        data = payload.model_dump()
        if not is_admin(current_user):
            data["owner"] = current_user.username

        project = Project(**data)
        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    @app.get("/projects", response_model=list[ProjectRead], tags=["projects"])
    def list_projects(
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_user)],
        owner: Optional[str] = None,
    ) -> list[Project]:
        query = select(Project)

        if is_admin(current_user):
            if owner:
                query = query.where(Project.owner == owner)
        else:
            if owner and owner != current_user.username:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
            query = query.where(Project.owner == current_user.username)

        return list(db.scalars(query.order_by(Project.id.asc())).all())

    @app.get("/projects/{project_id}", response_model=ProjectRead, tags=["projects"])
    def get_project(
        project_id: int,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> Project:
        project = db.get(Project, project_id)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        if not is_admin(current_user) and project.owner != current_user.username:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return project

    @app.put("/projects/{project_id}", response_model=ProjectRead, tags=["projects"])
    def update_project(
        project_id: int,
        payload: ProjectUpdate,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> Project:
        project = db.get(Project, project_id)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        if not is_admin(current_user) and project.owner != current_user.username:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")

        if not is_admin(current_user) and "owner" in updates and updates["owner"] != current_user.username:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        for field, value in updates.items():
            setattr(project, field, value)

        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    @app.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["projects"])
    def delete_project(
        project_id: int,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> Response:
        project = db.get(Project, project_id)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        if not is_admin(current_user) and project.owner != current_user.username:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        db.delete(project)
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app


app = create_app()
