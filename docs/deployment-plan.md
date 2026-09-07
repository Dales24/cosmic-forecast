# Deployment Plan (future)

Target split across GitHub, Hugging Face, and AWS. **Not built yet** — this is
the agreed shape to work toward, recorded so the layout doesn't get re-litigated.

## GitHub

| Area | Contents |
|------|----------|
| Source code | `app/`, `front_end/`, `scripts/`, `tests/` — this repo |
| Infrastructure | Terraform or CDK definitions for everything in the AWS section |
| Documentation | `README.md`, `docs/`, `claude/claude.md` |

## Hugging Face

**Account: https://huggingface.co/daley30** (created 2026-08-02).

| Area | Contents |
|------|----------|
| Datasets | Training patches for the object classifier |
| Model checkpoints | Intermediate training artifacts |
| Final models | The released classifier + trajectory transformer |
| Model cards | Provenance, intended use, and limitations for each model |

### What this repo would publish

Two models, both Keras `.keras` files:

| Model | Code | Local output |
|-------|------|--------------|
| Object classifier (CNN, 23 classes) | `app/object_classifier.py` | `models/object_classifier/model.keras`, timestamped copies in `models/archive/` |
| Trajectory transformer | `app/trajectory_transformer.py` | `models/trajectory_transformer/model.keras` |

### Before anything can be uploaded

- **No trained model exists on disk yet.** `models/` is not present; nothing has
  been trained and saved. `uv run python scripts/train_object_classifier.py`
  produces the classifier, but it needs a labelled image dataset organised by
  object slug (see README "Training") — the repo currently only has *synthetic*
  patches, which are illustrative and not worth publishing as a real model.
- **The classifier is trained on synthetic data.** `/api/classify/{id}` runs the
  CNN on a randomly generated patch, not telescope imagery (see
  [known-issues.md](known-issues.md)). Any model card must say this plainly —
  publishing it as a working astronomical classifier would be misleading.
- **Credentials.** Upload needs a HF write token (`huggingface_hub` +
  `HF_TOKEN`); it should live in the environment, never in the repo.

## AWS

| Service | Role |
|---------|------|
| EC2 / ECS / Lambda | Applications and APIs (the FastAPI service) |
| S3 | App uploads, logs, cached files |
| RDS / DynamoDB | Application data |
| CloudFront | Static assets (`front_end/static/*`) |
| IAM / Secrets Manager | Security and credential storage |

## Notes for when this is picked up

Things in the current codebase that this plan directly affects:

- **SQLite → RDS/DynamoDB.** `app/db.py` is the only data-access module and its
  interface is narrow, so the swap is contained — but the schema uses SQLite
  idioms (`AUTOINCREMENT`, `PRAGMA foreign_keys`) that won't port as-is.
- **Sessions have no expiry.** Before anything is internet-facing, session
  tokens need a TTL and pruning; today a token is valid forever. See the open
  items below.
- **The TLE disk cache assumes a writable local path** (`COSMIC_TLE_CACHE_DIR`,
  default `data/tle_cache`). On Lambda or a read-only container this needs to
  move to S3 or `/tmp`.
- **Caches are per-process and in-memory** (`_scene_cache`, `_catalog_cache`).
  Behind more than one instance each replica keeps its own, so hit rates drop
  and freshness varies between replicas. ElastiCache or accepting the drift are
  both fine, but it should be a decision, not a surprise.
- **Bootstrap admin creation requires an explicit secret.** When
  `COSMIC_BOOTSTRAP_ADMIN` is truthy, set
  `COSMIC_BOOTSTRAP_ADMIN_PASSWORD` to at least 12 characters. The username
  defaults to `admin` and can be changed with
  `COSMIC_BOOTSTRAP_ADMIN_USERNAME`. Startup creates or rotates that account;
  provide the password through deployment secret storage, never source control.

## Database behavior

Sessions expire after 7 days and are pruned on login. File databases use WAL
with a 5-second busy timeout. Application operations reuse one connection per
worker thread, roll back failed operations, and replace the connection when the
configured database path changes.
