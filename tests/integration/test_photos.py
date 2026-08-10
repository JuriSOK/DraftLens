"""Tests for prospect photo resolution and its export contract.

Photos are the one place DraftLens ships third-party media, so the guards
here are about NOT shipping something wrong: no unlicensed image, no
unattributed image, and no image attached to the wrong person. None of these
tests touch the network — licence and identity logic is pure and tested
directly, and the acquired dataset is only inspected if it already exists.

  ./.venv/bin/python -m unittest discover -s tests -t .
"""

import unittest

from data import photos as ph

HAVE_PHOTOS = ph.PHOTOS_FILE.exists()
needs_photos = unittest.skipUnless(
    HAVE_PHOTOS, "photos not acquired — run scripts/acquire.py photos")


class TestLicenseAllowList(unittest.TestCase):
    def test_free_licenses_are_accepted(self):
        for name in ("CC0", "CC BY 4.0", "CC BY-SA 3.0", "CC BY-SA 4.0",
                    "Public domain", "PD-US", "cc by 2.0"):
            self.assertTrue(ph.is_free_license(name), name)

    def test_non_free_or_unknown_licenses_are_rejected(self):
        for name in ("Fair use", "non-free", "All rights reserved",
                    "Copyrighted free use with restrictions", "", None,
                    "Unknown", "GFDL-only-nope"):
            self.assertFalse(ph.is_free_license(name), name)

    def test_rejection_is_the_default_for_unrecognised_text(self):
        self.assertFalse(ph.is_free_license("something new and unrecognised"))


class TestPhotoExportContract(unittest.TestCase):
    """A photo only reaches the product with identity AND licence verified."""

    def _index(self, rows):
        import pandas as pd
        import app_export

        original = ph.load_photos
        try:
            ph.load_photos = lambda *a, **k: pd.DataFrame(rows)
            return app_export._load_photo_index()
        finally:
            ph.load_photos = original

    def _ok_row(self, **over):
        row = dict(prospect_id="2026-x", status="OK",
                  thumbnail_url="https://upload.wikimedia.org/a.jpg",
                  source_url="https://commons.wikimedia.org/wiki/File:a.jpg",
                  attribution="Some Photographer", license="CC BY-SA 4.0",
                  license_url="https://creativecommons.org/licenses/by-sa/4.0")
        row.update(over)
        return row

    def test_valid_row_is_exported(self):
        idx = self._index([self._ok_row()])
        self.assertIn("2026-x", idx)
        self.assertEqual(idx["2026-x"]["license"], "CC BY-SA 4.0")

    def test_photo_without_attribution_is_not_exported(self):
        idx = self._index([self._ok_row(attribution="")])
        self.assertNotIn("2026-x", idx)

    def test_photo_without_license_is_not_exported(self):
        idx = self._index([self._ok_row(license="")])
        self.assertNotIn("2026-x", idx)

    def test_photo_without_thumbnail_is_not_exported(self):
        idx = self._index([self._ok_row(thumbnail_url="")])
        self.assertNotIn("2026-x", idx)

    def test_non_ok_statuses_are_never_exported(self):
        for status in (ph.STATUS_AMBIGUOUS, ph.STATUS_LICENSE_REJECTED,
                      ph.STATUS_NO_IMAGE, ph.STATUS_NOT_FOUND, "ERROR"):
            idx = self._index([self._ok_row(status=status)])
            self.assertNotIn("2026-x", idx, status)

    def test_missing_dataset_yields_no_photos_not_an_error(self):
        import app_export
        original = ph.load_photos
        try:
            ph.load_photos = lambda *a, **k: None
            self.assertEqual(app_export._load_photo_index(), {})
        finally:
            ph.load_photos = original


class TestIdentitySafety(unittest.TestCase):
    def test_status_constants_distinguish_failure_modes(self):
        """Ambiguity, missing image and licence rejection must be separable
        in the audit — collapsing them would hide why a photo is absent."""
        statuses = {ph.STATUS_OK, ph.STATUS_NO_IMAGE, ph.STATUS_AMBIGUOUS,
                   ph.STATUS_LICENSE_REJECTED, ph.STATUS_NOT_FOUND}
        self.assertEqual(len(statuses), 5)

    def test_search_requires_school_confirmation_in_source(self):
        import inspect
        src = inspect.getsource(ph.search_title)
        self.assertIn("school_key", src)
        self.assertIn("disambiguation", src)

    def test_photos_never_influence_analytics(self):
        """The photo module's CODE must not touch any scoring path. Prose in
        docstrings is stripped first — the module's own documentation says it
        is never read by a board or a score, which is the opposite of a
        violation."""
        import ast
        import inspect

        tree = ast.parse(inspect.getsource(ph))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef,
                                ast.AsyncFunctionDef, ast.ClassDef)):
                if (node.body and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)):
                    node.body = node.body[1:] or [ast.Pass()]
        code = ast.unparse(tree).lower()
        for banned in ("stage_a", "overall_score", "team_need",
                      "find_comparables", "board_rank", "drafted"):
            self.assertNotIn(banned, code, banned)


@needs_photos
class TestAcquiredPhotoDataset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = ph.load_photos()

    def test_every_ok_row_has_attribution_and_license(self):
        ok = self.df[self.df.status == "OK"]
        for r in ok.itertuples():
            self.assertTrue(str(r.thumbnail_url).strip(), r.prospect_id)
            self.assertTrue(str(r.attribution).strip(), r.prospect_id)
            self.assertTrue(str(r.license).strip(), r.prospect_id)

    def test_every_ok_license_is_on_the_free_allow_list(self):
        ok = self.df[self.df.status == "OK"]
        for r in ok.itertuples():
            self.assertTrue(ph.is_free_license(r.license),
                           f"{r.prospect_id}: {r.license}")

    def test_thumbnails_are_wikimedia_hosted(self):
        ok = self.df[self.df.status == "OK"]
        for r in ok.itertuples():
            self.assertIn("wikimedia.org", str(r.thumbnail_url),
                         r.prospect_id)

    def test_prospect_ids_are_unique(self):
        self.assertTrue(self.df.prospect_id.is_unique)


if __name__ == "__main__":
    unittest.main()
