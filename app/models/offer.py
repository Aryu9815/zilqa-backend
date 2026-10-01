from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID
from sqlalchemy import String, Boolean, DateTime, Numeric, Text, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    offer_type: Mapped[str] = mapped_column(String(50), nullable=False)
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)
    discount_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    coupon_code: Mapped[Optional[str]] = mapped_column(String(50), unique=True)

    minimum_order_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default="0")
    maximum_discount_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))

    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)

    usage_limit: Mapped[Optional[int]] = mapped_column(Integer)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default="false")

    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), server_default=func.current_timestamp())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    offer_products: Mapped[List["OfferProduct"]] = relationship("OfferProduct", back_populates="offer", cascade="all, delete-orphan")


class OfferProduct(Base):
    __tablename__ = "offer_products"

    offer_id: Mapped[UUID] = mapped_column(ForeignKey("offers.id", ondelete="CASCADE"), primary_key=True)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)

    offer: Mapped["Offer"] = relationship("Offer", back_populates="offer_products")
    product: Mapped["Product"] = relationship("Product")
