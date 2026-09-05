# Development environment

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

TensorFlow stays at 2.16.2 because 2.16 is the last release supporting
[Intel macOS](https://www.tensorflow.org/install/pip). Windows uses
`tensorflow-intel`; the other platforms use `tensorflow-cpu`. Copy-mode `uv`
installation and the existing setuptools compatibility pin are retained.
Upgrading TensorFlow requires a deliberate decision about Intel-mac support.
Apple Silicon is not covered by this CI matrix.

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
npm ci
npm test -- --runInBand
```

`package-lock.json` pins the full dependency graph. Commit manifest and lockfile
updates together. CI uses Node 22 and a clean `npm ci`. Windows PowerShell users
whose execution policy blocks `npm.ps1` can use `npm.cmd` for these commands.

Cloud-synced dependency directories can stall installation. Prefer a checkout
outside iCloud for development; keeping files out of Git does not prevent a
cloud client from syncing them. The lockfile was verified by clean installation
in a temporary directory; the local iCloud stall remains a known limitation.
