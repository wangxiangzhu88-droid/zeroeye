import unittest

from tools import config_generator


class ConfigGeneratorTests(unittest.TestCase):
    def test_generate_config_applies_environment_overrides(self):
        development = config_generator.generate_config("development")
        staging = config_generator.generate_config("staging")
        production = config_generator.generate_config("production")

        self.assertEqual("development", development["app"]["environment"])
        self.assertTrue(development["app"]["debug"])
        self.assertEqual("tent_dev", development["database"]["name"])
        self.assertEqual(1000, development["market"]["rate_limit_per_second"])
        self.assertEqual(1440, development["auth"]["jwt_expiry_minutes"])

        self.assertEqual("staging", staging["app"]["environment"])
        self.assertTrue(staging["app"]["debug"])
        self.assertEqual("tent_staging", staging["database"]["name"])
        self.assertEqual(20, staging["database"]["pool_max"])
        self.assertEqual(0.5, staging["monitoring"]["tracing_sample_rate"])

        self.assertEqual("production", production["app"]["environment"])
        self.assertFalse(production["app"]["debug"])
        self.assertEqual("tent_production", production["database"]["name"])
        self.assertEqual(50, production["database"]["pool_max"])
        self.assertTrue(production["auth"]["mfa_required"])

    def test_merge_config_preserves_nested_values_unless_replaced(self):
        base = {
            "server": {
                "host": "0.0.0.0",
                "port": 8080,
                "timeouts": {"read": 30, "write": 60},
            },
            "features": {"web_socket": True, "streaming": True},
        }
        override = {
            "server": {"port": 9090, "timeouts": {"write": 120}},
            "features": {"streaming": False},
        }

        merged = config_generator.merge_config(base, override)

        self.assertEqual("0.0.0.0", merged["server"]["host"])
        self.assertEqual(9090, merged["server"]["port"])
        self.assertEqual(30, merged["server"]["timeouts"]["read"])
        self.assertEqual(120, merged["server"]["timeouts"]["write"])
        self.assertTrue(merged["features"]["web_socket"])
        self.assertFalse(merged["features"]["streaming"])

    def test_generate_config_applies_custom_recursive_overrides(self):
        config = config_generator.generate_config(
            "production",
            {
                "database": {"pool_max": 75},
                "market": {"fees": {"maker": 0.0005}},
            },
        )

        self.assertEqual("tent_production", config["database"]["name"])
        self.assertEqual(10, config["database"]["pool_min"])
        self.assertEqual(75, config["database"]["pool_max"])
        self.assertEqual(0.0005, config["market"]["fees"]["maker"])
        self.assertEqual(0.002, config["market"]["fees"]["taker"])

    def test_mask_sensitive_redacts_database_redis_and_jwt_secrets(self):
        config = config_generator.generate_config(
            "staging",
            {
                "database": {"password": "db-password"},
                "redis": {"password": "redis-password"},
                "auth": {"jwt_secret": "jwt-secret"},
            },
        )

        masked = config_generator.mask_sensitive(config)

        self.assertEqual("***REDACTED***", masked["database"]["password"])
        self.assertEqual("***REDACTED***", masked["redis"]["password"])
        self.assertEqual("***REDACTED***", masked["auth"]["jwt_secret"])
        self.assertEqual("tent_staging", masked["database"]["name"])
        self.assertEqual("staging", masked["app"]["environment"])

    def test_sensitive_keys_are_unique(self):
        self.assertEqual(
            ["database.password", "redis.password", "auth.jwt_secret"],
            config_generator.SENSITIVE_KEYS,
        )
        self.assertEqual(
            len(config_generator.SENSITIVE_KEYS),
            len(set(config_generator.SENSITIVE_KEYS)),
        )


if __name__ == "__main__":
    unittest.main()
