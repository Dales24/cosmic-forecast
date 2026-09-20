# Development environment

Read the repository's [Codex context](../Codex/AGENTS.md) before making changes.
It summarizes the project structure, working rules, verification expectations,
and commands; this document provides the detailed environment setup.

Use Python 3.12 and the checked-in `uv.lock`:

```sh
uv sync --frozen --group publish
```

The optional `publish` group installs `huggingface_hub`. Include it when syncing
or using `uv run --group publish` for publishing so the dependency remains
available. Authentication is separate: set `HF_TOKEN` in your environment when
ready to upload. Do not place a token in source files. The publishing CLI is a
dry run unless `--push` is supplied and creates private repositories by default.

## Platform policy

The current dependency set targets Python 3.12 on Linux x64, Windows x64, and
Intel macOS. CI defines jobs for each; configuring the jobs does not establish
that a particular PR has passed them.

Dependency markers allow Windows to upgrade independently:

| Platform | TensorFlow dependency |
| --- | --- |
| Windows x64 | `tensorflow==2.21.0` |
| Linux x64 / Intel macOS | `tensorflow-cpu==2.16.2` |

Version 2.16 retains [Intel macOS support](https://www.tensorflow.org/install/pip).
The Windows package is the full `tensorflow` distribution, replacing the older
`tensorflow-intel` dependency. `uv sync --frozen` selects the platform's locked
dependencies automatically. Copy-mode installation and the setuptools shim
needed by the older runtime remain enabled. This configures native Windows CPU
TensorFlow; it does not add native Windows CUDA support.
Model serialization is tested within each platform's runtime; cross-version
artifact portability must be checked before sharing trained models between them.
Apple Silicon is not covered by this CI matrix.
The Windows 2.21.0 runtime passed the full 450-test backend suite on 2026-09-20,
including training and model save/load checks. Linux/macOS execution remains
covered by CI rather than this Windows session.

## Scripts and artifact locations

From the repository root, module invocation still works:

```sh
uv run python -m scripts.train_object_classifier --help
uv run python -m scripts.run_pipeline --help
uv run --group publish python -m scripts.publish_model --help
```

Direct file invocation also works from another directory. Use the checkout's
virtual-environment Python and the full path to the script. For example, in
PowerShell, replacing the paths with your checkout:

```powershell
& 'C:\path\cosmic-forecast\.venv\Scripts\python.exe' 'C:\path\cosmic-forecast\scripts\publish_model.py' --help
```

Default classifier, trajectory, and archive directories resolve under the
checkout's `models/`, regardless of the shell directory. Explicit relative
`--data-dir` and `--output` paths resolve relative to the caller. Publishing
accepts `--root` for an alternate root containing `models/`. No command changes
the caller's working directory.

## Frontend dependencies

From `front_end`:

```sh
npm test -- --runInBand
```

`npm test` installs tools with `npm ci` in a unique temporary directory, runs
Jest against this checkout, and cleans up. It works without a local
`node_modules` directory and uses npm's download cache on subsequent runs.
From any directory, use `npm --prefix /path/to/checkout/front_end test`.

`package-lock.json` pins the full dependency graph. Commit manifest and lockfile
updates together. CI uses Node 22 and verifies both a clean local `npm ci` with
`npm run test:local` and the isolated default command. Windows PowerShell users
whose execution policy blocks `npm.ps1` can use `npm.cmd` for these commands.

The isolated command avoids cloud-synced dependency directories, which stalled
installation in this iCloud checkout. It does not relocate or remove existing
workspace dependencies. For a conventional unsynced checkout, `npm ci` followed
by `npm run test:local` remains available.
