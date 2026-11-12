from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Vehicle
from app.schemas import VehicleMatchInput, VehicleMatchResponse, VehicleRead
from app.services.vehicle_matching import match_vehicle

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("", response_model=list[VehicleRead])
def list_vehicles(db: Session = Depends(get_db)) -> list[Vehicle]:
    return list(db.scalars(select(Vehicle).order_by(Vehicle.id)).all())


@router.post("/match", response_model=VehicleMatchResponse)
def preview_vehicle_match(
    payload: VehicleMatchInput,
    db: Session = Depends(get_db),
) -> VehicleMatchResponse:
    vehicles = list(db.scalars(select(Vehicle).order_by(Vehicle.id)).all())
    result = match_vehicle(
        length_cm=payload.length_cm,
        width_cm=payload.width_cm,
        height_cm=payload.height_cm,
        weight_kg=payload.weight_kg,
        quantity=payload.quantity,
        vehicles=vehicles,
    )
    return VehicleMatchResponse.model_validate(result)
