# Cosmic Forecast repository context

Use this file as the working context for changes in this repository. Keep it
short and update it when the architecture, supported commands, or engineering
rules change.

## Project

Cosmic Forecast is a Python 3.12 application that combines a FastAPI service,
a dependency-free canvas frontend, live astronomy catalogs, and TensorFlow
models for object classification and trajectory forecasting.

- `app/api.py` owns API routes, scene assembly, and static-page serving.
- `app/data_parser.py` fetches and normalizes CelesTrak, JPL, and SIMBAD data.
- `app/ephemeris.py` computes local solar-system body positions.
  Lunar positions use ERFA Moon98 in GCRS with TT conversion; preserve explicit
  historical and future time assumptions when changing this calculation.
- `app/horizons.py` retrieves geometric JPL reference vectors for NEO placement
  and sampled validation; `scripts/validate_ephemeris.py` records comparisons.
- `app/orbital_forecast.py` and `scripts/train_orbital_forecast.py` support
  experimental historical GP/OMM residual training, separate from the web forecast.
- `app/db.py` and `app/auth.py` own SQLite persistence and authentication.
- `app/pipeline.py` connects classification, track building, Transformer
  forecasting, and Kalman refinement.
- `front_end/` contains the HTML pages, canvas renderer, styles, and Jest tests.
- `scripts/` contains training, pipeline, frontend-test, and model-publishing
  entry points.
- `docs/architecture.md` describes the current system design.
- `docs/known-issues.md` contains unresolved work only, with tier and priority.

## Working rules

- Preserve scientific provenance. Distinguish sourced or computed positions,
  illustrative placement, synthetic model output, and decorative effects in
  code and user-facing text.
- Do not add fabricated objects to live scene responses. User-created and CSV
  objects may still use supported custom kinds such as `ufo`.
- Keep external-source failures isolated and visible through structured
  warnings and admin health data.
- Keep caches bounded, concurrency-safe, and keyed by the inputs that actually
  change. Preserve source freshness metadata when changing cache behavior.
- Treat model training and generated classification patches as synthetic until
  evaluation on representative observations establishes otherwise.
- Resolve paths from repository or module locations rather than the caller's
  working directory.
- Never commit credentials, tokens, local databases, caches, model artifacts,
  uploaded data, or private files from the surrounding iCloud directory.
- Model publishing must remain a dry run unless the user explicitly requests
  `--push`. Review the generated model card before any upload.
- Update `docs/architecture.md`, `README.md`, help text, and
  `docs/known-issues.md` when behavior or limitations change. Remove a known
  issue only when the implementation and documentation resolve it.
- Make focused changes and add tests for behavior with meaningful regression
  risk. Do not weaken the coverage gate.

## Environment and commands

Use the repository root unless a command says otherwise. The supported Python
version is exactly 3.12.
Dependency markers select TensorFlow 2.21.0 on Windows and TensorFlow CPU
2.16.2 elsewhere to retain Intel Mac compatibility. Keep the lockfile in sync
and verify model behavior on the affected platform when changing these pins.

```powershell
uv sync --group dev
uv run uvicorn app.api:app --reload
uv run pytest
uv run pytest --cov=. --cov-fail-under=80
npm.cmd --prefix front_end test -- --runInBand
uv run pre-commit run --all-files
```

Frontend tests use the tracked `front_end/package-lock.json` through
`scripts/test_frontend.mjs`; do not create an untracked install in the iCloud
checkout. Invoke Python scripts as modules, for example:

```powershell
uv run python -m scripts.run_pipeline
uv run python -m scripts.train_object_classifier
uv run python -m scripts.publish_model classifier --repo OWNER/REPO
```

Install the optional Hugging Face publishing dependency with
`uv sync --group publish`. Tokens belong in `HF_TOKEN` or the Hugging Face
credential store and must never be written into repository files or command
output.

## Verification

- Run targeted tests while developing.
- Run the full Python suite for backend, data, persistence, or model changes.
- Run the full frontend suite for HTML, CSS, or JavaScript changes.
- Run `git diff --check` before committing.
- Let pre-commit and pre-push hooks finish; fix failures instead of bypassing
  them.
- Confirm `git status` is clean and the intended branch tracks the expected
  remote after committing or pushing.

## Git scope

Work on the branch selected by the user. Do not include unrelated worktree
changes in a commit. Never rewrite shared history, force-push, or discard user
changes unless the user explicitly requests it.
