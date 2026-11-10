import pytest
from botocore.stub import Stubber
from pydantic import SecretStr

from src.clients.storage import create_storage
from src.clients.storage.client import LocalStorage, R2Storage
from src.core.config import R2Settings, StorageSettings
from src.core.exceptions import ServiceUnavailable

R2 = R2Settings(
    account_id="account",
    bucket="public",
    access_key_id=SecretStr("key"),
    secret_access_key=SecretStr("secret"),
)


def test_r2_is_used_once_every_setting_is_set(tmp_path):
    assert isinstance(create_storage(StorageSettings(r2=R2)), R2Storage)
    partial = R2.model_copy(update={"bucket": ""})
    assert isinstance(
        create_storage(StorageSettings(local_dir=tmp_path, r2=partial)), LocalStorage
    )


async def test_local_storage_writes_under_its_directory(tmp_path):
    storage = create_storage(StorageSettings(local_dir=tmp_path))

    await storage.put("release/current.json", b"{}", "application/json", "max-age=60")

    assert (tmp_path / "release" / "current.json").read_bytes() == b"{}"


async def test_r2_uploads_with_the_content_type_and_cache_header():
    storage = R2Storage(R2)
    with Stubber(storage._client) as r2:
        r2.add_response(
            "put_object",
            {},
            {
                "Bucket": "public",
                "Key": "release/current.json",
                "Body": b"{}",
                "ContentType": "application/json",
                "CacheControl": "max-age=60",
            },
        )
        await storage.put(
            "release/current.json", b"{}", "application/json", "max-age=60"
        )
        r2.assert_no_pending_responses()


async def test_an_r2_error_is_a_service_error():
    storage = R2Storage(R2)
    with Stubber(storage._client) as r2:
        r2.add_client_error("put_object", "AccessDenied", http_status_code=403)
        with pytest.raises(ServiceUnavailable):
            await storage.put(
                "release/current.json", b"{}", "application/json", "max-age=60"
            )
