"""
Accès au stockage privé. Les fichiers sensibles ne sont jamais exposés par une URL stable :
on génère une URL signée de courte durée, à la demande, après contrôle des permissions.
"""

from __future__ import annotations

import uuid
from pathlib import PurePosixPath

from django.conf import settings
from django.core.files.storage import Storage, storages


def private_storage() -> Storage:
    return storages["private"]


def public_storage() -> Storage:
    return storages["default"]


def generated_name(prefix: str, original_name: str, forced_ext: str | None = None) -> str:
    """Nom de fichier généré : jamais celui envoyé par l'utilisateur."""
    ext = forced_ext or PurePosixPath(original_name).suffix.lower().lstrip(".") or "bin"
    return f"{prefix}/{uuid.uuid4().hex}.{ext}"


def signed_private_url(name: str, expires: int | None = None) -> str:
    """URL signée vers le bucket privé, joignable depuis le navigateur."""
    storage = private_storage()
    ttl = expires or settings.S3_PRIVATE_URL_EXPIRY_SECONDS
    if not hasattr(storage, "connection"):
        # Stockage local (tests) : pas de signature possible.
        return storage.url(name)
    import boto3
    from botocore.config import Config

    client = boto3.client(
        "s3",
        endpoint_url=settings.S3_PUBLIC_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    url: str = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET_PRIVATE, "Key": name},
        ExpiresIn=ttl,
    )
    return url
