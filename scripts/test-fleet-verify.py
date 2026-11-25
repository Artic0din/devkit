"""Exercise the fleet command with two isolated, synthetic host processes."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

CLI = Path(__file__).with_name("fleet-verify")


class FleetVerifier(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.policy = {"hosts": {"local": "first", "second": "second"}, "workspace": "~/example",
                       "providers": {"agent": {"versionCommand": ["agent", "--version"],
                       "catalogCommand": ["agent", "list"], "version": "v1", "required": ["nested"],
                       "removed": ["retired"], "composerSkill": "nested", "composerDisplay": "group:nested"}}}
        sample = {"cli": {"agent": "v1"}, "native": {"agent": ["nested"]},
                  "composer": {"agent": {"cold": True, "selected": "nested", "inserted": "nested",
                                         "provider": "agent", "workspace": "~/example",
                                         "selectedLabel": "/skill:group:nested", "insertedLabel": "group:nested"}},
                  "t3": {"enabled": ["agent"], "catalogs": {"agent": {"status": "ready",
                        "auth": "authenticated", "version": "v1", "workspace": True,
                        "skills": ["nested"], "commands": [], "signatures": ["group/nested"]}}}}
        self.data = {host: copy.deepcopy(sample) for host in self.policy["hosts"]}
        for host, name in self.policy["hosts"].items():
            self.data[host]["hostname"] = self.data[host]["t3"]["hostname"] = name
        for program, host in [("bun", "local"), ("ssh", "second")]:
            exe = self.root / program
            exe.write_text(f'#!/bin/sh\ncat >/dev/null\ncat "$FIXTURE/{host}.json"\n')
            exe.chmod(0o755)

    def run_cli(self) -> subprocess.CompletedProcess:
        for host, record in self.data.items():
            (self.root / (host + ".json")).write_text(json.dumps(record))
        policy = self.root / "policy.json"
        policy.write_text(json.dumps(self.policy))
        files = {p: p.read_bytes() for p in self.root.iterdir()}
        result = subprocess.run([CLI, policy], text=True, capture_output=True,
                                env={**os.environ, "FIXTURE": str(self.root),
                                     "PATH": str(self.root) + ":" + os.environ["PATH"]})
        self.assertEqual(files, {p: p.read_bytes() for p in self.root.iterdir()})
        return result

    def test_missing_provider_on_every_host_then_repair(self) -> None:
        for record in self.data.values():
            record["t3"]["enabled"] = ["other"]
        for _ in range(2):
            run = self.run_cli()
            self.assertEqual(run.returncode, 1)
            self.assertIn("missing enabled provider", run.stdout)
        for record in self.data.values():
            record["t3"]["enabled"] = ["agent"]
        self.assertEqual(self.run_cli().stdout.strip(), "MATCH")

    def test_command_only_retired_native_and_absent_host(self) -> None:
        bad = self.data["second"]
        entry = bad["t3"]["catalogs"]["agent"]
        entry.update(skills=[], commands=["nested", "retired"])
        bad["native"]["agent"].append("retired")
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        for text in ["command only", "T3 removed entry present", "native removed entry present"]:
            self.assertIn(text, result.stdout)
        self.data["second"] = {}
        self.assertIn("UNVERIFIED second host identity", self.run_cli().stdout)

    def test_malformed_nested_data(self) -> None:
        self.data["second"]["t3"] = ["invalid"]
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    def test_qualified_labels_and_equivalent_workspace(self) -> None:
        self.policy["workspace"] += "/"
        self.assertEqual(self.run_cli().returncode, 0)
        agent = self.data["second"]["composer"]["agent"]
        agent.update(selectedLabel="/skill:wrong:nested", insertedLabel="wrong:nested")
        self.data["second"]["t3"]["catalogs"]["agent"]["labels"] = ["package:retired"]
        self.policy["providers"]["agent"]["removed"].append("package:retired")
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("cold composer", result.stdout)
        self.assertIn("removed entry present: package:retired", result.stdout)

    def test_server_without_optional_hostname_requires_expected_environment(self) -> None:
        server = self.data["second"]["t3"]
        del server["hostname"]
        server["environmentId"] = "environment-b"
        self.assertEqual(self.run_cli().returncode, 1)
        self.policy["environmentIds"] = {"second": "environment-b"}
        self.assertEqual(self.run_cli().returncode, 0)
        self.policy["environmentIds"]["second"] = "environment-a"
        self.assertEqual(self.run_cli().returncode, 1)

    def test_real_selection_and_full_membership_required(self) -> None:
        bad = self.data["second"]
        bad["composer"]["agent"].update(inserted="/nested", provider="other")
        bad["native"]["agent"].append("hidden")
        bad["cli"]["agent"] = "v2"
        bad["t3"]["catalogs"]["agent"]["signatures"] = ["different/nested"]
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        for text in ["cold composer", "native skills absent from T3", "T3 skill identities", "CLI expected"]:
            self.assertIn(text, result.stdout)
        del self.policy["providers"]["agent"]["composerSkill"]
        self.assertEqual(self.run_cli().returncode, 2)


if __name__ == "__main__":
    unittest.main()
