import logging
import platform
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, inspect, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, get_db
from app.schemas import (
    DevDatabaseStatus,
    DevDiagnostics,
    DevErrorInfo,
    DevTableInfo,
    DevTableClearRequest,
    DevTableClearResult,
)
from app.services.dev_diagnostics import get_recent_errors

router = APIRouter(prefix="/dev", tags=["development"])
logger = logging.getLogger(__name__)
_PROTECTED_TABLES = {"alembic_version"}


def _migration_head() -> str | None:
    backend_dir = Path(__file__).resolve().parents[2]
    alembic_config = Config(str(backend_dir / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(backend_dir / "migrations"))
    return ScriptDirectory.from_config(alembic_config).get_current_head()


def _database_location(bind) -> str:
    url = bind.url
    if url.get_backend_name() == "sqlite":
        database = url.database or ":memory:"
        if database != ":memory:" and not database.startswith("file:"):
            return str(Path(database).expanduser().resolve())
        return database
    return url.render_as_string(hide_password=True)


def _table_infos(db: Session) -> list[DevTableInfo]:
    bind = db.get_bind()
    existing_names = set(inspect(bind).get_table_names())
    table_infos = []
    for table in sorted(Base.metadata.tables.values(), key=lambda item: item.name):
        exists = table.name in existing_names
        row_count = (
            db.scalar(select(func.count()).select_from(table))
            if exists
            else None
        )
        table_infos.append(
            DevTableInfo(
                name=table.name,
                row_count=row_count,
                exists=exists,
                clearable=exists and table.name not in _PROTECTED_TABLES,
            )
        )
    return table_infos


@router.get("/status", response_model=DevDiagnostics)
def read_dev_status(db: Session = Depends(get_db)) -> DevDiagnostics:
    bind = db.get_bind()
    database_connected = False
    current_revision = None
    migration_status = "unknown"
    tables: list[DevTableInfo] = []
    try:
        db.execute(text("SELECT 1"))
        database_connected = True
        existing_names = set(inspect(bind).get_table_names())
        if "alembic_version" in existing_names:
            current_revision = db.scalar(text("SELECT version_num FROM alembic_version"))
        tables = _table_infos(db)
        head_revision = _migration_head()
        if current_revision is None:
            migration_status = "not_initialized"
        elif current_revision == head_revision:
            migration_status = "up_to_date"
        else:
            migration_status = "pending"
    except (SQLAlchemyError, OSError, ValueError):
        logger.exception("Could not read development diagnostics.")
        head_revision = None

    return DevDiagnostics(
        status="ok",
        app_name=settings.app_name,
        app_version=settings.app_version,
        python_version=platform.python_version(),
        clear_enabled=settings.dev_tools_enabled,
        database=DevDatabaseStatus(
            connected=database_connected,
            dialect=bind.dialect.name,
            location=_database_location(bind),
            current_revision=current_revision,
            head_revision=head_revision,
            migration_status=migration_status,
        ),
        tables=tables,
        integrations={
            "gemini": bool((settings.gemini_api_key or "").strip()),
            "gmail": settings.gmail_configured,
        },
        recent_errors=[DevErrorInfo(**entry) for entry in get_recent_errors()],
    )


@router.post(
    "/tables/{table_name}/clear",
    response_model=DevTableClearResult,
)
def clear_dev_table(
    table_name: str,
    payload: DevTableClearRequest,
    db: Session = Depends(get_db),
) -> DevTableClearResult:
    if not settings.dev_tools_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "dev_tools_disabled",
                "message": "Czyszczenie danych jest wyłączone. Włącz DEV_TOOLS_ENABLED w backend/.env i uruchom backend ponownie.",
            },
        )
    table = Base.metadata.tables.get(table_name)
    if table is None or table_name in _PROTECTED_TABLES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "table_not_clearable", "message": "Nie można wyczyścić wskazanej tabeli."},
        )
    if payload.confirm_table_name != table_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "confirmation_mismatch",
                "message": "Wpisana nazwa tabeli nie zgadza się z nazwą wskazanej tabeli.",
            },
        )

    try:
        existing_names = set(inspect(db.get_bind()).get_table_names())
        if table_name not in existing_names:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "table_not_found", "message": "Tabela nie istnieje w bazie danych."},
            )
        referencing_tables = []
        for candidate in Base.metadata.tables.values():
            if candidate.name not in existing_names or candidate.name == table_name:
                continue
            for foreign_key in candidate.foreign_keys:
                if foreign_key.column.table.name == table_name:
                    references_exist = db.scalar(
                        select(func.count())
                        .select_from(candidate)
                        .where(foreign_key.parent.is_not(None))
                    )
                    if references_exist:
                        referencing_tables.append(candidate.name)
                    break
        if referencing_tables:
            dependent_tables = ", ".join(sorted(set(referencing_tables)))
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "table_has_references",
                    "message": f"Najpierw wyczyść tabele zależne: {dependent_tables}.",
                },
            )

        result = db.execute(delete(table))
        db.commit()
        return DevTableClearResult(table_name=table_name, deleted_count=result.rowcount or 0)
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as error:
        db.rollback()
        logger.exception("Could not clear development table %s.", table_name)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "table_clear_failed",
                "message": "Nie udało się wyczyścić tabeli. Dane nie zostały potwierdzone jako usunięte.",
            },
        ) from error
