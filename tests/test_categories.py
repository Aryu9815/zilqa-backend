import pytest
from pydantic import ValidationError

from app.schemas.category import CategoryCreate, CategoryUpdate


def test_category_create_validation():
    cat = CategoryCreate(
        name="Rings",
        description="Silver and Gold Rings",
        image_url="https://example.com/rings.jpg"
    )
    assert cat.name == "Rings"
    assert cat.description == "Silver and Gold Rings"


def test_category_empty_name_rejected():
    with pytest.raises(ValidationError):
        CategoryCreate(name="")
