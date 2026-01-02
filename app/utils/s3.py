import boto3
import uuid
from app.config import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_REGION,
    AWS_BUCKET_NAME
)

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

def upload_file_to_s3(file_obj, filename: str, folder: str = "uploads"):
    """
    Upload any file type to AWS S3 and return public URL
    """
    unique_name = f"{folder}/{uuid.uuid4()}_{filename}"

    s3_client.upload_fileobj(
        file_obj,
        AWS_BUCKET_NAME,
        unique_name,
        ExtraArgs={"ACL": "public-read"}
    )

    return f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{unique_name}"
