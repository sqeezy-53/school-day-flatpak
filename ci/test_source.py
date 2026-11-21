import unittest
from source import resolve

SHA = "0410de6935c3740777afd3c420644a34b37ffd08"

class SourceTests(unittest.TestCase):
    def test_full_commit(self):
        self.assertEqual(resolve(SHA), (SHA, SHA, ""))

    def test_annotated_release_tag(self):
        self.assertEqual(resolve("v0.6.2", SHA, True), ("refs/tags/v0.6.2", SHA, "0.6.2"))

    def test_branch_and_invalid_values_are_rejected(self):
        for ref in ("main", "0410de6", "refs/tags/v0.6.2", "v01.1.1", "v1.2.3-rc1", "v0.6.2\n"):
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                resolve(ref)

    def test_release_needs_tag_and_sha(self):
        for ref, sha in [(SHA, SHA), ("v0.6.2", ""), ("v0.6.2", "0410de6")]:
            with self.subTest(ref=ref, sha=sha), self.assertRaises(ValueError):
                resolve(ref, sha, True)

if __name__ == "__main__":
    unittest.main()
