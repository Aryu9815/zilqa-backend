import boto3

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException, UploadFile

from app.core.config import settings


R2_ACCOUNT_ID = settings.R2_ACCOUNT_ID
R2_ACCESS_KEY_ID = settings.R2_ACCESS_KEY_ID
R2_SECRET_ACCESS_KEY = settings.R2_SECRET_ACCESS_KEY
R2_BUCKET_NAME = settings.R2_BUCKET_NAME
R2_PUBLIC_URL = settings.R2_PUBLIC_URL


r2_client = boto3.client(
    "s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    region_name="auto",
)


ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


async def upload_to_r2(
    file: UploadFile,
    image_name: str,
) -> dict:
    print("uploading started")
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG and WebP images are allowed.",
        )

    extension = ALLOWED_CONTENT_TYPES[file.content_type]

    # Remove extension supplied by frontend
    clean_name = image_name.rsplit(".", 1)[0]

    # Create filename
    filename = f"{clean_name}{extension}"

    # R2 object key
    key = f"products/{filename}"

    try:
        content = await file.read()

        r2_client.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=key,
            Body=content,
            ContentType=file.content_type,
        )

    except (BotoCoreError, ClientError) as e:
        print("uploading error", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload image: {str(e)}",
        )

    # Path stored in PostgreSQL
    db_path = f"/{key}"

    # Public URL
    public_url = f"{R2_PUBLIC_URL.rstrip('/')}/{key}"

    return {
        "key": key,
        "path": db_path,
        "url": public_url,
        "filename": filename,
        "content_type": file.content_type,
    }


def delete_from_r2(image_path: str):

    # /products/usa-ring.webp
    # ↓
    # products/usa-ring.webp

    key = image_path.lstrip("/")

    try:
        r2_client.delete_object(
            Bucket=R2_BUCKET_NAME,
            Key=key,
        )

    except (BotoCoreError, ClientError) as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete image: {str(e)}",
        )