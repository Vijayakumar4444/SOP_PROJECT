import unittest

from backend.app.database import check_database_health


class DatabaseHealthTests(unittest.TestCase):
    def test_missing_connection_string_reports_not_configured(self):
        result = check_database_health(conninfo="")

        self.assertFalse(result["connected"])
        self.assertEqual(result["status"], "not_configured")


if __name__ == "__main__":
    unittest.main()
