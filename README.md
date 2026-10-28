# media-request
Agent instructions and API reference for a self-hosted media request service (search movies/TV, request downloads into a Jellyfin library, track status).

- `SKILL.md` — agent instructions (filename and frontmatter required by the loader)
- `API.md` — HTTP API reference

Configuration (set as agent secrets / environment variables, never commit them):
- `MEDIA_REQ_BASE_URL` — e.g. `https://media.example.com/req`
- `MEDIA_REQ_API_KEY` — per-user bearer key
