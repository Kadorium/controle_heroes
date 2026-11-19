from pathlib import Path
import tempfile
import unittest
from release_url import current_release_url


class ReleaseUrlTests(unittest.TestCase):
    def test_same_ui_has_stable_url_and_a_new_ui_has_another_cache_key(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime = Path(folder)
            html = runtime / "v2/frontend/dist/index.html"
            html.parent.mkdir(parents=True)
            html.write_text("first version", encoding="utf8")
            first = current_release_url("http://127.0.0.1:8082/", runtime)
            self.assertEqual(first, current_release_url("http://127.0.0.1:8082", runtime))
            self.assertRegex(first, r"^http://127\.0\.0\.1:8082/\?epic_ui=[a-f0-9]{16}$")
            html.write_text("second version", encoding="utf8")
            self.assertNotEqual(first, current_release_url("http://127.0.0.1:8082", runtime))

    def test_missing_frontend_does_not_open_an_unversioned_page(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileNotFoundError):
                current_release_url("http://127.0.0.1:8082", Path(folder))


if __name__ == "__main__":
    unittest.main()
