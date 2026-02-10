import unittest

from fundus_recommend.ingest.registry import DEFAULT_PUBLISHER_IDS, resolve_publisher_tokens
from fundus_recommend.ingest.types import AdapterType


class IngestRegistryTests(unittest.TestCase):
    def test_default_publisher_ids_are_registered(self) -> None:
        configs, warnings, unknown = resolve_publisher_tokens(list(DEFAULT_PUBLISHER_IDS))

        self.assertEqual(len(unknown), 0)
        self.assertEqual(len(configs), len(DEFAULT_PUBLISHER_IDS))
        self.assertEqual(len(warnings), 0)

    def test_resolves_expected_adapters_for_key_publishers(self) -> None:
        configs, _warnings, unknown = resolve_publisher_tokens(["cnn", "npr", "reuters", "nyt"])

        self.assertEqual(unknown, [])
        by_id = {config.publisher_id: config for config in configs}

        self.assertEqual(by_id["cnn"].adapter, AdapterType.RSS)
        self.assertEqual(by_id["npr"].adapter, AdapterType.RSS)
        self.assertEqual(by_id["reuters"].adapter, AdapterType.LICENSED_FEED)
        self.assertEqual(by_id["nyt"].adapter, AdapterType.OFFICIAL_API)

    def test_resolves_legacy_country_code_with_warning(self) -> None:
        configs, warnings, unknown = resolve_publisher_tokens(["us"])

        self.assertEqual(unknown, [])
        self.assertEqual(len(configs), 1)
        self.assertEqual(configs[0].adapter, AdapterType.FUNDUS)
        self.assertEqual(configs[0].fundus_collection, "us")
        self.assertEqual(len(warnings), 1)
        self.assertIn("deprecated", warnings[0])

    def test_unknown_token_is_reported(self) -> None:
        configs, warnings, unknown = resolve_publisher_tokens(["unknown-source"])

        self.assertEqual(configs, [])
        self.assertEqual(warnings, [])
        self.assertEqual(unknown, ["unknown-source"])


if __name__ == "__main__":
    unittest.main()
