#!/usr/bin/env python3
"""Offline tests for scripts/t3-settings-sync: what merge keeps per Mac, and the LaunchAgent install."""

import os
import subprocess
import sys
import tempfile
import unittest
import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = Path(__file__).resolve().parent
_loader = SourceFileLoader("t3_settings_sync", str(HERE / "t3-settings-sync"))
sync = importlib.util.module_from_spec(importlib.util.spec_from_loader(_loader.name, _loader))
_loader.exec_module(sync)


class MergeTest(unittest.TestCase):
    def test_master_wins_shared_keys_and_target_keeps_local_keys(self):
        master = {"chatWidth": 900, "providerInstances": {"codex": {}, "max-only": {}}, "worktreesDirectory": "/m"}
        target = {"chatWidth": 700, "providerInstances": {"codex": {}}, "worktreesDirectory": "/t"}
        self.assertEqual(
            sync.merge("settings.json", master, target),
            {"chatWidth": 900, "providerInstances": {"codex": {}}, "worktreesDirectory": "/t"},
        )

    def test_key_reset_on_master_is_removed_on_target(self):
        merged = sync.merge("settings.json", {"a": 1}, {"a": 2, "threadTitleInstructions": "old"})
        self.assertEqual(merged, {"a": 1})

    def test_local_key_absent_on_target_is_not_copied(self):
        merged = sync.merge("client-settings.json", {"voiceMicrophone": "max mic", "x": 1}, {})
        self.assertEqual(merged, {"x": 1})

    def test_model_selection_for_missing_instance_keeps_target_value(self):
        master = {
            "providerInstances": {"codex": {}, "acp": {}},
            "defaultModelSelection": {"instanceId": "acp", "model": "m"},
            "textGenerationModelSelection": {"instanceId": "codex", "model": "c"},
        }
        master["providerInstances"]["acp"] = {"driver": "acpRegistry"}
        target = {"providerInstances": {}, "defaultModelSelection": {"instanceId": "codex", "model": "t"}}
        merged = sync.merge("settings.json", master, target)
        self.assertEqual(merged["defaultModelSelection"], {"instanceId": "codex", "model": "t"})
        self.assertEqual(merged["textGenerationModelSelection"], {"instanceId": "codex", "model": "c"})

    def test_target_text_generators_are_kept_with_selections_that_use_them(self):
        master = {"textGenerators": {"m": {}}, "textGenerationModelSelection": {"instanceId": "m"}}
        target = {"textGenerators": {"t": {}}, "textGenerationModelSelection": {"instanceId": "t"}}
        self.assertEqual(sync.merge("settings.json", master, target), target)

    def test_registry_provider_and_its_model_selection_sync_without_local_config(self):
        selection = {"instanceId": "acpRegistry_github_copilot", "model": "gpt"}
        master = {
            "providerInstances": {
                "acpRegistry_github_copilot": {
                    "driver": "acpRegistry",
                    "enabled": True,
                    "config": {
                        "agentId": "github-copilot-cli",
                        "distribution": "auto",
                        "commandPath": "/max/bin/copilot",
                        "commandArgs": ["local-only"],
                    },
                },
                "local-acp": {"driver": "acpRegistry", "config": {
                    "source": "local", "agentId": "local", "commandPath": "/max/bin/local",
                }},
            },
            "defaultModelSelection": selection,
        }
        target = {"providerInstances": {"cursor": {"driver": "cursor"}}}
        expected_instances = {
            **target["providerInstances"],
            "acpRegistry_github_copilot": {
                "driver": "acpRegistry",
                "enabled": True,
                "config": {"agentId": "github-copilot-cli", "distribution": "auto"},
            },
        }
        merged = sync.merge("settings.json", master, target)
        self.assertEqual(merged["providerInstances"], expected_instances)
        self.assertEqual(merged["defaultModelSelection"], selection)
        self.assertEqual(sync.merge("settings.json", master, merged), merged)

    def test_registry_sync_keeps_target_overrides_and_other_instances(self):
        master = {"providerInstances": {
            "devin": {"driver": "acpRegistry", "enabled": False, "config": {"agentId": "devin"}},
            "collision": {"driver": "acpRegistry", "enabled": False, "config": {"agentId": "devin"}},
        }}
        target = {"providerInstances": {
            "devin": {"driver": "acpRegistry", "enabled": True, "config": {
                "agentId": "devin", "commandPath": "/ace/bin/devin", "distribution": "binary",
            }},
            "collision": {"driver": "acpRegistry", "config": {
                "source": "local", "agentId": "devin", "commandPath": "/ace/bin/local",
            }},
            "target-only": {"driver": "codex"},
        }}
        expected = {**target["providerInstances"], "devin": {
            **target["providerInstances"]["devin"], "enabled": False,
        }}
        self.assertEqual(sync.merge("settings.json", master, target)["providerInstances"], expected)

    def test_registry_sync_uses_effective_enabled_state(self):
        def instance(config_enabled):
            return {"driver": "acpRegistry", "enabled": True, "config": {
                "agentId": "devin", "enabled": config_enabled, "commandPath": "/local/bin/devin",
            }}

        disabled = {"providerInstances": {"devin": instance(False)}}
        enabled = {"providerInstances": {"devin": instance(True)}}
        added = sync.merge("settings.json", disabled, {})["providerInstances"]["devin"]
        self.assertFalse(added["enabled"])
        merged = sync.merge("settings.json", enabled, disabled)["providerInstances"]["devin"]
        self.assertTrue(merged["enabled"])
        self.assertIsNot(merged["config"].get("enabled"), False)
        self.assertEqual(merged["config"]["commandPath"], "/local/bin/devin")

    def test_disabled_registry_selection_keeps_working_target_default(self):
        master = {
            "providerInstances": {"devin": {
                "driver": "acpRegistry", "config": {"agentId": "devin", "enabled": False},
            }},
            "defaultModelSelection": {"instanceId": "devin", "model": "devin"},
        }
        target = {"defaultModelSelection": {"instanceId": "codex", "model": "gpt"}}
        merged = sync.merge("settings.json", master, target)
        self.assertFalse(merged["providerInstances"]["devin"]["enabled"])
        self.assertEqual(merged["defaultModelSelection"], target["defaultModelSelection"])

    def test_existing_registry_agent_under_a_different_id_keeps_local_identity(self):
        master = {"providerInstances": {"devin": {
            "driver": "acpRegistry", "enabled": True, "config": {"agentId": "devin"},
        }}}
        target = {"providerInstances": {"local-devin": {
            "driver": "acpRegistry", "enabled": False,
            "config": {"agentId": "devin", "commandPath": "/local/bin/devin"},
        }}}
        self.assertEqual(sync.merge("settings.json", master, target), target)

    def test_distinct_master_instances_of_the_same_agent_both_sync(self):
        master = {"providerInstances": {
            "devin-old": {"driver": "acpRegistry", "enabled": False, "config": {"agentId": "devin"}},
            "devin-current": {"driver": "acpRegistry", "enabled": True, "config": {"agentId": "devin"}},
        }}
        target = {"providerInstances": {"devin-old": master["providerInstances"]["devin-old"]}}
        self.assertEqual(sync.merge("settings.json", master, {})["providerInstances"], master["providerInstances"])
        self.assertEqual(sync.merge("settings.json", master, target)["providerInstances"], master["providerInstances"])

    def test_keybindings_array_is_copied_whole(self):
        self.assertEqual(sync.merge("keybindings.json", [{"key": "mod+k"}], [{"key": "x"}]), [{"key": "mod+k"}])

    def test_changed_keys_lists_only_differences(self):
        self.assertEqual(sync.changed_keys({"a": 1, "b": 2}, {"a": 1, "b": 3, "c": 4}), ["b", "c"])
        self.assertEqual(sync.changed_keys(None, {"a": 1}), ["(whole file)"])
        self.assertEqual(sync.changed_keys({}, {"a": None}), ["a"])
        self.assertEqual(sync.changed_keys({"a": None}, {}), ["a"])


class InstallTest(unittest.TestCase):
    def test_install_writes_valid_watching_launch_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "T3_SETTINGS_SYNC_LAUNCH_AGENTS": tmp, "T3_SETTINGS_SYNC_LOG_DIR": tmp, "T3_SETTINGS_SYNC_NO_LAUNCHCTL": "1"}
            subprocess.run([sys.executable, "-I", str(HERE / "t3-settings-sync"), "install", "ace"], env=env, check=True, capture_output=True)
            plist = (Path(tmp) / f"{sync.LABEL}.plist").read_text()
            self.assertIn("<string>--apply</string>\n\t\t<string>ace</string>", plist)
            self.assertIn("WatchPaths", plist)
            self.assertIn("settings.json</string>", plist)


if __name__ == "__main__":
    unittest.main()
