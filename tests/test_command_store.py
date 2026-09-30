import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import command_store as cs  # noqa: E402


class PlaceholderTests(unittest.TestCase):
    def test_unique_in_order(self):
        self.assertEqual(cs.placeholders("gam user <new_owner> add acl <file_id> user <new_owner>"),
                         ["new_owner", "file_id"])

    def test_fill_replaces_every_occurrence(self):
        out = cs.fill("gam user <e> print courses teacherID <e>", {"e": "a@b.com"})
        self.assertEqual(out, "gam user a@b.com print courses teacherID a@b.com")

    def test_fill_single_pass(self):
        # A value containing another placeholder must not be substituted again.
        out = cs.fill("<a> <b>", {"a": "<b>", "b": "x"})
        self.assertEqual(out, "<b> x")

    def test_fill_keeps_blank_placeholders(self):
        self.assertEqual(cs.fill("<a> <b>", {"a": "1"}), "1 <b>")
        self.assertEqual(cs.missing_values("<a> <b>", {"a": "1", "b": "  "}), ["b"])

    def test_redirection_is_not_a_placeholder(self):
        self.assertEqual(cs.placeholders("Get-Thing 2>&1 | Out-File <path>"), ["path"])

    def test_choices(self):
        self.assertEqual(cs.placeholder_choices("reader|writer|owner"), ["reader", "writer", "owner"])
        self.assertEqual(cs.placeholder_choices("user"), [])


class ParseTests(unittest.TestCase):
    def test_legacy_desktop_and_web_layouts(self):
        data = {
            "GAM": [{"command": "gam info domain", "description": "Domain",
                     "copied_at": "2026-01-02T00:00:00", "last_used": "2026-01-01T00:00:00",
                     "category": "GAM", "custom": 1}],
            "powershell": [{"command": "Get-Process", "description": "Procs"}],
            "bogus": [{"command": "x", "description": "y"}],
        }
        cmds = cs.parse_commands(data)
        self.assertEqual([(c.category, c.command) for c in cmds],
                         [("GAM", "gam info domain"), ("PowerShell", "Get-Process")])
        self.assertEqual(cmds[0].last_used, "2026-01-02T00:00:00")
        self.assertEqual(cmds[0].extra, {"custom": 1})
        self.assertNotIn("copied_at", cmds[0].to_dict())

    def test_drops_empty_and_duplicate(self):
        cmds = cs.parse_commands({"AD": [
            {"command": "Get-ADUser  <u>", "description": "a"},
            {"command": "get-aduser <u>", "description": "A "},
            {"command": "get-aduser <u>", "description": "other section"},
            {"command": "   ", "description": "c"},
            "junk",
        ]})
        self.assertEqual([c.description for c in cmds], ["a", "other section"])

    def test_rejects_non_object(self):
        with self.assertRaises(ValueError):
            cs.parse_commands([1, 2])


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.lib = os.path.join(self.dir, "library.json")
        with open(self.lib, "w", encoding="utf-8") as f:
            json.dump({"GAM": [{"command": "gam info domain", "description": "Domain info"},
                               {"command": "gam user <user> suspended on", "description": "Suspend a user"}],
                       "AD": [{"command": "Get-ADUser -Identity <user>", "description": "Get a user"}]}, f)
        self.path = os.path.join(self.dir, "data", "commands.json")

    def tearDown(self):
        self.tmp.cleanup()

    def store(self):
        s = cs.CommandStore(self.path, self.lib)
        s.load()
        return s

    def test_seeds_from_library(self):
        s = self.store()
        self.assertEqual(len(s.commands), 3)
        self.assertTrue(os.path.exists(self.path))

    def test_crud_roundtrip(self):
        s = self.store()
        c = s.add("PowerShell", "Get-Service", "Services")
        with self.assertRaises(ValueError):
            s.add("powershell", " Get-Service ", "services ")
        s.toggle_favorite(c)
        s.mark_used(c)
        s2 = self.store()
        c2 = s2.find("PowerShell", "get-service")
        self.assertTrue(c2.favorite)
        self.assertEqual(c2.use_count, 1)
        s2.update(c2, "PowerShell", "Get-Service -Name <name>", "One service")
        idx = s2.remove(c2)
        self.assertIsNone(self.store().find("PowerShell", "Get-Service -Name <name>"))
        s2.restore(c2, idx)
        self.assertIsNotNone(self.store().find("PowerShell", "Get-Service -Name <name>"))

    def test_update_rejects_collision(self):
        s = self.store()
        a = s.find("GAM", "gam info domain")
        with self.assertRaises(ValueError):
            s.update(a, "GAM", "gam user <user> suspended on", "Suspend a user")
        s.update(a, "GAM", "gam user <user> suspended on", "Same command, other section")

    def test_corrupt_file_is_never_overwritten(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w") as f:
            f.write("{ not json")
        s = cs.CommandStore(self.path, self.lib)
        with self.assertRaises(cs.StoreError):
            s.load()
        self.assertTrue(s.read_only)
        with self.assertRaises(cs.StoreError):
            s.add("GAM", "gam x", "x")
        with open(self.path) as f:
            self.assertEqual(f.read(), "{ not json")
        self.assertTrue(any(".corrupt-" in n for n in os.listdir(os.path.dirname(self.path))))

    def test_search_ranking_and_filters(self):
        s = self.store()
        self.assertEqual([c.description for c in s.search("get")][0], "Get a user")
        self.assertEqual(len(s.search("user")), 2)
        self.assertEqual(len(s.search("user", category="GAM")), 1)
        self.assertEqual(s.search("suspend user")[0].description, "Suspend a user")
        self.assertEqual(s.search("zzz"), [])
        self.assertEqual(s.search(favorites=True), [])
        s.mark_used(s.commands[0])
        self.assertEqual(len(s.search(recent=True)), 1)

    def test_import_export_merge(self):
        s = self.store()
        fav = s.commands[0]
        s.toggle_favorite(fav)
        out = os.path.join(self.dir, "export.json")
        self.assertEqual(s.export_file(out), 3)
        with open(out) as f:
            exported = json.load(f)
        self.assertNotIn("use_count", exported["GAM"][0])

        other = cs.CommandStore(os.path.join(self.dir, "other.json"))
        other.load()
        self.assertEqual(other.import_file(out), (3, 0))
        self.assertEqual(other.import_file(out), (0, 3))
        self.assertTrue(other.find("GAM", fav.command).favorite)

    def test_merge_library_restores_deleted_builtins(self):
        s = self.store()
        s.remove(s.commands[0])
        self.assertEqual(s.merge_library(), (1, 2))


class SettingsTests(unittest.TestCase):
    def test_recent_values(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "settings.json")
            st = cs.Settings(p)
            for v in ["a", "b", "a"]:
                st.remember_values({"user": v, "role": "", "reader|writer": "reader"})
            self.assertEqual(cs.Settings(p).recent_values("user"), ["a", "b"])
            self.assertEqual(st.recent_values("reader|writer"), [])

    def test_bad_settings_file_uses_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "settings.json")
            with open(p, "w") as f:
                f.write("nope")
            self.assertEqual(cs.Settings(p).get("theme"), "dark")


class DataDirTests(unittest.TestCase):
    """Where data lives for source runs, the portable exe and installed copies."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.exe_dir = os.path.join(self.tmp.name, "app")
        os.makedirs(self.exe_dir)
        self.user_dir = os.path.join(self.tmp.name, "user")
        self._saved = (getattr(sys, "frozen", None), sys.executable,
                       os.environ.pop(cs.DATA_DIR_ENV, None), cs.user_data_dir)
        cs.user_data_dir = lambda: self.user_dir

    def tearDown(self):
        frozen, exe, env, udd = self._saved
        if frozen is None:
            if hasattr(sys, "frozen"):
                del sys.frozen
        else:
            sys.frozen = frozen
        sys.executable = exe
        if env is not None:
            os.environ[cs.DATA_DIR_ENV] = env
        cs.user_data_dir = udd
        self.tmp.cleanup()

    def freeze(self):
        sys.frozen = True
        sys.executable = os.path.join(self.exe_dir, "GAM_Command_Bank.exe")

    def test_source_run_uses_user_dir(self):
        if hasattr(sys, "frozen"):
            del sys.frozen
        self.assertEqual(cs.resolve_data_dir(), self.user_dir)

    def test_portable_exe_uses_its_folder(self):
        self.freeze()
        self.assertEqual(cs.resolve_data_dir(), self.exe_dir)

    def test_installed_exe_uses_user_dir(self):
        self.freeze()
        open(os.path.join(self.exe_dir, cs.INSTALLED_MARKER), "w").close()
        self.assertTrue(cs.is_installed())
        self.assertEqual(cs.resolve_data_dir(), self.user_dir)

    def test_env_override_wins(self):
        self.freeze()
        os.environ[cs.DATA_DIR_ENV] = self.tmp.name
        try:
            self.assertEqual(cs.resolve_data_dir(), os.path.abspath(self.tmp.name))
        finally:
            del os.environ[cs.DATA_DIR_ENV]


class RepoLibraryTests(unittest.TestCase):
    def test_shipped_library_is_valid(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "commands.json")
        raw = cs.read_json(path)
        total = sum(len(v) for v in raw.values())
        self.assertEqual(len(cs.parse_commands(raw)), total, "library has duplicate or empty entries")


if __name__ == "__main__":
    unittest.main()
