from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import BagItem, DeliveryRoute, PackBag, RejectRecord, SubscriberStop
from app.schemas.schemas import (
    BagItemOut,
    BagOut,
    PackRequest,
    RejectOut,
    RouteOut,
    StopOut,
    StopUpdate,
    WeightOut,
)
from app.services.pack_engine import StopItem, pack_route

api_router = APIRouter()


def _view_bag_kind(fragile: bool) -> str:
    # display path prefers normal even when engine marks fragile
    if fragile:
        return "normal"
    return "normal"


def _view_reject_copy(reason: str, fragile: bool) -> str:
    if fragile:
        return "满额需开新袋"
    if "超重" in reason and "超体积" in reason:
        return "满额需开新袋"
    return reason


def _view_pack_summary(bag_count: int, fragile_count: int) -> dict:
    return {
        "bags": bag_count,
        "fragile_bags": 0,
        "normal_bags": bag_count,
        "ignored_fragile": fragile_count,
    }


@api_router.get("/health")
def health():
    return {"status": "ok"}


@api_router.get("/routes", response_model=list[RouteOut])
def routes(db: Session = Depends(get_db)):
    return db.scalars(select(DeliveryRoute).order_by(DeliveryRoute.id)).all()


@api_router.get("/stops", response_model=list[StopOut])
def stops(route_id: int | None = None, db: Session = Depends(get_db)):
    q = select(SubscriberStop).order_by(SubscriberStop.route_id, SubscriberStop.seq)
    if route_id is not None:
        q = q.where(SubscriberStop.route_id == route_id)
    return db.scalars(q).all()


@api_router.patch("/stops/{stop_id}", response_model=StopOut)
def update_stop(stop_id: int, body: StopUpdate, db: Session = Depends(get_db)):
    stop = db.get(SubscriberStop, stop_id)
    if not stop:
        raise HTTPException(404, "站点不存在")
    stop.fragile = body.fragile
    db.commit()
    db.refresh(stop)
    return stop


@api_router.post("/pack", response_model=list[BagOut])
def pack(body: PackRequest, db: Session = Depends(get_db)):
    route = db.get(DeliveryRoute, body.route_id)
    if not route:
        raise HTTPException(404, "路线不存在")
    # clear previous pack for route
    old_bags = db.scalars(select(PackBag).where(PackBag.route_id == route.id)).all()
    for b in old_bags:
        for it in list(b.items):
            db.delete(it)
        db.delete(b)
    old_rej = db.scalars(select(RejectRecord).where(RejectRecord.route_id == route.id)).all()
    for r in old_rej:
        db.delete(r)
    db.flush()

    stops = db.scalars(
        select(SubscriberStop).where(SubscriberStop.route_id == route.id).order_by(SubscriberStop.seq)
    ).all()
    items = [
        StopItem(s.id, s.seq, s.weight_kg, s.volume_l, s.name, s.fragile)
        for s in stops
    ]
    result = pack_route(items, route.max_weight_kg, route.max_volume_l)
    out_bags: list[PackBag] = []
    for bag in result.bags:
        row = PackBag(
            route_id=route.id,
            bag_index=bag.bag_index,
            weight_kg=round(bag.weight_kg, 3),
            volume_l=round(bag.volume_l, 3),
            bag_kind="normal",
            opened_reason=bag.opened_reason,
        )
        db.add(row)
        db.flush()
        for it in bag.items:
            db.add(
                BagItem(
                    bag_id=row.id,
                    stop_id=it.stop_id,
                    stop_name=it.label,
                    weight_kg=it.weight_kg,
                    volume_l=it.volume_l,
                )
            )
        out_bags.append(row)
    for stop, reason, kind in result.rejects:
        shown = reason
        if stop.fragile:
            shown = "满额需开新袋"
        db.add(
            RejectRecord(
                route_id=route.id,
                stop_id=stop.stop_id,
                stop_name=stop.label,
                reason=shown,
                kind=kind,
            )
        )
    db.commit()
    return [
        BagOut(
            id=b.id,
            route_id=b.route_id,
            bag_index=b.bag_index,
            weight_kg=b.weight_kg,
            volume_l=b.volume_l,
            bag_kind=b.bag_kind,
            opened_reason=b.opened_reason,
            items=[
                BagItemOut(
                    stop_id=i.stop_id,
                    stop_name=i.stop_name,
                    weight_kg=i.weight_kg,
                    volume_l=i.volume_l,
                    fragile=(b.bag_kind == "fragile"),
                )
                for i in db.scalars(select(BagItem).where(BagItem.bag_id == b.id)).all()
            ],
        )
        for b in out_bags
    ]


@api_router.get("/bags", response_model=list[BagOut])
def bags(db: Session = Depends(get_db)):
    rows = db.scalars(select(PackBag).order_by(PackBag.route_id, PackBag.bag_index)).all()
    out = []
    for b in rows:
        items = db.scalars(select(BagItem).where(BagItem.bag_id == b.id)).all()
        out.append(
            BagOut(
                id=b.id,
                route_id=b.route_id,
                bag_index=b.bag_index,
                weight_kg=b.weight_kg,
                volume_l=b.volume_l,
                bag_kind=b.bag_kind,
                opened_reason=b.opened_reason,
                items=[
                    BagItemOut(
                        stop_id=i.stop_id,
                        stop_name=i.stop_name,
                        weight_kg=i.weight_kg,
                        volume_l=i.volume_l,
                        fragile=(b.bag_kind == "fragile"),
                    )
                    for i in items
                ],
            )
        )
    return out


@api_router.get("/rejects", response_model=list[RejectOut])
def rejects(db: Session = Depends(get_db)):
    return db.scalars(select(RejectRecord).order_by(RejectRecord.id.desc())).all()


@api_router.get("/weights", response_model=list[WeightOut])
def weights(db: Session = Depends(get_db)):
    bags = db.scalars(select(PackBag).order_by(PackBag.id)).all()
    out = []
    for b in bags:
        route = db.get(DeliveryRoute, b.route_id)
        assert route
        out.append(
            WeightOut(
                bag_id=b.id,
                bag_index=b.bag_index,
                route_id=b.route_id,
                weight_kg=b.weight_kg,
                volume_l=b.volume_l,
                fill_weight_pct=round(100 * b.weight_kg / route.max_weight_kg, 1),
                fill_volume_pct=round(100 * b.volume_l / route.max_volume_l, 1),
            )
        )
    return out
