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
./run.sh package          # build extension/provenance.vsix
code --install-extension extension/provenance.vsix
```

Then open `seed/repo` in VS Code, select `webhooks/delivery.py` lines 20–40 and press
`⌘⌥W`. `./run.sh help` lists everything else (`eval`, `mcp`, `bot`, `status`, `stop`).

### Plug it into your coding agent

Any MCP client works. The tool is read-only and idempotent, so clients can call it
without a confirmation prompt:

```json
{
  "mcpServers": {
    "provenance": {
      "command": "/path/to/provenance/.venv/bin/python",
      "args": ["-m", "provenance.mcp_server.server"]
    }
  }
}
```

### Or from the terminal

```bash
pip install -e .
provenance explain webhooks/delivery.py:20-40     # --json for the raw response
provenance graph 130e156                          # one commit's PR chain, no LLM
```

## It won't make things up

A tool that explains *why* is worse than useless if it invents reasons. So "no relevant
context" is a first-class answer, enforced at four independent layers:

1. **Retrieval null threshold**: weak matches short-circuit before any LLM call
2. **Rerank**: the LLM drops candidates that only share vocabulary with the code
3. **Synthesis prompt**: told to say plainly when the evidence doesn't explain the code
4. **Citation guard**: a synthesis that cites evidence it was never shown is discarded

`make eval` checks all of it against a seeded corpus with deliberate distractors: the
expected threads appear (and at what rank), the null case returns nothing and no
narrative, every `[n]` citation points at real evidence, and the conflict case reports
which proposal was superseded. `make calibrate` tunes the null threshold to your corpus.

## Built with

| | |
|---|---|
| **Retrieval** | Elasticsearch 8.17 (BM25 + dense kNN, reciprocal rank fusion) |
| **Models** | OpenAI `text-embedding-3-small`, `gpt-4o-mini` (rerank), `gpt-4o` (synthesis) |
| **Service** | Python 3.12, FastAPI, Pydantic contracts shared with TypeScript |
| **Surfaces** | VS Code extension (TypeScript, SVG timeline), MCP Python SDK, CLI |
| **Sources** | git, Slack (export, live API, Socket Mode bot), GitHub, Jira, Sentry |
| **Observability** | Sentry: each pipeline stage is a span, the same names as the diagram |

## Connecting real systems

The demo corpus needs nothing but an OpenAI key. `USE_MOCK_DATA=false` switches every
integration to its live API at once. Adapters without credentials return nothing rather
than falling back to fixtures, so real and fake data never mix.

<details>
<summary><b>Slack</b>: shared index, live sync and the on-demand bot</summary>

1. Create an **internal** Slack app from [`slack_app_manifest.yml`](slack_app_manifest.yml)
   and install it. Keep it internal: Slack throttles history reads for distributed apps.
2. Add `SLACK_BOT_TOKEN` and `SLACK_BOT_CHANNEL_IDS` (public channel IDs, or `*`) to `.env`.
3. `make slack-check` (it says exactly what's wrong), then `make ingest-slack`.

Keep it current with `make ingest-slack-incremental` (new messages, including replies
to old threads) and `make reconcile-slack` (edits, deletions, new channels).

**The bot** (`make slackbot`, Socket Mode, no public URL) indexes one conversation on
demand: use **Index in Provenance** from a message's `…` menu, or `/provenance`. A thread
that ended two minutes ago is matchable against the code you're about to write. Tip:
name the file in the thread (`webhooks/delivery.py`) to turn a semantic match into an
exact one.

</details>

<details>
<summary><b>Sentry</b>: incidents on the graph</summary>

Sentry doesn't model "which incidents did PR #4821 cause", so Provenance joins through
the identifier both systems already share:

```
PR #4821 --GitHub--> merge_commit_sha --Sentry--> firstRelease:<sha>
```

This needs the analysed repo to name releases after the merge commit, which
[`getsentry/action-release`](https://github.com/getsentry/action-release) does by
default. Then set `SENTRY_API_TOKEN` (`event:read`, `org:read`), `SENTRY_ORG`,
`SENTRY_PROJECT`, `GITHUB_TOKEN` and `GITHUB_REPO`. Separately, `SENTRY_DSN` traces
Provenance itself.

</details>

<details>
<summary><b>GitHub and Jira</b></summary>

GitHub (`GITHUB_TOKEN`, `GITHUB_REPO`) is required in live mode: it puts titles, authors
and merge dates on the PR chain. Jira (`JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_TOKEN`) is
optional; PR-to-ticket lookup is a JQL heuristic, ticket-key lookup is exact.

</details>

## Challenges we ran into

- **Code and Slack don't speak the same language.** Embedding code directly against
  chat matched nothing useful; rewriting code into engineering prose first fixed it.
- **"Exact" needs a commit-to-PR join that works everywhere.** Squash merges, merge
  commits and rebase merges each hide the PR differently, so `sha_to_pr` handles all three.
- **Incremental Slack sync is a trap.** Indexing only new messages truncates old threads
  that get a late reply, so affected threads are rebuilt whole.
- **Evals that flake on wording.** Expected evidence is pinned to the thread's own words,
  never its LLM summary, which changes on every ingest.

## What we're proud of

- Asserted evidence: a PR-number match can't be "reranked away" by a model
- Answers that name the superseded decision, not just the latest one
- One contract (`ContextResponse`), three surfaces, zero duplicated retrieval

## What's next

- Tree-sitter symbol extraction in place of the regex seam
- Multi-repository indexes and per-user access filtering
- Slack Events API webhooks instead of incremental polling
- More trackers (Linear, GitLab) behind the same adapter interface

## Project layout

```
provenance/
  service/      the /context pipeline: blame, query build, retrieve, rerank, graph
  ingest/       Slack → Elasticsearch: export and live readers, three sync modes
  slackbot/     on-demand indexing from inside Slack
  integrations/ GitHub, Jira, Sentry adapters (fixture or live)
  mcp_server/   MCP stdio server
  cli/          terminal surface
  models.py     the shared contract, mirrored in extension/src/types.ts
extension/      VS Code extension
evals/          eval harness and its fixed query set
seed/           deterministic demo corpus: a real git repo + Slack export
```

## Team

<!-- TEAM: add names, roles and links -->
