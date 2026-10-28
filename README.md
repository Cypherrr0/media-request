# media-request
Agent instructions and API reference for a self-hosted media request service (search movies/TV, request downloads into a Jellyfin library, track status).

- `SKILL.md` — agent instructions (filename and frontmatter required by the loader)
- `API.md` — HTTP API reference
- `scripts/media_req.py` — single stdlib-only Python 3 CLI for the API

Configuration (set as agent secrets / environment variables, never commit them):
- `MEDIA_REQ_BASE_URL` — e.g. `https://media.example.com/req`
- `MEDIA_REQ_API_KEY` — per-user bearer key

## CLI
```bash
cp .env.example .env   # fill in values, or export them
python3 scripts/media_req.py search "Oppenheimer" --type movie --region western
python3 scripts/media_req.py request movie:tmdb:872585 --region western [--dry-run]
python3 scripts/media_req.py status <request_id> [--wait --interval 300 --timeout 3600]
python3 scripts/media_req.py list
```
Prints JSON to stdout. Exit codes: 0 ok, 1 API error / `failed` / `quota_exceeded`, 2 network, 3 missing config, 4 wait timeout.
Terminal statuses: `available`, `failed`, `already_exists`, `quota_exceeded`, `dry_run_selected`; `--wait` also stops on `not_found` (retried server-side).
