# Changelog

## 1.1.0 — 2026-10-05

- `rgb-theme off` restores the state from before the first `on` instead of switching to
  Bibata-Modern-Ice: the first `on` saves the files (and whether they existed), the gsettings
  value (and whether it was set) and the session environment in `~/.local/state/bibata-rgb/`.
  Files edited by hand in between keep those edits; only the cursor theme line goes back, and
  gsettings and the environment go back only where they still say Bibata-RGB. An interrupted
  `on` is finished by the next `on` or undone by `off`; a stale snapshot (the look undone
  another way) is dropped; runs are serialised with a lock. A look switched on by 1.0 has no
  saved state, so its `off` still switches to Bibata-Modern-Ice.
- `rgb-theme speed cursor <s>` (seconds per rainbow cycle, 0.3–20) and
  `rgb-theme speed borders <s>` (seconds per turn, 0.3–10). The cursor speed rewrites the frame
  delays of the installed theme, so it needs no rebuild (the busy spinner turns with it).
  `generate.py --cycle-ms` sets it for a first install or a hand-made archive. `install.sh`
  keeps both speeds and the spin mode on reinstall.
- `generate.py` checks that its source is exactly Bibata-Modern-Ice v2.0.6 (manifest name and
  version, checksum of the `vendor/Bibata-Modern-Ice` tree, 56 shapes and 145 names) and that
  every recolouring rule matches in every frame and every XCursor alias resolves, and stops
  with a list of problems otherwise. `--no-verify` skips the name, version, checksum and count
  checks.
- XCursor variants: `./install.sh --lite` (24–64 px, ~54 MB, default) and `--full` (16–96 px
  like the original, ~235 MB); `generate.py --xcursor lite|full`.
- The built theme carries `BUILD-INFO` (version, source, XCursor variant, cycle length).
- `rgb-theme version`.

## 1.0.0 — 2026-10-05

First release.
