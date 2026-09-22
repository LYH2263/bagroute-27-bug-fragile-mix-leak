from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DeliveryRoute(Base):
    __tablename__ = "delivery_routes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    max_weight_kg: Mapped[float] = mapped_column(Float, default=8.0)
    max_volume_l: Mapped[float] = mapped_column(Float, default=20.0)
    stops: Mapped[list["SubscriberStop"]] = relationship(back_populates="route")


class SubscriberStop(Base):
    __tablename__ = "subscriber_stops"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("delivery_routes.id"))
    seq: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(80))
    weight_kg: Mapped[float] = mapped_column(Float)
    volume_l: Mapped[float] = mapped_column(Float)
    fragile: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    route: Mapped[DeliveryRoute] = relationship(back_populates="stops")


class PackBag(Base):
    __tablename__ = "pack_bags"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("delivery_routes.id"))
    bag_index: Mapped[int] = mapped_column(Integer)
    weight_kg: Mapped[float] = mapped_column(Float)
    volume_l: Mapped[float] = mapped_column(Float)
    # "fragile" 表示本袋只装易碎站点，"normal" 只装非易碎站点
    bag_kind: Mapped[str] = mapped_column(String(16), default="normal", server_default="normal")
    # 首袋 first / 满额开新袋 capacity / 易碎隔离 isolation
    opened_reason: Mapped[str] = mapped_column(String(16), default="first", server_default="first")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    items: Mapped[list["BagItem"]] = relationship(back_populates="bag")


class BagItem(Base):
    __tablename__ = "bag_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bag_id: Mapped[int] = mapped_column(ForeignKey("pack_bags.id"))
    stop_id: Mapped[int] = mapped_column(ForeignKey("subscriber_stops.id"))
    stop_name: Mapped[str] = mapped_column(String(80))
    weight_kg: Mapped[float] = mapped_column(Float)
    volume_l: Mapped[float] = mapped_column(Float)
    bag: Mapped[PackBag] = relationship(back_populates="items")


class RejectRecord(Base):
    __tablename__ = "reject_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("delivery_routes.id"))
    stop_id: Mapped[int] = mapped_column(Integer)
    stop_name: Mapped[str] = mapped_column(String(80))
    reason: Mapped[str] = mapped_column(String(200))
    # oversize = 单站自身超过路线限额（现网拒收）
    kind: Mapped[str] = mapped_column(String(16), default="oversize", server_default="oversize")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
