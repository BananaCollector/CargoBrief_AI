import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.ai import _check_rate_limit
from app.config import settings
from app.database import get_db
from app.models import (
    ShipmentNotification,
    ShipmentOrder,
    TransportOrder,
    TransportShipment,
    Vehicle,
)
from app.schemas import (
    ShipmentCreate,
    ShipmentRead,
    ShipmentSuggestionGroup,
    ShipmentSuggestInput,
    ShipmentSuggestionsResponse,
    TransportOrderRead,
    VehicleRead,
)
from app.services.ai_analyzer import (
    AIInvalidResponseError,
    AIProviderError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
    suggest_shipment_groups,
)
from app.services.email_service import validate_email_address
from app.services.shipment_planning import evaluate_shipment

router = APIRouter(prefix="/shipments", tags=["shipments"])
logger = logging.getLogger(__name__)


def _get_available_orders(db: Session, order_ids: list[int]) -> list[TransportOrder]:
    orders = list(
        db.scalars(
            select(TransportOrder)
            .where(TransportOrder.id.in_(order_ids))
            .order_by(TransportOrder.id)
        ).all()
    )
    if len(orders) != len(order_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "order_not_found", "message": "Nie znaleziono części zleceń."},
        )

    non_approved = [order.id for order in orders if order.status != "approved"]
    if non_approved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "order_not_approved",
                "message": "Do wysyłki można przypisać tylko zatwierdzone zlecenia.",
            },
        )

    assigned_orders = set(
        db.scalars(
            select(ShipmentOrder.order_id).where(ShipmentOrder.order_id.in_(order_ids))
        ).all()
    )
    if assigned_orders:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "order_already_assigned",
                "message": "Co najmniej jedno zlecenie jest już przypisane do wysyłki.",
            },
        )
    return orders


def _get_vehicles(db: Session) -> list[Vehicle]:
    return list(db.scalars(select(Vehicle).order_by(Vehicle.id)).all())


def _build_shipment_read(
    db: Session,
    shipment: TransportShipment,
) -> ShipmentRead:
    orders = list(
        db.scalars(
            select(TransportOrder)
            .join(ShipmentOrder, ShipmentOrder.order_id == TransportOrder.id)
            .where(ShipmentOrder.shipment_id == shipment.id)
            .order_by(TransportOrder.id)
        ).all()
    )
    vehicle = db.get(Vehicle, shipment.vehicle_id)
    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "shipment_vehicle_missing", "message": "Pojazd wysyłki już nie istnieje."},
        )
    evaluation = evaluate_shipment(
        orders,
        [vehicle],
        shipment.scheduled_date,
        vehicle_id=vehicle.id,
        confirm_date_override=True,
    )
    if not evaluation.eligible or evaluation.total_weight_kg is None or evaluation.total_volume_cm3 is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "shipment_invalid",
                "message": "Dane przypisanych zleceń nie spełniają już ograniczeń wysyłki.",
            },
        )
    notification_statuses = list(
        db.scalars(
            select(ShipmentNotification.status).where(
                ShipmentNotification.shipment_id == shipment.id
            )
        ).all()
    )
    if "not_configured" in notification_statuses:
        notification_status = "not_configured"
    elif "failed" in notification_statuses:
        notification_status = "failed"
    elif "pending" in notification_statuses:
        notification_status = "pending"
    elif "sending" in notification_statuses:
        notification_status = "sending"
    elif notification_statuses and all(item == "sent" for item in notification_statuses):
        notification_status = "sent"
    else:
        notification_status = "not_configured"

    return ShipmentRead(
        id=shipment.id,
        scheduled_date=shipment.scheduled_date,
        destination=shipment.destination,
        vehicle=VehicleRead.model_validate(vehicle),
        orders=[TransportOrderRead.model_validate(order) for order in orders],
        total_weight_kg=evaluation.total_weight_kg,
        total_volume_cm3=evaluation.total_volume_cm3,
        warnings=list(evaluation.warnings),
        notification_status=notification_status,
        created_at=shipment.created_at,
    )


@router.get("", response_model=list[ShipmentRead])
def list_shipments(db: Session = Depends(get_db)) -> list[ShipmentRead]:
    shipments = db.scalars(
        select(TransportShipment)
        .order_by(TransportShipment.scheduled_date, TransportShipment.id)
        .limit(50)
    ).all()
    return [_build_shipment_read(db, shipment) for shipment in shipments]


@router.get("/available-orders", response_model=list[TransportOrderRead])
def list_available_orders(db: Session = Depends(get_db)) -> list[TransportOrderRead]:
    assigned_order_ids = select(ShipmentOrder.order_id)
    orders = db.scalars(
        select(TransportOrder)
        .where(
            TransportOrder.status == "approved",
            TransportOrder.id.not_in(assigned_order_ids),
        )
        .order_by(TransportOrder.created_at.desc(), TransportOrder.id.desc())
    ).all()
    return [TransportOrderRead.model_validate(order) for order in orders]


@router.post("/suggest", response_model=ShipmentSuggestionsResponse)
def create_shipment_suggestions(
    payload: ShipmentSuggestInput,
    request: Request,
    db: Session = Depends(get_db),
) -> ShipmentSuggestionsResponse:
    if (settings.gemini_api_key or "").strip():
        _check_rate_limit(request)
    orders = _get_available_orders(db, payload.order_ids)
    try:
        groups, mode = suggest_shipment_groups(orders, payload.scheduled_date)
    except AIProviderTimeoutError as error:
        logger.warning("Gemini shipment suggestion timed out")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"code": "ai_timeout", "message": "Propozycje AI nie odpowiedziały na czas."},
        ) from error
    except AIInvalidResponseError as error:
        logger.warning("Gemini returned invalid shipment suggestions")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "ai_invalid_response", "message": "Nie udało się zweryfikować propozycji AI."},
        ) from error
    except AIProviderUnavailableError as error:
        logger.warning("Gemini shipment suggestion service is unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "ai_unavailable", "message": "Usługa AI jest chwilowo niedostępna."},
        ) from error
    except AIProviderError as error:
        logger.warning("Gemini shipment suggestion failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "ai_provider_error", "message": "Nie udało się przygotować propozycji AI."},
        ) from error

    orders_by_id = {order.id: order for order in orders}
    vehicles = _get_vehicles(db)
    suggestions: list[ShipmentSuggestionGroup] = []
    for group in groups:
        group_orders = [orders_by_id[order_id] for order_id in group.order_ids]
        evaluation = evaluate_shipment(
            group_orders,
            vehicles,
            payload.scheduled_date,
            confirm_date_override=True,
        )
        suggestions.append(
            ShipmentSuggestionGroup(
                order_ids=group.order_ids,
                destination=evaluation.destination,
                eligible=evaluation.eligible,
                recommended_vehicle=(
                    VehicleRead.model_validate(evaluation.recommended_vehicle)
                    if evaluation.recommended_vehicle
                    else None
                ),
                total_weight_kg=evaluation.total_weight_kg,
                total_volume_cm3=evaluation.total_volume_cm3,
                date_conflicts=list(evaluation.date_conflicts),
                warnings=list(evaluation.warnings),
                message=f"{group.reason} {evaluation.message}",
            )
        )
    return ShipmentSuggestionsResponse(mode=mode, groups=suggestions)


@router.post("", response_model=ShipmentRead, status_code=status.HTTP_201_CREATED)
def create_shipment(
    payload: ShipmentCreate,
    db: Session = Depends(get_db),
) -> ShipmentRead:
    orders = _get_available_orders(db, payload.order_ids)
    customer_emails: dict[int, str] = {}
    for order in orders:
        valid_email = validate_email_address(order.customer_email)
        if valid_email is not None:
            customer_emails[order.id] = valid_email
    missing_email_order_ids = [
        order.id for order in orders if order.id not in customer_emails
    ]
    if missing_email_order_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "customer_email_required",
                "message": "Uzupełnij adres e-mail w zleceniach: "
                + ", ".join(f"#{order_id}" for order_id in missing_email_order_ids)
                + ".",
            },
        )
    vehicle = db.get(Vehicle, payload.vehicle_id)
    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "vehicle_not_found", "message": "Nie znaleziono pojazdu."},
        )
    evaluation = evaluate_shipment(
        orders,
        [vehicle],
        payload.scheduled_date,
        vehicle_id=vehicle.id,
        confirm_date_override=payload.confirm_date_override,
    )
    if not evaluation.eligible:
        error_code = "shipment_date_conflict" if evaluation.date_conflicts else "shipment_not_eligible"
        error_status = (
            status.HTTP_409_CONFLICT
            if evaluation.date_conflicts and not payload.confirm_date_override
            else status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        raise HTTPException(
            status_code=error_status,
            detail={"code": error_code, "message": evaluation.message},
        )

    shipment = TransportShipment(
        scheduled_date=payload.scheduled_date,
        destination=evaluation.destination,
        vehicle_id=vehicle.id,
    )
    db.add(shipment)
    try:
        db.flush()
        db.add_all(
            ShipmentOrder(shipment_id=shipment.id, order_id=order.id)
            for order in orders
        )
        db.add_all(
            ShipmentNotification(
                shipment_id=shipment.id,
                order_id=order.id,
                recipient_email=customer_emails[order.id],
                status="pending" if settings.gmail_configured else "not_configured",
            )
            for order in orders
        )
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "order_already_assigned",
                "message": "Co najmniej jedno zlecenie zostało już przypisane do wysyłki.",
            },
        ) from error
    db.refresh(shipment)
    return _build_shipment_read(db, shipment)


@router.delete("/{shipment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shipment(shipment_id: int, db: Session = Depends(get_db)) -> None:
    shipment = db.get(TransportShipment, shipment_id)
    if shipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "shipment_not_found", "message": "Nie znaleziono wysyłki."},
        )
    associations = db.scalars(
        select(ShipmentOrder).where(ShipmentOrder.shipment_id == shipment_id)
    ).all()
    for association in associations:
        db.delete(association)
    notifications = db.scalars(
        select(ShipmentNotification).where(
            ShipmentNotification.shipment_id == shipment_id
        )
    ).all()
    for notification in notifications:
        db.delete(notification)
    db.delete(shipment)
    db.commit()
