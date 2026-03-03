import io
import unittest
from unittest.mock import patch

from fundus_recommend.services import article_body_store as store


class _FakeClient:
    def __init__(self):
        self.put_calls: list[dict] = []
        self.get_payload: bytes = b""
        self.get_error: Exception | None = None

    def put_object(self, **kwargs):
        self.put_calls.append(kwargs)

    def get_object(self, **kwargs):
        if self.get_error is not None:
            raise self.get_error
        return {"Body": io.BytesIO(self.get_payload)}


class ArticleBodyStoreTests(unittest.TestCase):
    def test_build_body_key_is_deterministic(self) -> None:
        url = "https://example.com/news/abc"
        key1 = store.build_body_key(42, url)
        key2 = store.build_body_key(42, url)

        self.assertEqual(key1, key2)
        self.assertTrue(key1.startswith("articles/42/"))
        self.assertTrue(key1.endswith(".txt"))

    def test_put_and_get_body_success(self) -> None:
        client = _FakeClient()
        client.get_payload = b"hello body"

        with patch("fundus_recommend.services.article_body_store._get_client", return_value=client):
            store.put_body("articles/1/key.txt", "hello body")
            result = store.get_body("articles/1/key.txt")

        self.assertEqual(len(client.put_calls), 1)
        self.assertEqual(client.put_calls[0]["Key"], "articles/1/key.txt")
        self.assertEqual(result, "hello body")

    def test_get_body_raises_not_found_for_missing_key(self) -> None:
        class FakeClientError(Exception):
            def __init__(self, code: str):
                self.response = {"Error": {"Code": code}}

        client = _FakeClient()
        client.get_error = FakeClientError("NoSuchKey")

        with (
            patch("fundus_recommend.services.article_body_store._get_client", return_value=client),
            patch.object(store, "ClientError", FakeClientError),
        ):
            with self.assertRaises(store.BodyNotFoundError):
                store.get_body("articles/1/missing.txt")

    def test_get_body_raises_store_error_on_transport_failure(self) -> None:
        class FakeBotoCoreError(Exception):
            pass

        client = _FakeClient()
        client.get_error = FakeBotoCoreError("timeout")

        with (
            patch("fundus_recommend.services.article_body_store._get_client", return_value=client),
            patch.object(store, "BotoCoreError", FakeBotoCoreError),
        ):
            with self.assertRaises(store.BodyStoreError):
                store.get_body("articles/1/key.txt")


if __name__ == "__main__":
    unittest.main()
