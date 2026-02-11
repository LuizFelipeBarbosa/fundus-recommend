import unittest

from fundus_recommend.ingest.registry import DEFAULT_PUBLISHER_IDS, PUBLISHER_REGISTRY, resolve_publisher_tokens
from fundus_recommend.ingest.types import AdapterType


class IngestRegistryTests(unittest.TestCase):
    def test_default_publisher_ids_are_registered(self) -> None:
        configs, warnings, unknown = resolve_publisher_tokens(list(DEFAULT_PUBLISHER_IDS))

        self.assertEqual(len(unknown), 0)
        self.assertEqual(len(configs), len(DEFAULT_PUBLISHER_IDS))
        self.assertEqual(len(warnings), 0)

    def test_defaults_are_all_fundus_country_collections(self) -> None:
        self.assertGreater(len(DEFAULT_PUBLISHER_IDS), 60)
        for pub_id in DEFAULT_PUBLISHER_IDS:
            config = PUBLISHER_REGISTRY[pub_id]
            self.assertEqual(config.adapter, AdapterType.FUNDUS)
            self.assertEqual(config.fundus_collection, pub_id)

    def test_resolves_expected_adapters_for_key_publishers(self) -> None:
        configs, _warnings, unknown = resolve_publisher_tokens(["cnn", "npr", "reuters", "nyt"])

        self.assertEqual(unknown, [])
        by_id = {config.publisher_id: config for config in configs}

        self.assertEqual(by_id["cnn"].adapter, AdapterType.RSS)
        self.assertEqual(by_id["npr"].adapter, AdapterType.RSS)
        self.assertEqual(by_id["reuters"].adapter, AdapterType.LICENSED_FEED)
        self.assertEqual(by_id["nyt"].adapter, AdapterType.OFFICIAL_API)

    def test_country_code_resolves_as_fundus_without_warning(self) -> None:
        configs, warnings, unknown = resolve_publisher_tokens(["us"])

        self.assertEqual(unknown, [])
        self.assertEqual(len(configs), 1)
        self.assertEqual(configs[0].adapter, AdapterType.FUNDUS)
        self.assertEqual(configs[0].fundus_collection, "us")
        self.assertEqual(configs[0].default_language, "en")
        self.assertEqual(len(warnings), 0)

    def test_unknown_token_is_reported(self) -> None:
        configs, warnings, unknown = resolve_publisher_tokens(["unknown-source"])

        self.assertEqual(configs, [])
        self.assertEqual(warnings, [])
        self.assertEqual(unknown, ["unknown-source"])


if __name__ == "__main__":
    unittest.main()
