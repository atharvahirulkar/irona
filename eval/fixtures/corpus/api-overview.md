# API overview

## Authentication

All requests require a local session token. Tokens are stored in `~/.irona/`.

## Endpoints

| Command | Description |
|---------|-------------|
| `irona ask` | Question with optional file retrieval |
| `irona eval` | Retrieval metrics |
| `irona index` | Build embedding index |

## Rate limits

Local inference has no cloud rate limit. Disk and RAM are the constraints.
