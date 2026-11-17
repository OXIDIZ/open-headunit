import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("sync_upstream", Path(__file__).with_name("sync_upstream.py"))
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class SyncTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.upstream = self.root / "upstream"
        self.upstream.mkdir()
        sync.git(self.upstream, "init", "-b", "main")
        self.identity(self.upstream)
        (self.upstream / "core.txt").write_text("original\n")
        self.commit(self.upstream, "base")
        sync.git(self.upstream, "tag", "v.1.0.0")
        self.fork = self.root / "fork"
        subprocess.run(["git", "clone", "-q", str(self.upstream), str(self.fork)], check=True)
        self.identity(self.fork)
        (self.fork / "geely.txt").write_text("climate dock adaptation\n")
        self.commit(self.fork, "customization")

    @staticmethod
    def identity(root):
        sync.git(root, "config", "user.name", "Sync test")
        sync.git(root, "config", "user.email", "test@example.invalid")

    @staticmethod
    def commit(root, message):
        sync.git(root, "add", ".")
        sync.git(root, "commit", "-qm", message)

    def test_update_preserves_fork_and_is_idempotent(self):
        (self.upstream / "core.txt").write_text("new release\n")
        self.commit(self.upstream, "upstream update")
        sync.git(self.upstream, "tag", "v.1.1.0")
        changed, sha = sync.merge_release(self.fork, str(self.upstream), "v.1.1.0")
        self.assertTrue(changed)
        self.assertEqual("climate dock adaptation\n", (self.fork / "geely.txt").read_text())
        self.assertEqual("new release\n", (self.fork / "core.txt").read_text())
        head = sync.git(self.fork, "rev-parse", "HEAD")
        changed_again, same_sha = sync.merge_release(self.fork, str(self.upstream), "v.1.1.0")
        self.assertFalse(changed_again)
        self.assertEqual(sha, same_sha)
        self.assertEqual(head, sync.git(self.fork, "rev-parse", "HEAD"))
        self.assertEqual(sha, json.loads((self.fork / sync.STATE).read_text())["commit"])

    def test_conflict_aborts_and_keeps_fork_head(self):
        (self.fork / "core.txt").write_text("Geely behavior\n")
        self.commit(self.fork, "fork core")
        head = sync.git(self.fork, "rev-parse", "HEAD")
        (self.upstream / "core.txt").write_text("incompatible upstream behavior\n")
        self.commit(self.upstream, "upstream core")
        sync.git(self.upstream, "tag", "v.1.1.0")
        with self.assertRaisesRegex(RuntimeError, "core.txt"):
            sync.merge_release(self.fork, str(self.upstream), "v.1.1.0")
        self.assertEqual(head, sync.git(self.fork, "rev-parse", "HEAD"))
        self.assertEqual("Geely behavior\n", (self.fork / "core.txt").read_text())
        self.assertEqual("", sync.git(self.fork, "status", "--porcelain"))

    def test_stable_release_selection_rejects_previews_and_invalid_refs(self):
        self.assertEqual("v.4.0.0", sync.stable_tag({"tag_name": "v.4.0.0"}))
        for value in ["v.4.1.0-beta1", "--upload-pack=other", "../main"]:
            with self.assertRaises(ValueError):
                sync.stable_tag({"tag_name": value})
        with self.assertRaises(ValueError):
            sync.stable_tag({"tag_name": "v.4.1.0", "prerelease": True})

    def test_unmarked_beta_and_backport_do_not_replace_latest_stable(self):
        releases = [
            {"tag_name": "v.4.1.0-beta1", "prerelease": False},
            {"tag_name": "v.3.4.1"},
            {"tag_name": "v.5.0.0", "draft": True},
            {"tag_name": "v.4.0.0"},
        ]
        self.assertEqual("v.4.0.0", sync.choose_stable_release(releases)["tag_name"])

    def test_uncommitted_user_changes_are_preserved(self):
        (self.fork / "core.txt").write_text("unsaved user edit\n")
        with self.assertRaisesRegex(RuntimeError, "local changes"):
            sync.merge_release(self.fork, str(self.upstream), "v.1.0.0")
        self.assertEqual("unsaved user edit\n", (self.fork / "core.txt").read_text())


if __name__ == "__main__":
    unittest.main()
