# Command Line Flag Reference

Dev Type supports several command-line flags for comprehensive testing, data generation, and profile management.

## Core Flags

### `--profile <name>`
**Description**: Loads a specific user profile on startup.
- If the profile does not exist, it is **automatically created** with default settings.
- Updates `global_config.json` to set this as the active profile.
- **Example**: `uv run main.py --profile "TestUser"`

### `--sandbox`
**Description**: Runs the application in **Sandbox Mode**.
- Uses an isolated, temporary database (`demo_stats.db`) instead of any user profile.
- Useful for guest sessions or testing without affecting real data.
- **Legacy Alias**: `--demo`
- **Example**: `uv run main.py --sandbox`

---

## Data Generation
These flags allow you to generate realistic fake typing history for testing the Stats page reliability and performance.

### `--gen-data`
**Description**: Triggers the data generation routine before starting the app.
- Targets the **Active Profile** (if `--profile` is used or default) or the **Sandbox** (if `--sandbox` is used).
- **Example**: `uv run main.py --profile "Bob" --gen-data`

### Configuration Options
Use these in conjunction with `--gen-data`:

- **`--gen-days <int>`**: Number of days of history to generate (Default: `365`).
- **`--gen-langs <list>`**: Comma-separated list of languages to include (Default: Standard set).
  - **Example**: `--gen-langs "Python,Rust,Go"`
- **`--gen-count <range>`**: Daily session count range (Default: `"3-10"`).
  - **Example**: `--gen-count "1-5"`

---

## Debugging

### `--debug-indent`
**Description**: Enables **Indent Testing Mode** for the Typing Area.
- Adds a "Record" button to the editor toolbar.
- Logs detailed keystroke data to the console (Input, Backspace, Tab processing).
- **Legacy Alias**: `--indent_test`
- **Example**: `uv run main.py --debug-indent`

---

## Legacy Flags
Supported for backward compatibility but recommended to use new equivalents.

- **`--demo`**: Same as `--sandbox`.
- **`--year <int>`**: Sets specific year for generation (use `--gen-days` instead).
- **`--persist`**: Prevents clearing the sandbox DB (only applies to `--sandbox`).

## Common Workflows

**1. Create/Load a Test Profile with Data**
```bash
uv run main.py --profile "StressTest" --gen-data --gen-days 730 --gen-count "10-20"
```

**2. Quick Sandbox Test**
```bash
uv run main.py --sandbox
```

**3. Debug Typing Input**
```bash
uv run main.py --debug-indent
```

**4. Generate Data for Current Default Profile**
```bash
uv run main.py --gen-data --gen-years 1
```
