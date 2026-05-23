# API overview

## Authentication

All requests require a local session token. Tokens are stored in `~/.cadbury/`.

## Endpoints

| Command | Description |
|---------|-------------|
| `cadbury ask` | Question with optional file retrieval |
| `cadbury eval` | Retrieval metrics |
| `cadbury index` | Build embedding index |

## Rate limits

Local inference has no cloud rate limit. Disk and RAM are the constraints.
