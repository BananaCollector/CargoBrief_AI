from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TransportOrder, Vehicle
from app.schemas import (
    TransportOrderCreate,
    TransportOrderDetail,
    TransportOrderRead,
    TransportOrderUpdate,
    VehicleMatchResponse,
)
from app.services.vehicle_matching import match_vehicle

router = APIRouter(prefix="/orders", tags=["orders"])


def build_order_detail(
    order: TransportOrder,
    vehicles: list[Vehicle],
) -> TransportOrderDetail:
    match = match_vehicle(
        length_cm=order.length_cm,
        width_cm=order.width_cm,
        height_cm=order.height_cm,
        weight_kg=order.weight_kg,
        quantity=order.quantity,
        vehicles=vehicles,
    )
    order_data = TransportOrderRead.model_validate(order).model_dump()
    return TransportOrderDetail(
        **order_data,
        match=VehicleMatchResponse.model_validate(match),
    )


def get_vehicles(db: Session) -> list[Vehicle]:
    return list(db.scalars(select(Vehicle).order_by(Vehicle.id)).all())


@router.post("", response_model=TransportOrderDetail, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: TransportOrderCreate,
    db: Session = Depends(get_db),
) -> TransportOrderDetail:
    order = TransportOrder(**payload.model_dump())
    db.add(order)
    db.commit()
    db.refresh(order)
    return build_order_detail(order, get_vehicles(db))


@router.get("", response_model=list[TransportOrderDetail])
def list_orders(db: Session = Depends(get_db)) -> list[TransportOrderDetail]:
    orders = db.scalars(
        select(TransportOrder)
        .order_by(TransportOrder.created_at.desc(), TransportOrder.id.desc())
        .limit(50)
    ).all()
    vehicles = get_vehicles(db)
    return [build_order_detail(order, vehicles) for order in orders]


@router.get("/{order_id}", response_model=TransportOrderDetail)
def read_order(
    order_id: int,
    db: Session = Depends(get_db),
) -> TransportOrderDetail:
    order = db.get(TransportOrder, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "order_not_found", "message": "Nie znaleziono zlecenia."},
        )
    return build_order_detail(order, get_vehicles(db))


@router.put("/{order_id}", response_model=TransportOrderDetail)
def update_order(
    order_id: int,
    payload: TransportOrderUpdate,
    db: Session = Depends(get_db),
) -> TransportOrderDetail:
    order = db.get(TransportOrder, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "order_not_found", "message": "Nie znaleziono zlecenia."},
        )

    for field, value in payload.model_dump(exclude={"status"}).items():
        setattr(order, field, value)
    if payload.status is not None:
        order.status = payload.status
    order.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(order)
    return build_order_detail(order, get_vehicles(db))


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, db: Session = Depends(get_db)) -> Response:
    order = db.get(TransportOrder, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "order_not_found", "message": "Nie znaleziono zlecenia."},
        )

    db.delete(order)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
