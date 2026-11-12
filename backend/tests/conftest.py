import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Vehicle


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
        db.add_all(
            [
                Vehicle(
                    name="Van S",
                    max_length_cm=180,
                    max_width_cm=115,
                    max_height_cm=115,
                    max_payload_kg=600,
                ),
                Vehicle(
                    name="Van L2H2",
                    max_length_cm=340,
                    max_width_cm=170,
                    max_height_cm=190,
                    max_payload_kg=1000,
                ),
                Vehicle(
                    name="Van XL",
                    max_length_cm=420,
                    max_width_cm=175,
                    max_height_cm=210,
                    max_payload_kg=1400,
                ),
            ]
        )
        db.commit()

    def override_get_db():
        with TestingSessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
