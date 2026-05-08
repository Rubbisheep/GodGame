# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

《无名之界》— a Chinese-language, LLM-driven command-line god simulator. The UI, prompts, narrative output, and most in-code comments are in Chinese; commands accept both Chinese and English input (see README for the full command table). LLM responses should stay Chinese — don't translate prompts or narrative text unless asked.

## Commands

```bash
pip install -r requirements.txt        # openai, python-dotenv, rich
cp .env.example .env                   # then fill in OPENROUTER_API_KEY
python main.py                         # auto-creates savegame.json on first run
```

No test suite, no lint config, no build step. To replay from genesis: delete `savegame.json` and everything in `modules/` except `__init__.py`.

## Core design: minimal kernel + emergent modules

The repo is architected around a hard split:

- **Hardcoded kernel** — only the minimum physics: world clock, people (birth/aging/death/prayer), the faith economy, player intervention channels, NPC autonomy, and the emergence engine itself. That's it.
- **Everything else is LLM-generated at runtime.** Mutations, myths, special individuals/prophets, other gods, trade, war, disease, rituals — none of these are built-in features. The emergence engine watches the event stream and, when it detects enough signal, asks Sonnet to write a Python module implementing the needed system, writes it to `modules/`, and hot-loads it.

This is the load-bearing constraint when deciding where new code goes: **if the concept is domain-specific world content, it belongs in an emergent module, not in the kernel.** The kernel has been actively trimmed to reinforce this (see commit `86eb816` — `mutation_tick`, `entity_tick`, `divinity_tick`, `llm/mutations.py`, `SpecialEntity`, `Mutation` were all removed for this reason). Don't re-add them in `core/` or `systems/`.

`llm/codegen.py::EMERGENCE_PALETTE` is the catalog the emergence prompt shows the LLM — categories like `mutation_system`, `prophet_system`, `trade_system`, `myth_system`, `other_deities`, etc. If you want to bias what emerges, edit that palette rather than hardcoding the system.

## Tick loop

Real time drives world time. `core/simulator.py::WorldSimulator` runs a daemon thread that sleeps `TICK_INTERVAL` (300s, i.e. 5 real-minutes = 1 world year), then calls `StateManager.end_of_turn()`. On startup, `calc_catchup_years()` reads `__last_tick_time__` from the save and fast-forwards up to `MAX_CATCHUP` (100) silent ticks for offline time. Autosave every 5 ticks.

All player input and all background ticks acquire `WorldSimulator.lock` (RLock). Never touch `state_manager` directly from `main.py` — route through:
- `sim.player_act(fn, ...)` — turn-consuming actions; runs `fn` then immediately `end_of_turn`
- `sim.player_query(fn, ...)` — read-only / non-turn actions (rendering, gaze, ask, talk)

`end_of_turn()` sequence: resource tick → iterate `SYSTEMS` → drain module upgrade/fix queues + run all modules' `on_turn_end` → meta-system emergence check every `CHECK_INTERVAL` (3) years.

### Adding a hardcoded tick system (rare — think twice)

Create `systems/foo_tick.py` with `def tick(sm) -> list[str]` and append it to `SYSTEMS` in `systems/__init__.py`. Order matters. The current list is intentionally minimal: `population_tick` (aging/birth/prayer generation) and `autonomy_tick` (LLM-driven NPC self-action). If you're tempted to add a third, ask first whether it should be an emergent module instead.

## LLM layer (quarantined in `llm/`)

Nothing outside `llm/` calls the API directly. `llm/client.py` owns the OpenRouter client, `.env` loading, `call()`, and `safe_json()` — the latter has truncation-repair heuristics, use it instead of raw `json.loads` when parsing LLM output. Two models: `MODEL` (`claude-haiku-4-5`) for gameplay narration, `MODEL_CODE` (`claude-sonnet-4-5`) for code generation, repair, and upgrades. `USE_MOCK = False` gates offline-dev fallbacks. `llm/bible.py` holds the world-setting prompt prepended to narrative calls; `llm/schemas.py` holds the JSON schema descriptors referenced by each call.

## Self-writing modules (`evolution/` + `modules/`)

Every `CHECK_INTERVAL = 3` world years, `MetaSystem.check_and_generate()` asks the LLM whether a new system has emerged based on recent events + the EMERGENCE_PALETTE. If yes, `llm.generate_module_code()` produces source, `ModuleLoader.load()` writes it to `modules/<name>.py`, `exec()`s it into a fresh `ModuleType`, and registers it.

Generated modules must expose:
```
MODULE_NAME, MODULE_DESCRIPTION, EMERGENCE_REASON
def register(sm): ...
def on_turn_end(sm) -> list[str]: ...
def on_action(sm, action_type, subject) -> dict: ...
```

Modules are **purely additive** — they read state, append events, persist into `state_manager.module_data[MODULE_NAME]`, and propose upgrades via `sm.request_upgrade()`. They must not override or replace kernel tick behavior. This contract is spelled out to the LLM in `llm/codegen.py::MODULE_API_DOCS` — **when you change anything the modules consume (public API on `WorldState`, `PopulationPool`, `Person`, `StateManager`), update `MODULE_API_DOCS` too, or generated code will compile but crash at runtime.**

Crash handling: when a module raises in `on_turn_end`/`on_action`, `ModuleLoader._handle_crash()` evicts it, spawns a daemon thread running `fix_module_code()`, and queues the repair. NPC-triggered upgrades go through `upgrade_module_code()` on another thread. Both queues are drained by `check_pending_results()` at turn end. Because of this, **don't assume a module loaded last turn is still active** — check `loader.is_loaded(name)` or iterate `loader.active_names()`.

## Persistence

Save schema (`savegame.json`) is unversioned. Adding fields to `WorldState` / `Person` / `PopulationPool` requires updating their `to_dict` / `from_dict` *and* usually defensive `.get(..., default)` reads in `StateManager.load()`. `WorldState.from_dict` already pops deprecated fields like `active_mutations` — follow that pattern when deleting fields so old saves still load.

Generated module `.py` files are gitignored. Only their names are stored in the save under `active_modules`; on load, the loader reads each `modules/<name>.py` from disk and re-execs it. So: a save without its `modules/` directory loses all emergent systems but keeps world/population state.

## Working in this repo

- Repo root is `GodGame/`, not the outer `god/` directory — `cd GodGame` before running.
- Adding a player command: extend the `elif cmd in (...)` chain in `main.py::run()`; route state changes through `sim.player_act`, display-only work through `sim.player_query`. Update `_help()` too.
- Touching `WorldState`/`Person`/`PopulationPool`/`StateManager` public surface → keep `llm/codegen.py::MODULE_API_DOCS` in sync. It's the only spec the LLM has.
- Before adding world content (new tick, new dataclass, new hardcoded mechanic), check: could this emerge as a module instead? The answer is usually yes, and that path is preferred.
- `modules/*.py` is LLM output — don't hand-edit unless debugging; re-gen is the normal flow.
