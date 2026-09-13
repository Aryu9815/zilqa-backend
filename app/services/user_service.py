from typing import List, Optional
from uuid import UUID

from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.core.security import hash_password, verify_password
from app.repositories.address_repository import address_repository
from app.repositories.user_repository import user_repository
from app.schemas.address import AddressCreate, AddressResponse, AddressUpdate
from app.schemas.user import UserResponse, UserUpdate


class UserService:

    async def get_profile(self, user_id: UUID) -> UserResponse:
        record = await user_repository.get_by_id(user_id)
        if not record:
            raise NotFoundException(message="User not found", error_code="USER_NOT_FOUND")
        return UserResponse.model_validate(dict(record))

    async def update_profile(self, user_id: UUID, user_update: UserUpdate) -> UserResponse:
        current_user = await user_repository.get_by_id(user_id)
        if not current_user:
            raise NotFoundException(message="User not found", error_code="USER_NOT_FOUND")

        new_password_hash = None
        if user_update.new_password:
            if not user_update.current_password:
                raise BadRequestException(
                    message="Current password is required to set a new password",
                    error_code="CURRENT_PASSWORD_REQUIRED"
                )
            if not current_user.get("password_hash") or not verify_password(user_update.current_password, current_user["password_hash"]):
                raise BadRequestException(
                    message="Current password is incorrect",
                    error_code="INVALID_CURRENT_PASSWORD"
                )
            new_password_hash = hash_password(user_update.new_password)

        if user_update.email and user_update.email.lower() != current_user["email"].lower():
            existing = await user_repository.get_by_email(user_update.email)
            if existing:
                raise ConflictException(
                    message="An account with this email address already exists",
                    error_code="EMAIL_ALREADY_EXISTS"
                )

        updated_record = await user_repository.update(
            user_id=user_id,
            name=user_update.name,
            email=user_update.email,
            password_hash=new_password_hash
        )
        assert updated_record is not None
        return UserResponse.model_validate(dict(updated_record))

    # ----------------- Address Operations -----------------

    async def list_addresses(self, user_id: UUID) -> List[AddressResponse]:
        records = await address_repository.list_by_user(user_id)
        return [AddressResponse.model_validate(dict(r)) for r in records]

    async def get_address(self, address_id: UUID, user_id: UUID) -> AddressResponse:
        record = await address_repository.get_by_id_and_user(address_id, user_id)
        if not record:
            raise NotFoundException(message="Address not found", error_code="ADDRESS_NOT_FOUND")
        return AddressResponse.model_validate(dict(record))

    async def create_address(self, user_id: UUID, address_in: AddressCreate) -> AddressResponse:
        # If this is the user's first address, automatically make it default
        count = await address_repository.count_by_user(user_id)
        if count == 0:
            address_in.is_default = True

        record = await address_repository.create(user_id, address_in)
        return AddressResponse.model_validate(dict(record))

    async def update_address(
        self,
        address_id: UUID,
        user_id: UUID,
        address_in: AddressUpdate
    ) -> AddressResponse:
        existing = await address_repository.get_by_id_and_user(address_id, user_id)
        if not existing:
            raise NotFoundException(message="Address not found", error_code="ADDRESS_NOT_FOUND")

        record = await address_repository.update(address_id, user_id, address_in)
        assert record is not None
        return AddressResponse.model_validate(dict(record))

    async def delete_address(self, address_id: UUID, user_id: UUID) -> None:
        deleted = await address_repository.delete(address_id, user_id)
        if not deleted:
            raise NotFoundException(message="Address not found", error_code="ADDRESS_NOT_FOUND")

    async def set_default_address(self, address_id: UUID, user_id: UUID) -> AddressResponse:
        record = await address_repository.set_default(address_id, user_id)
        if not record:
            raise NotFoundException(message="Address not found", error_code="ADDRESS_NOT_FOUND")
        return AddressResponse.model_validate(dict(record))


user_service = UserService()
