Contributions are welcome — this is a small personal project, so a little
process keeps it manageable:

- **Small fixes** (typos, obvious bugs, minor UI tweaks) — open a PR directly.
- **Anything bigger** (new features, mascot moods, behavior changes, refactors)
  — please open an issue first so we can agree on the approach before you spend
  time on it.
- **Test your change** with `--mock` for UI work, or against a live Claude Code
  session for mascot/transcript behavior, and keep each PR focused on one thing.

**Please don't:**

- **Modify, add, or relicense the Clawd mascot art.** The sprites
  (`assets/sprites/`) are © Anthropic under a deliberate carve-out — see
  [NOTICE](NOTICE) and the license section. They are not MIT-licensed.
- **Add new runtime dependencies** without discussing it first. The footprint is
  intentionally tiny (PySide6 + httpx); let's keep it lean.
- **Bundle large refactors or unrelated reformatting** into a feature/fix PR.
  Small, focused diffs get reviewed and merged faster.

**Cross-platform (Linux/macOS):** this is intentionally a Windows-focused app,
and that's the current scope. The UI is Qt (PySide6) so a port isn't far-fetched,
but several pieces are Windows-specific (tray and Start-menu integration, the
PyInstaller build, some font choices) and I'm not set up to test other platforms.
If you're interested, open an issue to discuss before starting — I'm open to it in
principle, but it can't come at the expense of the Windows experience, and a port
would realistically need someone willing to help maintain it.
