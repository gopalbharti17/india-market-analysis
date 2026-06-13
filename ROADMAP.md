# PROJECT ROADMAP & PICK-UP GUIDE
### India Market Analysis Agent · written June 2026 · v7

This file exists so the project can be paused and resumed without losing the
plot. It records where things stand, what comes next in dependency order, and
the exact prompts to restart work with Claude (chat) or Claude Code.

> Companion documents: **README.md** (setup & usage) · **METHODOLOGY.md**
> (scoring logic, weaknesses, validation plan). Read those two plus this file
> and you have the complete project state.

---

## A. Where the project stands (honest status)

**Built and logic-tested (v1–v7):**
- Data layer: AMFI fund NAVs (mfapi.in), NSE TRI benchmarks with flagged
  fallback, Yahoo stock prices/momentum, screener.in fundamentals bridge
  (ROCE, 3-yr growth, promoter pledging), SQLite cache, provider architecture
  ready for paid APIs (Kite stub included)
- Analysis: sector-aware stock scoring; category/benchmark-relative fund
  scoring (alpha, capture ratios, rolling returns); governance red flags
- Memory: every run recorded to research_history.db; change narration with
  pillar attribution; trend queries (history_report.py)
- Documentation: METHODOLOGY.md (formulas, rationale, weakness register W1–W8,
  validation plan)

**NOT yet done — the three honest gaps:**
1. **Never run on live data.** All tests used synthetic/mocked inputs.
2. **Agent layer embryonic.** agent.py = 3-tool skeleton, never executed,
   no document reading, no access to memory/trends.
3. **Methodology unvalidated.** No backtest; scores are hypotheses (W1).

**Verdict at time of writing:** good quantitative research ENGINE (~7/10 for
free-data class), nascent AI AGENT (~2/10). The hard substrate is done; the
intelligence layer is the remaining 30%.

---

## B. The steps, in dependency order

Mark each ☐ → ☑ with the date as you complete it.

### ☐ STEP 1 — Live verification  *(owner: YOU · ~1 hour · the gate for everything)*
Do: README setup → `python main.py` 3–4 times over a few days → then one
screener.in export and switch `STOCK_PROVIDER = "screener_export"`.
**Acceptance criteria:**
- [ ] Both ranking tables print; CSVs created
- [ ] Benchmarks print "using official TRI data" (or the loud fallback warning)
- [ ] Second run is fast (cache) and the CHANGES section activates
- [ ] screener.in path loads and reports its mapped fields
If anything breaks: paste the error to Claude, or run the Claude Code prompt
in §C below.

### ☐ STEP 2 — Weekly habit + (optional) scheduler  *(owner: YOU · 10 min/wk)*
Weekly: fresh screener export → run → skim changes. Every run enriches
research_history.db (BACK IT UP). Optional build: OS scheduler + alerts.

### ☐ STEP 3 — Bring the agent to life  *(owner: Claude/Claude Code · one session)*
Set ANTHROPIC_API_KEY → first run of agent.py → expand toolset from 3 tools to
the full engine: fund comparison, memory/trend queries, screening, change
summaries, watchlist editing.
**Acceptance:** you can ask in plain English "which of my funds deteriorated
this quarter and why?" and get a tool-backed answer.

### ☐ STEP 4 — Document-reading layer  *(the capability leap · best in Claude Code)*
Agent ingests annual reports / concall transcripts / rating rationales (PDF),
answers sourced questions, cross-checks narrative vs the quantitative scores.
This fulfils the original "research AI agent" vision; no screener site has it.

### ☐ STEP 5 — Backtest  *(the credibility test · spec in METHODOLOGY.md §8)*
Historical scores quarterly ≥10 yrs (guard against look-ahead bias) → forward
returns of top vs bottom quintile → tune weights on training years, verify
held-out → publish result in METHODOLOGY.md either way.
**Until this is done: scores are structured opinions, not evidence.**

### ☐ STEP 6 — Quality of life  *(optional, anytime after Step 3)*
Streamlit dashboard · alerts (Telegram/email) · ETF support (route NSE ETF
prices through the fund analyzer) · MF portfolio-overlap analysis · TRI
self-relative valuation bands · auto research notes. Backlog: METHODOLOGY.md §9.

---

## C. Resume prompts (copy-paste to restart work)

**Claude Code, Step 1 (fix live-data issues):**
> Read README.md, METHODOLOGY.md and ROADMAP.md in this folder. Run
> main.py against live data, fix whatever fails, and verify all four
> acceptance criteria under Step 1 of ROADMAP.md. Don't change scoring logic;
> if you must, update METHODOLOGY.md in the same change.

**Claude Code, Step 3 (agent expansion):**
> Read ROADMAP.md Step 3. Expand agent.py: add tools for fund comparison,
> trend/history queries (core/history.py), full-watchlist screening, and
> change summaries. Test each tool live. Keep the system prompt's honesty
> rules (relative scores, not advice).

**Claude chat (strategy/design):**
> I'm resuming my India market research agent project. Attached/pasted:
> ROADMAP.md. We are at Step <N>. <What happened since last time.> Advise
> on <question> before I build.

**Rules that survive any handoff:**
1. Scoring changes must update METHODOLOGY.md in the same change (+changelog).
2. research_history.db is precious — never delete; back it up.
3. No automated order placement, ever. Research and execution stay separated.
4. This is a personal research tool; sharing recommendations with others
   requires SEBI RIA registration.

---

## D. Decision log (why things are the way they are)
- Free-first data, paid-ready architecture: budget constraint + clean upgrade
  path (provider pattern, config switch)
- Percentile/relative scoring with flagged peer groups: transparency over
  false absolutes
- Pledging reported, not scored: discrete risk must not be averaged away
- TRI default with loud fallback: correctness with resilience
- Memory before backtest: history must start accumulating as early as possible
- Honest labels everywhere (rank_scope, HYPOTHESIS status): a research tool
  that overstates its certainty is worse than no tool

*Update this file as steps complete. It is the project's continuity.*
