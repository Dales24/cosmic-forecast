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

| Area | Contents |
|------|----------|
| Datasets | Training patches for the object classifier |
| Model checkpoints | Intermediate training artifacts |
| Final models | The released classifier + trajectory transformer |
| Model cards | Provenance, intended use, and limitations for each model |

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
- **`_ensure_admin_user()` creates a default `admin`/`admin` login on startup**
  and deliberately bypasses the password-length rule. This must be removed or
  gated before any real deployment.

## Still-open database work (pre-deployment)

- Session expiry + pruning (needs a TTL decision; 30 days is typical).
- WAL journal mode — writers currently block readers.
- Connection reuse; a new connection is opened per query (~37x overhead on
  repeated reads).
