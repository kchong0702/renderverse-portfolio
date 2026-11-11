from urllib.parse import parse_qs, urlsplit

import pytest
from botocore.stub import Stubber
from pydantic import SecretStr, ValidationError

from src.clients.storage import create_storage
from src.clients.storage.client import LocalStorage, R2Storage
from src.core.config import R2Settings, StorageSettings
from src.core.exceptions import ServiceUnavailable

R2 = R2Settings(
    account_id="account",
    bucket="public",
    private_bucket="private",
    access_key_id=SecretStr("key"),
    secret_access_key=SecretStr("secret"),
)
CHECKSUM = "47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU="


def test_r2_is_used_once_every_setting_is_set_and_a_partial_setup_fails(tmp_path):
    assert isinstance(create_storage(StorageSettings(r2=R2), "/ops-api"), R2Storage)
    local = create_storage(StorageSettings(local_dir=tmp_path), "/x")
    assert isinstance(local, LocalStorage)
    with pytest.raises(ValidationError, match="also set private_bucket, secret_acc"):
        R2Settings(**{**R2.model_dump(), "private_bucket": "", "secret_access_key": ""})


async def test_local_storage_writes_under_its_directory(tmp_path):
    storage = create_storage(StorageSettings(local_dir=tmp_path), "/ops-api")

    await storage.put("release/current.json", b"{}", "application/json", "max-age=60")

    assert (tmp_path / "release" / "current.json").read_bytes() == b"{}"


async def test_local_storage_takes_uploads_through_ops_api_and_publishes_them(
    tmp_path,
):
    storage = create_storage(
        StorageSettings(local_dir=tmp_path / "public", local_private_dir=tmp_path),
        "/ops-api",
    )
    assert isinstance(storage, LocalStorage)

    target = storage.upload_target("user/abc", "image/png", 3, CHECKSUM)
    with storage.write_private("user/abc") as file:
        file.write(b"png")
    with pytest.raises(ValueError), storage.write_private("user/def") as file:
        file.write(b"half")
        raise ValueError
    await storage.publish("user/abc", "media/abc.png")

    assert target.url == "/ops-api/v1/portfolio/uploads/abc"
    assert target.headers == {"Content-Type": "image/png"}
    assert storage.download_url("user/abc") == "/ops-api/v1/portfolio/uploads/abc"
    assert [path.name for path in (tmp_path / "user").iterdir()] == ["abc"]
    assert await storage.size("user/abc") == 3
    assert await storage.public_keys("media/") == ["media/abc.png"]
    await storage.unpublish("media/abc.png")
    await storage.delete("user/abc")
    assert await storage.public_keys("media/") == []
    assert await storage.size("user/abc") is None


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


def test_r2_presigns_a_put_into_the_private_bucket_bound_to_the_file():
    target = R2Storage(R2).upload_target("abc", "video/mp4", 3, CHECKSUM)

    url = urlsplit(target.url)
    assert (url.netloc, url.path) == (
        "account.r2.cloudflarestorage.com",
        "/private/abc",
    )
    assert parse_qs(url.query)["X-Amz-SignedHeaders"] == [
        "content-length;content-type;host;x-amz-checksum-sha256"
    ]
    assert target.headers == {
        "Content-Type": "video/mp4",
        "x-amz-checksum-sha256": CHECKSUM,
    }


async def test_r2_reads_sizes_and_copies_and_deletes_in_the_right_bucket():
    storage = R2Storage(R2)
    with Stubber(storage._client) as r2:
        r2.add_response(
            "head_object", {"ContentLength": 3}, {"Bucket": "private", "Key": "abc"}
        )
        r2.add_client_error("head_object", "404", http_status_code=404)
        r2.add_response(
            "copy_object",
            {},
            {
                "Bucket": "public",
                "Key": "media/abc.mp4",
                "CopySource": {"Bucket": "private", "Key": "abc"},
            },
        )
        r2.add_response(
            "list_objects_v2",
            {
                "Contents": [{"Key": "media/b.png"}],
                "IsTruncated": True,
                "NextContinuationToken": "t",
            },
            {"Bucket": "public", "Prefix": "media/"},
        )
        r2.add_response(
            "list_objects_v2",
            {"Contents": [{"Key": "media/a.png"}], "IsTruncated": False},
            {"Bucket": "public", "Prefix": "media/", "ContinuationToken": "t"},
        )
        r2.add_response("delete_object", {}, {"Bucket": "public", "Key": "media/a.png"})
        r2.add_response("delete_object", {}, {"Bucket": "private", "Key": "abc"})

        assert await storage.size("abc") == 3
        assert await storage.size("missing") is None
        await storage.publish("abc", "media/abc.mp4")
        assert await storage.public_keys("media/") == ["media/a.png", "media/b.png"]
        await storage.unpublish("media/a.png")
        await storage.delete("abc")
        r2.assert_no_pending_responses()
