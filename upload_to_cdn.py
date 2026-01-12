import boto3
from botocore.config import Config
import os

filename = "research_presentation_20260112.pptx"
local_path = f"/Users/saurabhbidwai/Documents/cc-hitl-template/{filename}"

# S3 client for DO Spaces
s3 = boto3.client('s3',
    endpoint_url="https://fra1.digitaloceanspaces.com",
    region_name="fra1",
    aws_access_key_id=os.getenv("DO_SPACES_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("DO_SPACES_SECRET_KEY"),
    config=Config(signature_version='s3v4'))

# Upload with public-read ACL
s3.upload_file(
    local_path,
    'studios-general-bucket',
    f'research-presentations/{filename}',
    ExtraArgs={
        'ACL': 'public-read',
        'ContentType': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    }
)

# Construct CDN URL
cdn_url = f"https://studios-general-bucket.fra1.digitaloceanspaces.com/research-presentations/{filename}"
print(cdn_url)
