import json
import base64
import os
from pathlib import Path
import subprocess
import tempfile


def run_hook(stdout: str, stderr: str = "") -> str:
    payload = {"tool_response": {"stdout": stdout, "stderr": stderr}}
    result = subprocess.run(
        ["bash", str(Path(__file__).with_name("bash-output-scrub.sh"))],
        input=json.dumps(payload), text=True, capture_output=True, check=True,
        timeout=3,
    )
    assert result.stderr == "", result.stderr
    return result.stdout


def test_inline_yaml() -> None:
    for field in ("password", "api_key", "SecretAccessKey"):
        for prefix in ("", "  ", "- ", "  - "):
            for channel in ("stdout", "stderr"):
                text = f"{prefix}{field}: correct horse battery staple\nuser: bob\n"
                output = run_hook(text if channel == "stdout" else "", text if channel == "stderr" else "")
                result = json.loads(output)
                assert result["decision"] == "block"
                assert "horse battery staple" not in result["reason"], "inline YAML value leaked"
                assert "user: bob" in result["reason"]


def test_empty_quoted_segments() -> None:
    for value in ('""hunter2', "''hunter2", "''\"\"hunter2", '""hun\'\'ter2', '""', "''"):
        for channel in ("stdout", "stderr"):
            text = f"PASSWORD={value}\nuser=bob\n"
            output = run_hook(text if channel == "stdout" else "", text if channel == "stderr" else "")
            assert output, "empty quoted segment bypassed blocking"
            result = json.loads(output)
            assert result["decision"] == "block"
            assert "hunter2" not in result["reason"] and "ter2" not in result["reason"]
            assert "user=bob" in result["reason"]


def test_safe_identifiers() -> None:
    identifiers = ("97e5ddcd8e0237eea46d05c0882e2f2eae7470c5", "ABCDEF1234" * 4,
                   "AbCdEf1234" * 4, "01a125c2-15e7-7212-8311-25672b51aa18", "a" * 64)
    for identifier in identifiers:
        for channel in ("stdout", "stderr"):
            text = f"commit {identifier}\n"
            assert run_hook(text if channel == "stdout" else "", text if channel == "stderr" else "") == "", "safe identifier blocked"
            output = run_hook(f"api_key={identifier}" if channel == "stdout" else "",
                              f"api_key={identifier}" if channel == "stderr" else "")
            assert json.loads(output)["decision"] == "block" and identifier not in output


def test_yaml_boundaries() -> None:
    for channel in ("stdout", "stderr"):
        for text in ("{password: correct horse battery staple, user: bob}",
                     "password: |\n  correct horse battery staple\nuser: bob\n",
                     "password: >-\n  correct horse battery staple\nuser: bob\n"):
            output = run_hook(text if channel == "stdout" else "", text if channel == "stderr" else "")
            assert json.loads(output)["decision"] == "block"
            assert "horse battery staple" not in output, "YAML boundary leaked value"
            assert ("user: bob" in output) == text.startswith("{"), "YAML preview boundary changed"
        text = "password:\nuser: bob\n"
        assert run_hook(text if channel == "stdout" else "", text if channel == "stderr" else "") == "", "empty YAML field consumed next line"


def test_quoted_yaml_keys() -> None:
    for quote in ("'", '"'):
        for value in ("correct horse,battery staple", "|\n  correct horse battery staple", ">-\n  correct horse battery staple"):
            for channel in ("stdout", "stderr"):
                text = f"  - {quote}password{quote}: {value}\n"
                output = run_hook(text if channel == "stdout" else "", text if channel == "stderr" else "")
                assert json.loads(output)["decision"] == "block"
                assert "battery staple" not in output, "quoted YAML key leaked value"


def test_terminal_assignment_boundaries() -> None:
    for channel in ("stdout", "stderr"):
        for sequence in ("\x1b]0;my title\x07", "\x1bPmy title\x1b\\", "\x1bXmy title\x1b\\", "\x1b^my title\x1b\\", "\x1b_my title\x1b\\"):
            text = f"password={sequence}hunter2\nuser=bob\n"
            output = run_hook(text if channel == "stdout" else "", text if channel == "stderr" else "")
            assert json.loads(output)["decision"] == "block"
            assert "hunter2" not in output, "terminal sequence exposed assignment tail"


def test_environment_and_yaml_properties() -> None:
    cases = ("PASSWORD=correct horse battery staple\nuser=bob\n",
             "password: &pw |\n  correct horse battery staple\nuser: bob\n",
             "password: !!str >-\n  correct horse battery staple\nuser: bob\n")
    for text in cases:
        for channel in ("stdout", "stderr"):
            output = run_hook(text if channel == "stdout" else "", text if channel == "stderr" else "")
            assert json.loads(output)["decision"] == "block"
            assert "horse battery staple" not in output, "assignment boundary leaked value"
            assert ("user=bob" in output) == text.startswith("PASSWORD=")


def test_yaml_flow_and_indented_continuations() -> None:
    marker = "synthetic-yaml-continuation-value"
    leaking = (
        f"{{password: &pw\n  {marker}}}",
        f"{{password: !secret\n  {marker}}}",
        f"{{api_key: !!str\n  {marker}}}",
        f"{{ password: &pw\n  {marker} }}",
        f"password:\n  {marker}\nuser: bob\n",
        f"password: \n  {marker}\nuser: bob\n",
        f"password:\n\t{marker}\nuser: bob\n",
        f"  password:\n    {marker}\n  user: bob\n",
        f"- password:\n    {marker}\nuser: bob\n",
        f"'password':\n  {marker}\nuser: bob\n",
        f'password:\n  {marker}',
    )
    for text in leaking:
        for channel in ("stdout", "stderr"):
            output = run_hook(text if channel == "stdout" else "", text if channel == "stderr" else "")
            assert output, f"continuation bypassed blocking on {channel}: {text!r}"
            result = json.loads(output)
            assert result["decision"] == "block", text
            assert marker not in result["reason"], f"continuation leaked on {channel}: {text!r}"
            assert marker not in output, f"continuation leaked on {channel}: {text!r}"
    for text in ("password:\nuser: bob\n", "config:\n  retries: 3\n", "{user: bob, retries: 3}"):
        for channel in ("stdout", "stderr"):
            assert run_hook(text if channel == "stdout" else "", text if channel == "stderr" else "") == "", text


def test_yaml_ignorable_and_flow_continuations() -> None:
    # Legal YAML may start a plain value after blank lines, comments, CRLF, or a
    # newline inside flow containers; assert block + literal marker absence.
    marker = "synthetic-continuation-probe"
    leaking = (
        f"password:\n\n  {marker}\nuser: bob\n",
        f"password: # explanatory comment\n  {marker}\nuser: bob\n",
        f"{{password:\n  {marker}, user: bob}}",
        f"password:\r\n\r\n  {marker}\r\nuser: bob\r\n",
        f"password:\n# only a separator comment\n  {marker}\nuser: bob\n",
        f"password:\n\n# comment after blank\n  {marker}\nuser: bob\n",
        f"  password:\n\n    {marker}\n  user: bob\n",
        f"[password:\n  {marker}, user: bob]",
        f"{{ password:\n  {marker} , user: bob }}",
    )
    for text in leaking:
        for channel in ("stdout", "stderr"):
            output = run_hook(text if channel == "stdout" else "", text if channel == "stderr" else "")
            assert output, f"continuation bypassed blocking on {channel}: {text!r}"
            result = json.loads(output)
            assert result["decision"] == "block", text
            assert marker not in result["reason"], f"continuation leaked on {channel}: {text!r}"
            assert marker not in output, f"continuation leaked on {channel}: {text!r}"
    for text in (
        "password:\nuser: bob\n",
        "password: null\nuser: bob\n",
        "password: true\nuser: bob\n",
        "password: #\nuser: bob\n",
        "config:\n  retries: 3\n",
        "{user: bob, retries: 3}",
    ):
        for channel in ("stdout", "stderr"):
            output = run_hook(text if channel == "stdout" else "", text if channel == "stderr" else "")
            if text.startswith("password: null") or text.startswith("password: true"):
                result = json.loads(output)
                assert result["decision"] == "block", text
                assert "user: bob" in result["reason"], text
            else:
                assert output == "", text


def test_yaml_same_line_plain_folded_continuations() -> None:
    # Psych-valid plain scalars may start on the key line and fold onto more-indented
    # following lines; both value-start paths must use the same continuation bounds.
    marker = "SYNTH_MARKER_VALUE_9f3a"
    leaking = (
        f"password: first-part\n  {marker}\nuser: bob\n",
        f"password: first-part\n\n  {marker}\nuser: bob\n",
        f"password: first part more\n  {marker}\nuser: bob\n",
        f"password: first-part\n# separator comment\n  {marker}\nuser: bob\n",
        f"password: first-part\r\n\r\n  {marker}\r\nuser: bob\r\n",
        f"  password: first-part\n    {marker}\n  user: bob\n",
        f"- password: first-part\n    {marker}\nuser: bob\n",
        f"{{password: first-part\n  {marker}, user: bob}}",
        f"[password: first-part\n  {marker}, user: bob]",
    )
    for text in leaking:
        for channel in ("stdout", "stderr"):
            output = run_hook(text if channel == "stdout" else "", text if channel == "stderr" else "")
            assert output, f"same-line fold bypassed blocking on {channel}: {text!r}"
            result = json.loads(output)
            assert result["decision"] == "block", text
            assert marker not in result["reason"], f"same-line fold leaked on {channel}: {text!r}"
            assert marker not in output, f"same-line fold leaked on {channel}: {text!r}"
            assert "first-part" not in result["reason"] and "first part more" not in result["reason"], text
            if "user: bob" in text and not text.lstrip().startswith(("{", "[")):
                assert "user: bob" in result["reason"], text
    for text in (
        f'password: "first-part, still-quoted"\nuser: bob\n',
        f"password: 'first-part, still-quoted'\nuser: bob\n",
        f'{{password: "a,b,c", user: bob}}',
        f"{{password: 'closer]inside', user: bob}}",
        "password: first-part\nuser: bob\n",
        "password: null\nuser: bob\n",
        "config:\n  retries: 3\nuser: bob\n",
    ):
        for channel in ("stdout", "stderr"):
            output = run_hook(text if channel == "stdout" else "", text if channel == "stderr" else "")
            if text.startswith("config:"):
                assert output == "", text
                continue
            result = json.loads(output)
            assert result["decision"] == "block", text
            assert marker not in output, text
            assert "user: bob" in result["reason"], text
            if "still-quoted" in text or "a,b,c" in text or "closer]inside" in text:
                assert "still-quoted" not in result["reason"]
                assert "a,b,c" not in result["reason"]
                assert "closer]inside" not in result["reason"]
            if text == "password: first-part\nuser: bob\n":
                assert "first-part" not in result["reason"], text


def test_completed_flow_value_keeps_later_output() -> None:
    for text in (
        "{password: first-part, user: bob}\nUNRELATED_KEEP_ME\n",
        "[password: first-part, user: bob]\nUNRELATED_KEEP_ME\n",
        "{password: first-part}\nuser: bob\nUNRELATED_KEEP_ME\n",
        "{password: first-part,\n  user: bob}\nUNRELATED_KEEP_ME\n",
    ):
        for channel in ("stdout", "stderr"):
            output = run_hook(text if channel == "stdout" else "", text if channel == "stderr" else "")
            result = json.loads(output)
            assert result["decision"] == "block", text
            assert "first-part" not in result["reason"], f"flow value leaked on {channel}: {text!r}"
            assert "user: bob" in result["reason"], f"sibling hidden on {channel}: {text!r}"
            assert "UNRELATED_KEEP_ME" in result["reason"], f"later output hidden on {channel}: {text!r}"


def test_collection_values_hide_every_element() -> None:
    for collection in (
        '{"api_keys": ["alpha", "beta-secret"], "user": "bob"}',
        "{api_keys: [alpha, beta-secret], user: bob}",
        "- {tokens: [alpha, beta-secret], user: bob}",
        '{"password": {"first": "alpha", "second": "beta-secret"}, "user": "bob"}',
        '{"api_keys": ["a]b", "beta-secret"], "user": "bob"}',
        "api_keys: [alpha,\nbeta-secret]\nuser: bob",
        "Config(passwords=['alpha', 'beta-secret'], user='bob')",
        '{\n  "api_keys": [\n    "alpha",\n    "beta-secret"\n  ],\n  "user": "bob"\n}',
    ):
        for text in (collection, collection + "\nUNRELATED_KEEP_ME\n"):
            for channel in ("stdout", "stderr"):
                output = run_hook(text if channel == "stdout" else "", text if channel == "stderr" else "")
                result = json.loads(output)
                assert result["decision"] == "block", text
                assert "beta-secret" not in result["reason"], f"collection element leaked on {channel}: {text!r}"
                assert "bob" in result["reason"], f"sibling hidden on {channel}: {text!r}"
                if "UNRELATED_KEEP_ME" in text:
                    assert "UNRELATED_KEEP_ME" in result["reason"], f"later output hidden on {channel}: {text!r}"
    for text in ("{api_keys: [alpha, beta-secret", "{api_keys: [alpha, beta-secret\nuser: bob\n"):
        output = run_hook(text)
        assert "beta-secret" not in json.loads(output)["reason"], f"unclosed collection leaked: {text!r}"


def test_values_on_next_line_and_after_collection_closers() -> None:
    for text in (
        "PASSWORD=\nbeta-secret\n",
        "PASSWORD=\r\nbeta-secret\r\n",
        "PASSWORD=  \n\nbeta-secret\nuser=bob\n",
        'api_keys=\n["alpha", "beta-secret"]\n',
        "password:\nbeta-secret\nuser: bob\n",
        "  password: \n  beta-secret\n  user: bob\n",
        "- password:\nbeta-secret\n",
        "{password: [alpha]beta-secret, user: bob}",
        "{password: [] beta-secret, user: bob}",
        "{api_keys: [a]b, beta-secret], user: bob}",
        "x password=[alpha]beta-secret",
    ):
        for channel in ("stdout", "stderr"):
            output = run_hook(text if channel == "stdout" else "", text if channel == "stderr" else "")
            assert output, f"value bypassed blocking on {channel}: {text!r}"
            result = json.loads(output)
            assert result["decision"] == "block", text
            assert "beta-secret" not in result["reason"], f"value leaked on {channel}: {text!r}"
    for text in ("PASSWORD=\nUSER=bob\n", "password:\nuser: bob\n"):
        assert run_hook(text) == "", f"empty field hid its sibling: {text!r}"


def test_separator_on_later_line_and_flow_comments() -> None:
    for text in (
        '{"password"\n:\n"beta-secret","user":"bob"}\n',
        "password\n= beta-secret\n",
        "{api_keys: [\n  alpha, # ]\n  beta-secret\n], user: bob}\n",
        "{password: {a: alpha, # }\n b: beta-secret}, user: bob}\n",
        "{api_keys: [a,# ]\n beta-secret] }\n",
        "{api_keys: [a,[b],# ]\n beta-secret] }\n",
    ):
        for channel in ("stdout", "stderr"):
            output = run_hook(text if channel == "stdout" else "", text if channel == "stderr" else "")
            assert output, f"value bypassed blocking on {channel}: {text!r}"
            result = json.loads(output)
            assert result["decision"] == "block", text
            assert "beta-secret" not in result["reason"], f"value leaked on {channel}: {text!r}"


def test_many_fields_scan_in_linear_time() -> None:
    assert run_hook("# password:\n" * 20000) == ""
    for text in ("# password: x\n" * 20000, '{"token":"a",' * 50000, "{token: a, " * 50000, " " * 20000 + "x " + "token=a, " * 20000):
        assert json.loads(run_hook(text))["decision"] == "block", text[:40]


def test_list_item_keys_keep_siblings() -> None:
    for text in (
        "- password: first-part\n  user: bob\n",
        "- password: first-part\n    folded-secret\n  user: bob\n",
        '  - "password": first-part\n    user: bob\n',
    ):
        result = json.loads(run_hook(text))
        assert result["decision"] == "block", text
        assert "first-part" not in result["reason"] and "folded-secret" not in result["reason"], text
        assert "user: bob" in result["reason"], f"list item sibling hidden: {text!r}"


if __name__ == "__main__":
    test_inline_yaml()
    test_empty_quoted_segments()
    test_safe_identifiers()
    test_yaml_boundaries()
    test_quoted_yaml_keys()
    test_terminal_assignment_boundaries()
    test_environment_and_yaml_properties()
    test_yaml_flow_and_indented_continuations()
    test_yaml_ignorable_and_flow_continuations()
    test_yaml_same_line_plain_folded_continuations()
    test_completed_flow_value_keeps_later_output()
    test_collection_values_hide_every_element()
    test_values_on_next_line_and_after_collection_closers()
    test_separator_on_later_line_and_flow_comments()
    test_many_fields_scan_in_linear_time()
    test_list_item_keys_keep_siblings()
    for response in ({}, {"stdout": ""}, {"stderr": ""}):
        result = subprocess.run(
            ["bash", str(Path(__file__).with_name("bash-output-scrub.sh"))],
            input=json.dumps({"tool_response": response}), text=True,
            capture_output=True, timeout=3,
        )
        assert result.returncode == 2 and result.stdout == "", result
    with tempfile.TemporaryDirectory() as directory:
        Path(directory, "python3").write_text("#!/bin/sh\nexit 1\n")
        Path(directory, "python3").chmod(0o755)
        result = subprocess.run(
            ["bash", str(Path(__file__).with_name("bash-output-scrub.sh"))],
            input=json.dumps({"tool_response": {"stdout": "", "stderr": ""}}),
            env={**os.environ, "PATH": directory + os.pathsep + os.environ["PATH"]},
            text=True, capture_output=True, timeout=3,
        )
        assert result.returncode == 2 and result.stdout == "", result
    assert run_hook("ordinary output") == ""
    assert run_hook("version abc.def.ghi") == ""
    assert run_hook("task-abcdefghijklmnopqrstuvwxyz") == ""
    assert run_hook("eyJ" * 100000) == ""
    header = base64.urlsafe_b64encode(b'{\n "alg":"HS256","typ":"JWT"}').decode().rstrip('=')
    token = header + '.e30.' + 'Z' * 43
    assert token not in run_hook(token)
    assert json.loads(run_hook(token))["decision"] == "block"
    with tempfile.TemporaryDirectory() as directory:
        Path(directory, "json.py").write_text("import sys\nprint(sys.stdin.read())\nraise SystemExit(0)\n")
        token = "sk-" + "Z" * 40
        result = subprocess.run(
            ["bash", str(Path(__file__).with_name("bash-output-scrub.sh"))],
            input=json.dumps({"tool_response": {"stdout": token, "stderr": ""}}),
            env={**os.environ, "PYTHONPATH": directory}, text=True,
            capture_output=True, check=True, timeout=3,
        )
        assert token not in result.stdout
        assert json.loads(result.stdout)["decision"] == "block"
    for prefix in ("sk-", "pk-"):
        token = prefix + "A" * 40
        output = run_hook(token)
        assert json.loads(output)["decision"] == "block"
        assert token not in output
    output = run_hook("x" * 1000000 + "ghp_" + "A" * 36)
    assert json.loads(output)["decision"] == "block"
    assert run_hook("token" * 200000) == ""
    assert run_hook("\x1b[32mok\x1b[0m") == ""
    siblings = ("Zsecret/Access+Key0", "ZsessionToken+/=")
    for short in ("password=hunter2", "password=getToken()hunter2", 'password=getToken()"hunter2"', "PASSWORD='x'\"hunter2\"", "password=hunter2(2)", "password=[REDACTED_VALUE]hunter2",
                  "\x1b[01;31m\x1b[Kpassword\x1b[m\x1b[K=" + "a" * 32 + "hunter2"):
        output = run_hook(short)
        assert json.loads(output)["decision"] == "block" and "hunter2" not in output, output
    pem_body = ("MIIEvQIBADANBgkqhkiG9w0BAQEFAASC", "Zq9LeakPemLine+/==")
    pem = "-----BEGIN PRIVATE KEY-----\n" + "\n".join(pem_body) + "\n-----END PRIVATE KEY-----"
    for pem_output in (f"PRIVATE_KEY='{pem}'", f"PRIVATE_KEY={pem}", pem):
        output = run_hook(pem_output + "\nnext")
        assert json.loads(output)["decision"] == "block"
        assert not any(line in output for line in pem_body) and "next" in output, output
    output = run_hook("private_key: |\n  " + pem.replace("\n", "\n  ") + "\nnext")
    assert json.loads(output)["decision"] == "block"
    assert not any(line in output for line in pem_body) and "next" not in output
    output = run_hook('Missing token: "abc\nrow 1\nrow 2')
    assert "row 2" in json.loads(output)["reason"], output
    for minified in ('{"token":"abc","user":"bob"}', '{"token":abc,"user":"bob"}', "{'token':abc,'user':'bob'}"):
        output = run_hook(minified)
        assert "abc" not in output and "user" in output and "bob" in output, output
    sts = json.dumps({"Credentials": {"AccessKeyId": "ASIA" + "Z" * 16, "SecretAccessKey": siblings[0], "SessionToken": siblings[1]}})
    for source in ("const token = getToken();", "if secret_ref == other:", "a=" * 20000 + "(", "k=v&" * 10000 + "[", "token=f();" * 100000, "-----BEGIN A" * 100000, "-----BEGIN " + "PRIVATE KEY " * 83000):
        assert run_hook(source) == "", source
    nested = json.dumps({"SecretString": json.dumps({"password": siblings[0]})})
    for credential_output in (sts, nested, '{"password": "x\\"' + siblings[0] + '"}', f"AWS_SECRET_ACCESS_KEY={siblings[0]}\npassword: '{siblings[1]}'", f"password={siblings[0]},{siblings[1]}", *(f"a=x,password=ab{c}{siblings[0]}" for c in ":=&<(;")):
        output = run_hook(credential_output)
        assert json.loads(output)["decision"] == "block"
        assert not any(sibling in output for sibling in siblings), output
    for credential in ("sk-" + "Z" * 40, "ghp_" + "Z" * 36, "ASIA" + "Z" * 16, "eyJhbGciOiJIUzI1NiJ9.e30." + "Z" * 43):
        for styled in ("\x1b[1;31m" + credential[:3] + "\x1b[0m" + credential[3:], credential[:3] + "\x1b(B\x1b[m" + credential[3:]):
            output = run_hook(styled)
            assert json.loads(output)["decision"] == "block"
            assert credential[3:] not in output, output
        for hidden in ("\x1b]0;x\n" + credential, "\x1b" + credential, "\x1b[" + credential, "\x1bPq\n" + credential[:3] + "\x1b[1m" + credential[3:]):
            output = run_hook(hidden)
            assert json.loads(output)["decision"] == "block", repr(hidden)
            assert credential[4:] not in output, output
    for channel in ("stdout", "stderr"):
        token = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=") + ".e30." + "Z" * 43
        output = run_hook(**{channel: "prefix." + token, **({"stdout": ""} if channel == "stderr" else {})})
        assert json.loads(output)["decision"] == "block"
        assert token not in output
        for credential in ("ASIA" + "Z" * 16, "eyJhbGciOiJIUzI1NiJ9.e30." + "Z" * 43):
            output = run_hook(**{channel: credential, **({"stdout": ""} if channel == "stderr" else {})})
            assert json.loads(output)["decision"] == "block"
            assert credential not in output
        for prefix in ("ghp_", "ghs_", "gho_", "ghu_", "ghr_", "github_pat_"):
            fake_token = prefix + "Z" * 36
            output = run_hook(**{channel: fake_token, **({"stdout": ""} if channel == "stderr" else {})})
            result = json.loads(output)
            assert result["decision"] == "block", result
            assert set(result) == {"decision", "reason"}, result
            assert fake_token not in output
            assert "[REDACTED_GH_TOKEN]" in result["reason"]
    print("PASS: ordinary output, stdout/stderr redaction, Codex block contract")
