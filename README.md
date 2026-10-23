<div align="center">

<img src="extension/media/icon.svg" alt="Provenance" width="88" />

# Provenance

**Select any code. Get the story behind it.**

The commit that wrote it, the PR it shipped in, the Slack thread that decided it, the
ticket that tracked it and the incident it caused, joined into one cited answer.

![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)
![VS Code](https://img.shields.io/badge/VS%20Code-extension-007ACC?logo=visualstudiocode&logoColor=white)
![MCP](https://img.shields.io/badge/MCP-server-000000)
![Elasticsearch](https://img.shields.io/badge/Elasticsearch-8.17-005571?logo=elasticsearch&logoColor=white)
![Sentry](https://img.shields.io/badge/Sentry-traced-362D59?logo=sentry&logoColor=white)

</div>

<!-- DEMO VIDEO: paste the video embed/link here -->
> 🎥 **Demo video:** _coming soon_

---

## The problem

Every codebase is full of lines like `RETRY_BACKOFF_SECONDS = 7`. Why 7 and not 5? The
answer exists, scattered across a PR description, a Slack thread from eight months ago
and an incident nobody links to the code. `git blame` tells you **who**. Nothing tells you
**why**, so the constant gets "cleaned up" and the incident happens again.

## What it does

Highlight a block of code and Provenance recovers its evidence chain:

- **Origin**: blame plus `git log -L`, so even values the code has since replaced are found
- **Discussion**: the Slack threads that explain the code, ranked and cited
- **Consequences**: linked tickets and Sentry incidents
- **Contradictions**: when two threads disagree, it says which one the merged PR matches

One retrieval API (`POST /context`) serves three surfaces. None of them has retrieval
logic of its own:

| Surface | How you use it |
|---|---|
| **VS Code extension** | select code, `⌘⌥W` / `Ctrl+Alt+W`: cited answer, evidence cards, interactive timeline, CodeLens |
| **MCP server** | coding agents call `search_team_context` before touching unfamiliar code |
| **CLI** | `provenance explain webhooks/delivery.py:20-40` |

## How it works

```
POST /context
  ├─ git.blame      ─┐  concurrent; git log -L walks the range's full history
  ├─ query_build    ─┘  code → engineering prose (LLM) + identifiers (regex)
  ├─ retrieve          exact tier (PR / SHA / path / symbol) + hybrid kNN ⊕ BM25 (RRF)
  ├─ rerank            LLM relevance pass; exact hits can never be dropped
  ├─ synthesis         cited 2–3 sentence answer + conflict / supersede detection
  └─ resolve_graph     deterministic PR → ticket → incident joins, no LLM
```

- **Exact beats fuzzy.** If git proves a commit belongs to PR #4821 and a Slack thread
  names #4821, that link is asserted, not scored. Semantic search only fills the gaps.
- **Code is never embedded against prose.** An LLM rewrites the selection into
  engineering prose first, so both sides of the comparison are in the same language.
- **One store.** Elasticsearch does BM25, dense kNN, fusion and relevance weighting.

## Quick start

Needs Python 3.12+, Docker and an `OPENAI_API_KEY`. No other credentials: it runs on a
built-in demo corpus by default.

```bash
cp .env.example .env      # add OPENAI_API_KEY
./run.sh                  # venv, Elasticsearch, seed data, ingest, then serves on :8000
./run.sh package          # build provenance.vsix and install it into VS Code
```

Then open `seed/repo` in VS Code, select `webhooks/delivery.py` lines 20–40 and press
`⌘⌥W`. `./run.sh help` lists everything else (`eval`, `mcp`, `bot`, `status`, `stop`).
