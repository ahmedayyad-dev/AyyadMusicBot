# DHVbot — AI Constitution & Operating Rules

## ⚠ Permanent Operating Rules
- **Document Durable Rules**: Whenever the user specifies a lasting rule, coding standard, or durable preference, record it in this file. Only keep essential rules needed for future development; avoid transient notes or conversational artifacts.
- **Rule Adherence**: Every rule and preference is binding across sessions. Re-read this file at the start of tasks and verify compliance before committing.

## Open-Source Safety & Privacy (Absolute Requirement)
- **Zero Absolute Paths**: Never write system home directories, local usernames, or environment-specific paths in any git-tracked file. All references must be strictly relative to the project root.
- **Zero Secrets**: Never commit credentials, tokens, session strings, private IDs, or IP addresses.

## Response Language
- Always respond to the user in Arabic.

## Git Policy
- **Local Commits Only**: Push, pull/fetch, clone, remote operations, rebase, and branch switching are rejected unless explicitly requested.
- **Atomic Commits**: Commit one self-contained logical unit of work at a time, only when all touched files pass verification (`python -m py_compile`).

## Absolute Prohibitions
- **Never Run the Bot**: Do not execute `python main.py` or boot the bot instance. Verification is strictly static (`py_compile` and `pylint`).
- **UV Exclusively**: Use `uv` for environment and package management (`uv sync`, `uv add`); never use bare `pip` or system `python`.

## Project Architecture
The project root must contain strictly **three directories**:
1. `core/`: Backend logic, database, configuration, Anghami client, player queue, and voice-call orchestration.
2. `languages/`: Localization dictionaries (`ar.py`).
3. `plugins/`: Pyrogram event handlers (`bot/` for main commands, `helper/` for assistant userbots).

## Code Style & Standards
PEP 8 compliance and a Pylint rating of 10.00/10 (`.pylintrc`) are strictly enforced.

- **Imports at Top of File Only**: Never use deferred or local imports inside functions or classes. Circular dependencies must be resolved architecturally.
- **Single Import Statement Per Source**: Combine all imports from the same module or package into one line (e.g., `from core import anghami, player`).
- **Import Grouping**: Standard library first, then third-party, then internal project packages.
- **No Single-Use Variables (R9002)**: Inline values directly at call sites unless an inline comment `# pylint: disable=no-single-use-var` is strictly necessary.
- **No Wrapper Functions (R9004)**: Avoid functions that merely forward arguments to another callable without adding logic.
- **Inline Redis Keys (R9003)**: Format Redis keys inline directly within database calls (e.g., `f'{bot.me.id}:group:{chat_id}:perm:{command}'`).
- **Redis Pipeline (R9001)**: Use `database.pipeline()` for sequential Redis operations instead of multiple round-trips or `asyncio.gather`.
- **Direct Database Delete**: Delete keys directly without prior existence checks (`get`).
- **Specific Exceptions**: Raise and catch specific exceptions (`aiohttp.ClientError`, `asyncio.TimeoutError`, etc.); never use broad `except Exception`.
- **Arabic Commands Formatting**: Use spaces instead of underscores in Arabic command strings (e.g., `تشغيل الأغنية`, not `تشغيل_الأغنية`).
- **Single Source of Truth**: Eliminate duplicated logic across modules.
- **No `filters.text` with `filters.regex`**: `filters.regex` already evaluates text inherently; combining them is redundant.

## User-Facing Text & UI
- **No Emojis**: Use textual symbols only (`▪`, `▫`, `═`, `✗`, `✓`, `➤`, `⇧`, `⇩`, `↻`, `↺`, `‹`, `›`, `■`, `✕`).
- **Strict Localization**: All text presented to users must be stored as keys in `languages/ar.py`. Never hardcode user-visible strings in logic files.
