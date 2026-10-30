#!/usr/bin/env ruby
# frozen_string_literal: true

require "fileutils"
require "json"
require "open3"
require "tmpdir"

SCRIPT = File.expand_path("list-skills", __dir__)

def assert(condition, message)
  raise message unless condition
end

def write_skill(dir, front_matter)
  FileUtils.mkdir_p(dir)
  File.write(File.join(dir, "SKILL.md"), "---\n#{front_matter}\n---\n\n# Body\n")
end

def row_for(html, name)
  html[%r{<tr><td>#{Regexp.escape(name)}</td>.*?</tr>}]
end

Dir.mktmpdir do |tmp|
  root = File.join(tmp, "devkit")
  home = File.join(tmp, "home")
  run = ->(*args) { Open3.capture2e({ "HOME" => home }, "git", "-C", root, *args) }

  write_skill(File.join(root, "skills", "owned"), "name: owned\ndescription: Ours.\nmetadata:\n  version: \"0.1.0\"")
  FileUtils.mkdir_p(root)
  run.call("init", "-q")
  run.call("remote", "add", "origin", "git@github.com:Owner/Repo.git")
  run.call("add", "skills")
  run.call("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "init")

  write_skill(File.join(root, "skills", "copied"), "name: copied\ndescription: >-\n  Folded\n  text.")
  write_skill(File.join(root, "skills", "tweaked"), "name: tweaked\ndescription: Changed copy.")
  write_skill(File.join(root, "skills", "declared"), "name: declared\ndescription: d\nmetadata:\n  version: \"2.0.0\"")
  write_skill(File.join(root, "skills", "released"), "name: released\ndescription: r\nmetadata:\n  version: \"34\"")
  write_skill(File.join(root, "skills", "editor"), "name: editor\ndescription: Built in.")
  write_skill(File.join(root, "skills", "editor2"), "name: editor2\ndescription: Older built in.")
  write_skill(File.join(root, "skills", "broken"), "description: has: colon")
  write_skill(File.join(root, "skills", "mystery"), "name: mystery\ndescription: \"<script>alert(1)</script>\"")
  write_skill(File.join(root, "skills", "synced", "account", "syncme"), "name: syncme\ndescription: From claude.ai.")
  File.write(File.join(root, "skills.lock.json"), JSON.generate(
    "skills" => {
      "owned" => { "source" => "https://github.com/up/owned.git", "modified" => true },
      "copied" => { "source" => "https://github.com/up/stream.git", "ref" => "abcdef1234567", "date" => "2026-01-02" },
      "tweaked" => { "source" => "https://github.com/up/stream.git", "modified" => true },
      "declared" => { "source" => "https://github.com/up/stream.git", "ref" => "abcdef1234567" },
      "released" => { "source" => "https://github.com/up/rel.git", "version" => "6.3.0" },
      "editor" => { "source" => "cursor", "version" => "3.25.6" },
      "editor2" => { "source" => "cursor", "modified" => true },
    },
  ))

  plugin_dir = File.join(home, "plugin-cache", "plug")
  write_skill(File.join(plugin_dir, "skills", "pskill"), "name: pskill\ndescription: Plugin skill.")
  write_skill(File.join(plugin_dir, "skills", "engineering", "tdd"), "name: tdd\ndescription: Listed in plugin.json.")
  FileUtils.mkdir_p(File.join(plugin_dir, ".claude-plugin"))
  File.write(File.join(plugin_dir, ".claude-plugin", "plugin.json"), JSON.generate("skills" => ["./skills/engineering/tdd"]))
  inner_dir = File.join(home, "plugin-cache", "inner")
  write_skill(File.join(inner_dir, "skills", "iskill"), "name: iskill\ndescription: Inside the marketplace.")
  plugins = File.join(home, ".claude", "plugins")
  FileUtils.mkdir_p(File.join(plugins, "marketplaces", "mkt", ".claude-plugin"))
  File.write(File.join(plugins, "installed_plugins.json"), JSON.generate(
    "plugins" => {
      "plug@mkt" => [{ "scope" => "user", "installPath" => plugin_dir, "version" => "1.0.6" }],
      "inner@mkt" => { "installPath" => inner_dir, "version" => "0.2.0" },
    },
  ))
  File.write(File.join(plugins, "known_marketplaces.json"), JSON.generate(
    "mkt" => { "source" => { "source" => "github", "repo" => "o/plugins" } },
  ))
  File.write(File.join(plugins, "marketplaces", "mkt", ".claude-plugin", "marketplace.json"), JSON.generate(
    "plugins" => [
      { "name" => "plug", "source" => { "source" => "url", "url" => "https://github.com/own/plug.git" } },
      { "name" => "inner", "source" => "./plugins/inner" },
    ],
  ))

  out = File.join(tmp, "skills.html")
  output, status = Open3.capture2e({ "HOME" => home }, "ruby", SCRIPT, "--root", root, "--out", out, "--no-open")
  assert(status.success?, "list-skills failed: #{output}")
  assert(output.include?("no readable front matter in #{File.join(root, "skills", "broken", "SKILL.md")}"), "bad front matter not reported: #{output}")
  html = File.read(out, encoding: "UTF-8")

  owned = row_for(html, "owned")
  assert(owned&.include?("<td>DevKit</td>"), "tracked skill is not DevKit: #{owned}")
  assert(owned.include?(%(href="https://github.com/Owner/Repo")), "DevKit row lacks the origin remote: #{owned}")
  assert(owned.match?(/<td>0\.1\.0, \h{7} \(\d{4}-\d\d-\d\d\)<\/td>/), "DevKit row lacks version and last commit: #{owned}")
  assert(owned.include?("copied from https://github.com/up/owned, changed since"), "DevKit row hides its upstream: #{owned}")

  copied = row_for(html, "copied")
  assert(copied&.include?("<td>Copied from a repo</td>"), "copied skill origin: #{copied}")
  assert(copied.include?("<td>abcdef1 (2026-01-02)</td>"), "copied skill version: #{copied}")
  assert(copied.include?("Folded text."), "folded description not parsed: #{copied}")

  tweaked = row_for(html, "tweaked")
  assert(tweaked&.include?("changed since it was copied"), "modified copy not flagged: #{tweaked}")
  assert(row_for(html, "declared")&.include?("<td>2.0.0, abcdef1</td>"), "declared version and pin not both shown")
  assert(row_for(html, "released")&.include?("<td>6.3.0</td>"), "recorded release version not preferred")
  assert(row_for(html, "editor2")&.include?("differs from the current built-in copy"), "changed built-in not flagged")
  assert(row_for(html, "broken")&.include?("<td>Unknown</td>"), "skill with bad front matter dropped")
  assert(row_for(html, "editor")&.include?("<td>Cursor built-in</td><td></td><td>3.25.6</td>"), "built-in row wrong")

  mystery = row_for(html, "mystery")
  assert(mystery&.include?("<td>Unknown</td>"), "unrecorded skill is not Unknown: #{mystery}")
  assert(!html.include?("<script>alert(1)"), "description was not escaped")

  assert(row_for(html, "syncme")&.include?("<td>Claude.ai synced</td>"), "synced skill missing")
  plugin = row_for(html, "plug:pskill")
  assert(plugin&.include?("<td>1.0.6</td>") && plugin.include?(%(href="https://github.com/own/plug")), "plugin row wrong: #{plugin}")
  assert(row_for(html, "plug:tdd"), "plugin.json skill path not listed")
  inner = row_for(html, "inner:iskill")
  assert(inner&.include?(%(href="https://github.com/o/plugins")) && inner.include?("<td>0.2.0</td>"), "older plugin format or marketplace fallback wrong: #{inner}")
  assert(html.include?("<h1>Skills (13)</h1>"), "row count wrong")

  File.write(File.join(plugins, "installed_plugins.json"), "{not json")
  output, status = Open3.capture2e({ "HOME" => home }, "ruby", SCRIPT, "--root", root, "--out", out, "--no-open")
  assert(status.success? && output.include?("skipping unreadable"), "broken plugin file crashed the page: #{output}")
  assert(File.read(out, encoding: "UTF-8").include?("<h1>Skills (10)</h1>"), "repo skills lost when plugin file is broken")
end

puts "list-skills tests passed"
