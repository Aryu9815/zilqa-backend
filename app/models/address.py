from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy import String, Boolean, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.user import User

class UserAddress(Base):
    __tablename__ = "user_addresses"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    address_line_1: Mapped[str] = mapped_column(Text, nullable=False)
    address_line_2: Mapped[Optional[str]] = mapped_column(Text)
    city: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False)
    postal_code: Mapped[str] = mapped_column(String, nullable=False)
    country: Mapped[str] = mapped_column(String, nullable=False, server_default="India")
    
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    user: Mapped["User"] = relationship("User", back_populates="addresses")
