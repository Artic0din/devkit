#!/usr/bin/env python3
"""Check install metadata validation and recommendation card text fitting."""

import re
from pathlib import Path
from tempfile import TemporaryDirectory

from render_stack_card import SKILL_NAME_WIDTH, SKILL_ROLE_WIDTH, render
from stage_install import parse_name


with TemporaryDirectory() as temporary:
    skill = Path(temporary) / "SKILL.md"
    skill.write_text("---\nname: sample\n---\n")
    try:
        parse_name(skill)
    except ValueError as error:
        assert "missing description" in str(error), error
    else:
        raise AssertionError("a skill without a description was accepted")
    skill.write_text("---\nname: sample\ndescription: >-\n  Example\n---\n")
    assert parse_name(skill) == "sample"

long_name = "-".join(["abcdefghi"] * 8)[:80]
long_role = " ".join(["capability"] * 17)[:180]
svg = render({"title": "T", "goal": "G", "skills": [{"name": long_name, "role": long_role}, {"name": "b"}]})
rows = re.findall(r'<rect x="56" y="\d+" width="1088" height="(\d+)"', svg)
assert len(rows) == 2 and int(rows[0]) > 72 and rows[1] == "72", rows
for size, width in (("24", SKILL_NAME_WIDTH), ("18", SKILL_ROLE_WIDTH)):
    lines = re.findall(rf'<text x="84" [^>]*font-size="{size}"[^>]*>([^<]*)</text>', svg)
    assert lines and all(len(line) <= width for line in lines), lines

print("Install metadata and card wrapping checks passed.")
