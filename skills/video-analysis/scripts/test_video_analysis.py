#!/usr/bin/env python3
"""Offline tests for the video-analysis scripts. Run: python3 skills/video-analysis/scripts/test_video_analysis.py"""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


fetch = load("fetch_transcript")
render = load("render_report")

META = {"id": "abc", "title": "T", "url": "https://www.youtube.com/watch?v=abc", "site": "Youtube",
        "duration_seconds": 600, "caption_kind": "auto", "caption_language": "en-orig"}


def analysis(**overrides) -> dict:
    base = {
        "tldr": "What it is.", "subject": "Subject.",
        "summary": [{"t": "1:05", "text": "Moment"}],
        "themes": [{"name": "Theme", "why": "Why"}],
        "actions": [{"action": "Do it", "area": "Home Assistant", "effort": "1 hour", "when": "now"}],
        "tutorial": None, "not_tutorial": "A talk, not a walkthrough.",
    }
    base.update(overrides)
    return base


class ChooseTrack(unittest.TestCase):
    def test_creator_captions_win_over_auto(self):
        info = {"subtitles": {"en-GB": [{}]}, "automatic_captions": {"en-orig": [{}], "en": [{}]}}
        self.assertEqual(fetch.choose_track(info, "en"), ("creator", "en-GB"))

    def test_auto_prefers_original_over_translation(self):
        info = {"subtitles": {"live_chat": [{}]}, "automatic_captions": {"en": [{}], "en-orig": [{}]}}
        self.assertEqual(fetch.choose_track(info, "en"), ("auto", "en-orig"))

    def test_falls_back_to_other_language_creator_track(self):
        info = {"subtitles": {"de": [{}]}, "automatic_captions": {}}
        self.assertEqual(fetch.choose_track(info, "en"), ("creator", "de"))

    def test_vimeo_autogen_is_auto_but_downloaded_from_subtitles(self):
        info = {"subtitles": {"en-x-autogen": [{"ext": "vtt"}]}, "automatic_captions": {}}
        self.assertEqual(fetch.choose_track(info, "en"), ("auto", "en-x-autogen"))
        self.assertEqual(fetch.collection(info, "auto", "en-x-autogen"), "subtitles")
        self.assertEqual(fetch.choose_format(info, "auto", "en-x-autogen"), "vtt")

    def test_other_language_vimeo_autogen_is_used(self):
        info = {"subtitles": {"de-x-autogen": [{"ext": "vtt"}]}, "automatic_captions": {}}
        self.assertEqual(fetch.choose_track(info, "en"), ("auto", "de-x-autogen"))

    def test_none_when_no_captions(self):
        self.assertIsNone(fetch.choose_track({"subtitles": {}, "automatic_captions": {}}, "en"))


class Parsing(unittest.TestCase):
    def test_json3_skips_empty_events(self):
        raw = json.dumps({"events": [
            {"tStartMs": 0, "segs": [{"utf8": "hello "}, {"utf8": "world"}]},
            {"tStartMs": 1500, "segs": [{"utf8": "\n"}]},
            {"tStartMs": 61000, "segs": [{"utf8": "later"}]},
        ]})
        self.assertEqual(fetch.parse_json3(raw), [(0.0, "hello world"), (61.0, "later")])

    def test_vtt_drops_rolling_duplicates_and_tags(self):
        raw = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nfirst <c>line</c>\n\n00:00:03.000 --> 00:00:05.000\nfirst line\nsecond line\n"
        self.assertEqual(fetch.parse_cues(raw), [(1.0, "first line"), (3.0, "second line")])

    def test_same_words_in_separate_cues_are_kept(self):
        raw = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nPress Enter\n\n00:01:30.000 --> 00:01:31.000\nPress Enter\n"
        self.assertEqual(fetch.parse_cues(raw), [(1.0, "Press Enter"), (90.0, "Press Enter")])

    def test_auto_captions_keep_adjacent_single_line_repeats(self):
        raw = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nPress Enter\n\n00:00:02.000 --> 00:00:03.000\nPress Enter\n"
        self.assertEqual(len(fetch.parse_cues(raw, rolling_captions=True)), 2)

    def test_creator_captions_keep_adjacent_repeats(self):
        raw = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nPress Enter\n\n00:00:02.000 --> 00:00:03.000\nPress Enter\n"
        self.assertEqual(len(fetch.parse_cues(raw, rolling_captions=False)), 2)

    def test_character_references_are_decoded(self):
        raw = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nx &lt; 5 &amp;&amp; ready\n"
        self.assertEqual(fetch.parse_cues(raw), [(1.0, "x < 5 && ready")])

    def test_srt_with_hours(self):
        raw = "1\n01:02:03,500 --> 01:02:05,000\nhi\n"
        self.assertEqual(fetch.parse_cues(raw), [(3723.5, "hi")])

    def test_merge_lines_windows(self):
        lines = fetch.merge_lines([(0, "a"), (5, "b"), (21, "c"), (3700, "d")])
        self.assertEqual(lines, ["[0:00] a b", "[0:21] c", "[1:01:40] d"])


class FolderName(unittest.TestCase):
    def test_same_title_different_videos_get_different_folders(self):
        self.assertNotEqual(fetch.folder_name("2026-10-20", "Same", "aaa"), fetch.folder_name("2026-10-20", "Same", "bbb"))

    def test_non_ascii_title_and_unsafe_id(self):
        self.assertEqual(fetch.folder_name("2026-10-20", "日本語", "a/b..c"), "2026-10-20-video-abc")


class Render(unittest.TestCase):
    def test_fractional_duration_renders(self):
        html = render.render({**META, "duration_seconds": 165.768}, analysis())
        self.assertIn("2:45", html)

    def test_escapes_untrusted_text(self):
        html = render.render(META, analysis(tldr="<script>alert(1)</script>"))
        self.assertNotIn("<script>alert(1)", html)
        self.assertIn("&lt;script&gt;alert(1)", html)

    def test_timestamp_links_jump_to_second(self):
        html = render.render(META, analysis())
        self.assertIn("watch?v=abc&amp;t=65s", html)

    def test_existing_timestamps_are_replaced(self):
        yt = render.time_link("https://www.youtube.com/watch?v=abc&t=10s", "Youtube", 65)
        vimeo = render.time_link("https://vimeo.com/123#t=1m", "Vimeo", 65)
        self.assertEqual((yt, vimeo), ("https://www.youtube.com/watch?v=abc&t=65s", "https://vimeo.com/123#t=65s"))

    def test_sites_without_seek_support_get_plain_timestamps(self):
        html = render.render({**META, "url": "https://www.ted.com/talks/x", "site": "TedTalk"}, analysis())
        self.assertIn('<span class="ts">1:05</span>', html)
        self.assertNotIn("ted.com/talks/x\" target", html.split("<h2>")[1])

    def test_non_http_url_is_not_linked(self):
        html = render.render({**META, "url": "javascript:alert(1)"}, analysis())
        self.assertNotIn("javascript:", html)

    def test_bad_when_names_the_field(self):
        bad = analysis(actions=[{"action": "x", "area": "y", "effort": "1 hour", "when": "soon"}])
        with self.assertRaisesRegex(render.AnalysisError, r"actions\[0\]\.when"):
            render.render(META, bad)

    def test_null_tutorial_requires_reason(self):
        with self.assertRaisesRegex(render.AnalysisError, "not_tutorial"):
            render.render(META, analysis(not_tutorial=""))

    def test_tutorial_steps_render_as_checklist_with_code(self):
        tutorial = {"goal": "G", "steps": [{"t": 10, "text": "Run it", "code": "brew install yt-dlp"}], "costs": []}
        html = render.render(META, analysis(tutorial=tutorial))
        self.assertIn('type="checkbox"', html)
        self.assertIn("brew install yt-dlp", html)
        self.assertIn("Nothing in the video needs an API key", html)

    def test_missing_cost_check_is_rejected(self):
        with self.assertRaisesRegex(render.AnalysisError, "tutorial.costs"):
            render.render(META, analysis(tutorial={"goal": "G", "steps": [{"text": "x"}]}))

    def test_other_tutorial_edits_keep_the_progress_key(self):
        def key(costs):
            html = render.render(META, analysis(tutorial={"goal": "G", "steps": [{"text": "a"}], "costs": costs}))
            return html.split('data-store-key="')[1].split('"')[0]
        self.assertEqual(key([]), key(["Needs a subscription"]))

    def test_unknown_caption_provenance_is_stated(self):
        html = render.render({**META, "caption_kind": "unknown"}, analysis())
        self.assertIn("does not say whether they are creator-made or auto-generated", html)

    def test_changed_steps_get_a_new_progress_key(self):
        def key(steps):
            html = render.render(META, analysis(tutorial={"goal": "G", "steps": steps, "costs": []}))
            return html.split('data-store-key="')[1].split('"')[0]
        self.assertNotEqual(key([{"text": "a"}]), key([{"text": "new"}, {"text": "a"}]))

    def test_rejects_bad_timestamp(self):
        with self.assertRaisesRegex(render.AnalysisError, r"summary\[0\]\.t"):
            render.render(META, analysis(summary=[{"t": "soon", "text": "x"}]))


if __name__ == "__main__":
    unittest.main()
