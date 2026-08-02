# Connect Front-End and Back-End Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Feed the static GitHub Pages site with real Supabase data via a build-time Python export run inside the Pages deploy workflow.

**Architecture:** A new `bot/export.py` reuses the bot's `supabase-py` client to fetch `tournaments` + `round_results`, and a pure `build_site_data()` reshapes the player-centric rows into the front-end's pairing-centric JSON. The Pages workflow runs the export before deploying (after `ingest`, on dispatch, or on `web/**` push); the JSON is generated into the artifact and never committed. The front-end fetches `data/tournaments.json` (a committed seed keeps local dev working).

**Tech Stack:** Python 3.11 + `supabase-py` (existing bot deps), pytest, GitHub Actions Pages, vanilla JS front-end (unchanged except its data path).

---

## File Structure

- `bot/export.py` — `build_site_data(tournaments, results)` (pure), `_fetch(client)`, `export_to_file(client, out)`, `main(argv)`
- `tests/test_export.py` — pytest for the pure reshape + the file-writing wiring
- `web/app.js` — one line changes (data source path)
- `web/data/tournaments.json` — renamed from `mock-tournaments.json` (committed seed)
- `tests/web/seed-data.test.mjs` — asserts the committed seed matches the front-end shape
- `.github/workflows/pages.yml` — add triggers + Python export step
- `.github/workflows/bot-ci.yml` — new: runs `pytest`

**Environment notes for the executor:**
- Python: use the worktree venv — commands below use `.venv/Scripts/python.exe`.
- Node (for the one `node --test` step): not on PATH; prepend it in that Bash command:
  `export PATH="$PATH:/c/Users/Aleksejs/AppData/Local/Microsoft/WinGet/Packages/OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe/node-v24.18.1-win-x64"`
- Git identity is configured in this repo. LF/CRLF warnings are harmless.

---

## Task 1: Environment setup

**Files:** none (tooling only)

- [ ] **Step 1: Create the venv and install the package (dev extras)**

Run (Bash, from the worktree root):
```bash
python -m venv .venv && .venv/Scripts/python.exe -m pip install -e ".[dev]"
```
Expected: installs httpx, supabase, tzdata, pytest with no errors.

- [ ] **Step 2: Confirm the existing test suite passes (baseline)**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: all existing tests pass (0 failures).

- [ ] **Step 3: No commit** (nothing changed in the repo; `.venv/` is gitignored).

---

## Task 2: Pure reshape — `build_site_data`

**Files:**
- Create: `bot/export.py`
- Test: `tests/test_export.py`

- [ ] **Step 1: Write the failing test**

`tests/test_export.py`:
```python
from bot.export import build_site_data


def res(tid, rnd, pr, name, key, gw, w, d, l):
    return {
        "tournament_id": tid, "round": rnd, "pairing": pr,
        "player_name": name, "player_key": key, "game_wins": gw,
        "record_wins": w, "record_draws": d, "record_losses": l,
    }


def test_full_pairing_two_rows():
    tournaments = [{"id": 1, "name": "A", "event_date": "2026-07-06"}]
    results = [res(1, 1, 1, "Ann", "ann", 2, 1, 0, 0),
               res(1, 1, 1, "Bob", "bob", 1, 0, 0, 1)]
    data = build_site_data(tournaments, results)
    t = data["tournaments"][0]
    assert t["id"] == "1"
    assert t["date"] == "2026-07-06"
    p = t["rounds"][0]["pairings"][0]
    assert p["pairing"] == 1
    assert p["player1"] == {"name": "Ann", "game_wins": 2, "record": {"wins": 1, "draws": 0, "losses": 0}}
    assert p["player2"] == {"name": "Bob", "game_wins": 1, "record": {"wins": 0, "draws": 0, "losses": 1}}


def test_bye_single_row():
    tournaments = [{"id": 1, "name": "A", "event_date": "2026-07-06"}]
    results = [res(1, 1, 1, "Cara", "cara", 2, 1, 0, 0)]
    data = build_site_data(tournaments, results)
    p = data["tournaments"][0]["rounds"][0]["pairings"][0]
    assert p["player1"]["name"] == "Cara"
    assert p["player2"] is None


def test_deterministic_player1_by_key():
    tournaments = [{"id": 1, "name": "A", "event_date": "2026-07-06"}]
    results = [res(1, 1, 1, "Bob", "bob", 1, 0, 0, 1),
               res(1, 1, 1, "Ann", "ann", 2, 1, 0, 0)]
    data = build_site_data(tournaments, results)
    p = data["tournaments"][0]["rounds"][0]["pairings"][0]
    assert p["player1"]["name"] == "Ann"
    assert p["player2"]["name"] == "Bob"


def test_ordering_and_grouping():
    tournaments = [{"id": 2, "name": "Later", "event_date": "2026-08-01"},
                   {"id": 1, "name": "Earlier", "event_date": "2026-07-06"}]
    results = [
        res(1, 2, 1, "Ann", "ann", 2, 2, 0, 0), res(1, 2, 1, "Bob", "bob", 1, 1, 0, 1),
        res(1, 1, 1, "Ann", "ann", 2, 1, 0, 0), res(1, 1, 1, "Bob", "bob", 1, 0, 0, 1),
        res(2, 1, 1, "Ann", "ann", 2, 1, 0, 0), res(2, 1, 1, "Zed", "zed", 0, 0, 0, 1),
    ]
    data = build_site_data(tournaments, results)
    assert [t["name"] for t in data["tournaments"]] == ["Earlier", "Later"]
    assert [r["round"] for r in data["tournaments"][0]["rounds"]] == [1, 2]


def test_null_name_fallback():
    tournaments = [{"id": 1, "name": None, "event_date": "2026-07-06"}]
    results = [res(1, 1, 1, "Ann", "ann", 2, 1, 0, 0)]
    data = build_site_data(tournaments, results)
    assert data["tournaments"][0]["name"] == "Tournament"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_export.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bot.export'`

- [ ] **Step 3: Write minimal implementation**

`bot/export.py`:
```python
from __future__ import annotations

from collections import defaultdict


def _player_obj(row: dict) -> dict:
    return {
        "name": row["player_name"],
        "game_wins": row["game_wins"],
        "record": {
            "wins": row["record_wins"],
            "draws": row["record_draws"],
            "losses": row["record_losses"],
        },
    }


def build_site_data(tournaments: list[dict], results: list[dict]) -> dict:
    grouped: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for row in results:
        grouped[row["tournament_id"]][row["round"]][row["pairing"]].append(row)

    out_tournaments = []
    for t in sorted(tournaments, key=lambda t: t["event_date"]):
        rounds_map = grouped.get(t["id"], {})
        rounds_out = []
        for round_no in sorted(rounds_map):
            pairings_out = []
            for pairing_no in sorted(rounds_map[round_no]):
                rows = sorted(
                    rounds_map[round_no][pairing_no],
                    key=lambda r: r["player_key"],
                )
                pairings_out.append(
                    {
                        "pairing": pairing_no,
                        "player1": _player_obj(rows[0]),
                        "player2": _player_obj(rows[1]) if len(rows) > 1 else None,
                    }
                )
            rounds_out.append({"round": round_no, "pairings": pairings_out})
        out_tournaments.append(
            {
                "id": str(t["id"]),
                "name": t["name"] or "Tournament",
                "date": t["event_date"],
                "rounds": rounds_out,
            }
        )
    return {"tournaments": out_tournaments}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_export.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add bot/export.py tests/test_export.py
git commit -m "feat(export): add pure round_results -> site JSON reshape"
```

---

## Task 3: Fetch + write — `export_to_file` and `main`

**Files:**
- Modify: `bot/export.py`
- Test: `tests/test_export.py`

- [ ] **Step 1: Write the failing test (append to `tests/test_export.py`)**

```python
import json
import pytest
from bot.export import export_to_file, main


class _FakeQuery:
    def __init__(self, data):
        self._data = data

    def select(self, *_cols):
        return self

    def execute(self):
        return type("R", (), {"data": self._data})


class _FakeClient:
    def __init__(self, tournaments, results):
        self._tables = {"tournaments": tournaments, "round_results": results}

    def table(self, name):
        return _FakeQuery(self._tables[name])


def test_export_to_file_writes_expected_json(tmp_path):
    tournaments = [{"id": 1, "name": "A", "event_date": "2026-07-06"}]
    results = [res(1, 1, 1, "Ann", "ann", 2, 1, 0, 0),
               res(1, 1, 1, "Bob", "bob", 1, 0, 0, 1)]
    out = tmp_path / "tournaments.json"
    count = export_to_file(_FakeClient(tournaments, results), str(out))
    assert count == 1
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["tournaments"][0]["rounds"][0]["pairings"][0]["player1"]["name"] == "Ann"


def test_export_to_file_preserves_unicode(tmp_path):
    tournaments = [{"id": 1, "name": None, "event_date": "2026-07-06"}]
    results = [res(1, 1, 1, "Mārtiņš", "mārtiņš", 2, 1, 0, 0)]
    out = tmp_path / "t.json"
    export_to_file(_FakeClient(tournaments, results), str(out))
    assert "Mārtiņš" in out.read_text(encoding="utf-8")


def test_main_requires_env(monkeypatch, tmp_path):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    with pytest.raises(SystemExit):
        main(["--out", str(tmp_path / "x.json")])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_export.py -k "export_to_file or main" -v`
Expected: FAIL — `ImportError: cannot import name 'export_to_file'`

- [ ] **Step 3: Write minimal implementation (append to `bot/export.py`)**

```python
import argparse
import json
import os
import sys

_TOURNAMENT_COLS = "id, name, event_date"
_RESULT_COLS = (
    "tournament_id, round, pairing, player_name, player_key, "
    "game_wins, record_wins, record_draws, record_losses"
)


def _fetch(client) -> tuple[list[dict], list[dict]]:
    tournaments = client.table("tournaments").select(_TOURNAMENT_COLS).execute().data
    results = client.table("round_results").select(_RESULT_COLS).execute().data
    return tournaments, results


def export_to_file(client, out_path: str) -> int:
    tournaments, results = _fetch(client)
    data = build_site_data(tournaments, results)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    return len(data["tournaments"])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="bot.export")
    parser.add_argument("--out", default="web/data/tournaments.json")
    args = parser.parse_args(argv)

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("SUPABASE_URL and SUPABASE_KEY must be set", file=sys.stderr)
        raise SystemExit(1)

    from supabase import create_client

    count = export_to_file(create_client(url, key), args.out)
    print(f"Wrote {count} tournaments to {args.out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_export.py -v`
Expected: PASS (8 tests total)

- [ ] **Step 5: Commit**

```bash
git add bot/export.py tests/test_export.py
git commit -m "feat(export): add supabase fetch and file writer with CLI"
```

---

## Task 4: Point the front-end at the exported data

**Files:**
- Rename: `web/data/mock-tournaments.json` → `web/data/tournaments.json`
- Modify: `web/app.js`
- Test: `tests/web/seed-data.test.mjs`

- [ ] **Step 1: Rename the seed data file (preserve git history)**

Run: `git mv web/data/mock-tournaments.json web/data/tournaments.json`

- [ ] **Step 2: Update the fetch path in `web/app.js`**

Change the line:
```js
    const response = await fetch('data/mock-tournaments.json');
```
to:
```js
    const response = await fetch('data/tournaments.json');
```

- [ ] **Step 3: Write a seed-shape test**

`tests/web/seed-data.test.mjs`:
```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const data = JSON.parse(
  readFileSync(new URL('../../web/data/tournaments.json', import.meta.url), 'utf-8'),
);

test('committed seed data matches the front-end shape', () => {
  assert.ok(Array.isArray(data.tournaments) && data.tournaments.length > 0);
  const t = data.tournaments[0];
  for (const key of ['id', 'name', 'date', 'rounds']) {
    assert.ok(key in t, `tournament missing ${key}`);
  }
  const pairing = t.rounds[0].pairings[0];
  assert.ok('pairing' in pairing && 'player1' in pairing && 'player2' in pairing);
  const p1 = pairing.player1;
  assert.ok('name' in p1 && 'game_wins' in p1 && 'record' in p1);
});
```

- [ ] **Step 4: Run the web suite (prepend node to PATH first)**

Run:
```bash
export PATH="$PATH:/c/Users/Aleksejs/AppData/Local/Microsoft/WinGet/Packages/OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe/node-v24.18.1-win-x64"
node --check web/app.js && node --test tests/web/*.test.mjs
```
Expected: `node --check` clean; all web tests pass (now including `seed-data.test.mjs`).

- [ ] **Step 5: Commit**

```bash
git add web/app.js web/data/tournaments.json tests/web/seed-data.test.mjs
git commit -m "feat(web): read data/tournaments.json and add seed-shape test"
```

---

## Task 5: Wire the export into the Pages workflow

**Files:**
- Modify: `.github/workflows/pages.yml`

- [ ] **Step 1: Replace `.github/workflows/pages.yml` with:**

```yaml
name: pages
on:
  workflow_run:
    workflows: ["ingest"]
    types: [completed]
  workflow_dispatch:
  push:
    branches: [main]
    paths:
      - "web/**"
      - "bot/export.py"
      - ".github/workflows/pages.yml"

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  deploy:
    if: ${{ github.event_name != 'workflow_run' || github.event.workflow_run.conclusion == 'success' }}
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e .
      - run: python -m bot.export --out web/data/tournaments.json
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: web
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Validate the YAML parses**

Run: `.venv/Scripts/python.exe -c "import yaml; yaml.safe_load(open('.github/workflows/pages.yml')); print('ok')"`
Expected: prints `ok`. (If PyYAML is missing, install it first: `.venv/Scripts/python.exe -m pip install pyyaml`.)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/pages.yml
git commit -m "ci(pages): generate data from supabase before deploy"
```

---

## Task 6: Python CI for the export tests

**Files:**
- Create: `.github/workflows/bot-ci.yml`

- [ ] **Step 1: Create `.github/workflows/bot-ci.yml`**

```yaml
name: bot-ci
on:
  push:
    paths:
      - "bot/**"
      - "tests/**"
      - "pyproject.toml"
      - ".github/workflows/bot-ci.yml"
  pull_request:
    paths:
      - "bot/**"
      - "tests/**"
      - "pyproject.toml"
      - ".github/workflows/bot-ci.yml"
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: pytest -q
```

- [ ] **Step 2: Validate the YAML parses**

Run: `.venv/Scripts/python.exe -c "import yaml; yaml.safe_load(open('.github/workflows/bot-ci.yml')); print('ok')"`
Expected: prints `ok`.

- [ ] **Step 3: Final full local check**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: all Python tests pass (including `tests/test_export.py`).

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/bot-ci.yml
git commit -m "ci: run pytest for the bot package"
```

---

## Notes for delivery

- Delivered as a **pull request** from this worktree/branch (`connect-frontend-backend`).
- The `pages` deploy needs the `SUPABASE_URL` / `SUPABASE_KEY` repository secrets to be set (the bot's secrets). If they are not yet configured, the deploy step will fail with a clear message — note this in the PR description.

---

## Self-Review Notes

- **Spec coverage:** real data via build-time export (Tasks 2,3,5), pure reshape with byes + deterministic player1 (Task 2), server-side-only Supabase access (Task 3 + workflow env, Task 5), reuse of existing service_role secrets (Task 5), trigger after `ingest` + dispatch + `web/**` push (Task 5), front-end single-path change + committed seed + no leftover mock file (Task 4), local dev unaffected (seed served as before), pytest coverage incl. bye/null-name/unicode/ordering (Tasks 2,3), CI runs pytest (Task 6), seed-shape sanity test (Task 4), fail-closed on missing secrets/errors (Task 3 `main` + workflow). All spec sections map to tasks.
- **Placeholder scan:** none; every code step contains complete content.
- **Type consistency:** `build_site_data(tournaments, results)` output keys (`id`,`name`,`date`,`rounds[].round`,`pairings[].{pairing,player1,player2}`, `player.{name,game_wins,record.{wins,draws,losses}}`) match the front-end seed test (Task 4) and the front-end renderers. `_fetch`/`export_to_file`/`main` signatures are consistent across Task 3 and the workflow's `python -m bot.export --out …`. The `res(...)` test helper defined in Task 2 is reused by Task 3's appended tests (same file).
