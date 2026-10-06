from datetime import datetime
from typing import Optional, List
from uuid import UUID
from sqlalchemy import String, Boolean, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password_hash: Mapped[Optional[str]] = mapped_column(Text)
    mobile_number: Mapped[Optional[str]] = mapped_column(String)
    google_id: Mapped[Optional[str]] = mapped_column(String)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_email_verified: Mapped[Optional[bool]] = mapped_column(Boolean, server_default="false")

    otp: Mapped[Optional[str]] = mapped_column(String)
    otp_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    country_code: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    @property
    def role(self) -> str:
        return "customer"

    def __getitem__(self, item: str):
        if item == "role":
            return "customer"
        return getattr(self, item)

    def get(self, item: str, default=None):
        if item == "role":
            return "customer"
        return getattr(self, item, default)

    def keys(self):
        cols = [c.name for c in self.__table__.columns]
        if "role" not in cols:
            cols.append("role")
        return cols

    def items(self):
        return [(k, getattr(self, k, None) if k != "role" else "customer") for k in self.keys()]

    addresses: Mapped[List["UserAddress"]] = relationship("UserAddress", back_populates="user")
    carts: Mapped[List["Cart"]] = relationship("Cart", back_populates="user")
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="user")
    wishlist_items: Mapped[List["WishlistItem"]] = relationship("WishlistItem", back_populates="user")
    reviews: Mapped[List["Review"]] = relationship("Review", back_populates="user")
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship("RefreshToken", back_populates="user")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.current_timestamp())

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")
