from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Text,
    Numeric,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Product(Base):
    __tablename__ = "products"
    id: Mapped[UUID] = mapped_column(primary_key=True,server_default=func.gen_random_uuid())
    name: Mapped[str] = mapped_column(String,nullable=False)
    main_image_url: Mapped[Optional[str]] = mapped_column(Text,nullable=True)
    price: Mapped[float] = mapped_column(Numeric,nullable=False)
    category_ids: Mapped[List[UUID]] = mapped_column(ARRAY(PGUUID(as_uuid=True)),nullable=False,server_default="{}")
    other_image_urls: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text),nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    product_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    related_product_ids: Mapped[List[UUID]] = mapped_column(ARRAY(PGUUID(as_uuid=True)),nullable=False,server_default="{}",)
    faqs: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, nullable=False, server_default="'[]'::jsonb")
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    seo_title: Mapped[str] = mapped_column(String(255), nullable=False)
    seo_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    og_title: Mapped[str] = mapped_column(String(255), nullable=False)
    og_description: Mapped[str] = mapped_column(Text, nullable=False)
    og_image: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False,server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


    cart_items: Mapped[List["CartItem"]] = relationship(
        "CartItem",
        back_populates="product",
    )
    order_items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="product",
    )
    reviews: Mapped[List["Review"]] = relationship(
        "Review",
        back_populates="product",
    )
    wishlist_items: Mapped[List["WishlistItem"]] = relationship(
        "WishlistItem",
        back_populates="product",
    )

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)

    def keys(self) -> List[str]:
        return [c.name for c in self.__table__.columns]