from datetime import datetime, timezone
from uuid import uuid4
import pytest
from pydantic import ValidationError

from app.schemas.address import AddressCreate, AddressResponse, AddressUpdate


def test_address_create_validation():
    addr = AddressCreate(
        full_name="John Doe",
        phone="+919876543210",
        address_line_1="123 Main Street",
        address_line_2="Flat 4B",
        city="Mumbai",
        state="Maharashtra",
        postal_code="400001",
        country="India",
        is_default=True
    )
    assert addr.city == "Mumbai"
    assert addr.is_default is True


def test_address_short_phone_rejected():
    with pytest.raises(ValidationError):
        AddressCreate(
            full_name="John Doe",
            phone="123",  # Too short
            address_line_1="123 Main Street",
            city="Mumbai",
            state="Maharashtra",
            postal_code="400001"
        )
