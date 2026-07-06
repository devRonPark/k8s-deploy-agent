# Harness Lessons

Reusable prevention rules from solved errors.

## Current Rules

- Keep raw secret values out of all generated assets and UI.
- Prefer credential IDs and environment variable names for sensitive integration points.
- For this repository, use `UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q` to avoid home cache permission issues.
- Do not assume internet access in target runtime; design for customer on-premise and air-gapped operation.
- Validate analyzer changes against both multi-service subdirectory repos and root-level app repos; they exercise different service discovery paths.
