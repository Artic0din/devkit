---
summary: Compare the effective agent setup across machines, including a nested skill in the T3 composer.
read_when:
  - Checking a fleet after a provider installation, cleanup or settings sync.
---
# Verify the effective fleet setup

Run `scripts/fleet-verify /path/to/private-policy.json` before and after syncing.
Use the approved provider list, expected CLI versions and removal decisions to build the policy.
Keep actual host names, catalogs and evidence outside this repository.
The verifier needs Bun and a running T3 Code server on each host, Python 3 on the initiating host and batch-mode SSH for remote hosts.
Run it from a trusted machine and use trusted argument arrays. Each catalog or composer adapter runs as your user inside the selected workspace.

```json
{
  "hosts": {"local": "first", "second-ssh-alias": "second"},
  "workspace": "~/projects/example",
  "providers": {
    "example-provider": {
      "versionCommand": ["example-cli", "--version"],
      "version": "example-cli 1.0",
      "catalogCommand": ["example-cli", "skills", "--json"],
      "required": ["nested-skill"],
      "removed": ["retired-skill"],
      "composerSkill": "nested-skill",
      "composerCommand": ["/path/to/fleet-composer.cjs", "example/project", "example-provider", "nested-skill", "example-plugin:nested-skill"]
    }
  }
}
```

Use the T3 provider instance ID as the key.
When T3 omits the optional server hostname, supply a top-level `environmentIds` object mapping SSH aliases (including `local`) to their expected T3 environment IDs.
Pinning an ID verifies it even when the server also publishes a hostname.
List every expected enabled provider and its exact first line of version output.
Set `runtimeVersionRequired` to false only for a driver that supplies no T3 version; the standalone version check still runs.
A native adapter must query the running provider or its own skill-list command and print a JSON array of names or records with a `name` field.
Disabled and unloadable entries cannot satisfy a requirement.
A plugin list containing only package names or a slash-command list cannot establish native skill discovery.

For the composer check, open a fresh client for the requested project and provider, type the nested skill mid-sentence, select its qualified skill entry, and read the inserted skill reference from the unsent draft.
The included `scripts/fleet-composer.cjs` drives the installed T3 web client in a new Chrome profile with a session scoped to reading.
Install this repository's locked dependencies with `bun install --frozen-lockfile` on the probe host, or bundle the helper once with `bun build scripts/fleet-composer.cjs --target=node --format=cjs --outfile=/path/to/fleet-composer-bundle.cjs` and run that file with Node on each host.
Supply the GitHub repository already registered with T3, the provider, the name T3 stores in the draft and the qualified display name.
An optional `FLEET_CHROME` environment variable selects the Chrome binary.
The adapter must observe the selected provider and workspace as well as the skill identity.
Return one JSON object, for example `{"provider":"example-provider","workspace":"~/projects/example","cold":true,"selected":"nested-skill","inserted":"nested-skill"}`.
Use a fresh client for each measurement and record separately whether the running server already cached that workspace.
A cached screenshot, a command match or a directory listing cannot supply this evidence.
The example workspace is home-relative; the bundled helper reports the absolute project root.
Without a functioning adapter the command reports the missing observation.

The verifier refreshes each provider in the exact workspace through its running T3 server.
It grants itself a short-lived read session and revokes it afterward.
It does not sync files or modify installations.
Exit 0 means every check specified by the policy passed, 1 means a difference or missing observation, and 2 means the policy or inventory could not be interpreted.
The comparison covers the supplied providers and native catalog adapters.
It does not certify every desktop interaction.
