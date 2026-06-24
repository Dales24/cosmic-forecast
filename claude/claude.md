# Engineering Rules

Guidance for working in this repo. These apply to every change.

## Stack

- **Backend:** Python 3.12, FastAPI, TensorFlow/NumPy/Pandas (`app/`)
- **Frontend:** vanilla JS SPA, canvas rendering (`front_end/`)
- **Tooling:** uv (env + deps, Python 3.12), black + flake8, pytest + coverage, pre-commit

## 1. Readable, not clever

- Prefer the obvious solution over the compact one. Code is read far more than it's written.
- Name things for what they are: `track_builder`, not `tb`. No single-letter names except short loop indices.
- Keep functions short and single-purpose. If a function needs a paragraph to explain, split it.
- Avoid deep nesting — return early, flatten conditionals.
- No premature abstraction. Don't add a layer until there are two real callers.

## 2. Modular

- Respect the existing module boundaries (see `README.md` Architecture). Each `app/` file owns one stage of the pipeline: CNN → track → transformer → Kalman.
- A module should do its job and expose a clear interface; don't reach across into another module's internals.
- Pure logic stays out of `api.py` — routes wire things together, they don't contain the algorithm.
- Shared types/constants live in `object_classes.py`; don't redefine them locally.

## 3. Corner cases & coverage

- Think through the edges before writing: empty input, single element, missing/NaN data, network failure from the data sources (CelesTrak / JPL / SIMBAD), malformed uploads.
- External data fetchers must handle timeouts and bad responses gracefully — never let one source failure crash the pipeline.
- Every behavioral change ships with a test. New `app/` logic → a `tests/` case; new `front_end/` logic → a `front_end/tests/` case.
- Coverage must stay **≥ 80%** (`uv run pytest --cov-fail-under=80`, enforced on push). Run tests before claiming done.
- Cover the failure path, not just the happy path.

## 4. Follow the linter

- Format with **black** and pass **flake8** before finishing — pre-commit runs both.
- Match the configured rules; don't introduce new ignores to dodge a warning. Fix the code instead.
- Keep imports clean and ordered. No dead code or unused variables.

## 5. Concise comments

- Comment the **why**, not the **what** — the code already says what it does.
- One clear line beats a paragraph. Explain non-obvious math, model assumptions, and external-API quirks.
- Keep docstrings short: purpose, key params, return. No boilerplate.
- Delete stale comments when you change the code they describe.

## 6. Cleanup checklist

Run this pass over any code you add or touch before calling it done:

- **Organization:** Code lives in the module that owns its stage of the pipeline. Entry-point/process concerns (CLI args, signals, exit codes) stay in `scripts/`; algorithms stay in `app/`. Related functions sit together; order them so a reader meets helpers before their callers.
- **Modular:** One function, one job. Extract a private helper (`_write_model`) when two paths repeat the same steps. Don't reach into another module's internals — call its interface.
- **Corner cases:** Handle empty/missing/single-element input and not-found paths explicitly. Fail loud and clear (`FileNotFoundError("No archived model named …")`) instead of letting a downstream library throw something cryptic.
- **Types:** Annotate params and returns (`-> Path`, `str | Path`, `name: str | None = None`). Accept the widest sane input type, return the narrowest.
- **Commons:** No repeated literals or magic strings — promote them to a named constant (`MODEL_FILENAME`) shared by every reader. Shared types/constants belong in their owning module, imported, never redefined.

## Definition of done

1. Code is readable and modular.
2. Edge cases handled and tested; coverage ≥ 80%.
3. black + flake8 clean.
4. Comments explain the non-obvious, and nothing else.
5. Cleanup checklist (§6) applied: organization, modular, corners, types, commons.
