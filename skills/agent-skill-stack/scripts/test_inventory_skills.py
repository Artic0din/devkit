#!/usr/bin/env python3
"""Check the block descriptions used by imported skills."""

from pathlib import Path
from tempfile import TemporaryDirectory

from inventory_skills import iter_skill_files, parse_frontmatter


for scalar in (">", ">-", ">+", "|", "|-", "|+"):
    text = f"---\nname: sample\ndescription: {scalar}\n  first line\n  second line\n---\n"
    metadata, issues = parse_frontmatter(text)
    separator = " " if scalar.startswith(">") else "\n"
    assert metadata["description"] == separator.join(("first line", "second line")), scalar
    assert not issues, issues

with TemporaryDirectory() as temporary:
    base = Path(temporary)
    root = base / "installed"
    root.mkdir()
    source = base / "source"
    source.mkdir()
    skill = source / "SKILL.md"
    skill.write_text("---\nname: sample\ndescription: Example\n---\n")
    (root / "first").symlink_to(source, target_is_directory=True)
    (root / "second").symlink_to(source, target_is_directory=True)
    (source / "cycle").symlink_to(root, target_is_directory=True)
    found = list(iter_skill_files(root))
    assert len(found) == 1 and found[0].resolve() == skill.resolve(), found

print("Block description and linked skill checks passed.")
