# Time Thief Hunter

> A local multi-agent productivity enforcement system built on Screenpipe, with persistent memory, policy orchestration, and Claude-powered negotiation.

## What It Does

- **Perception agent** — Pulls OCR/window activity from Screenpipe every 30 seconds
- **Task context agent** — Inspects local repo/branch/workspace signals to infer what you should be doing
- **Classification agent** — Scores distraction risk from app hits, OCR signals, and prior history
- **Policy agent** — Decides whether to ignore, observe, cool down, or interrupt
- **Planner agent** — Builds an intervention contract with follow-up timing and negotiation constraints
- **Enforcement agent** — Activates plans, schedules follow-ups, and fires an on-top desktop popup
- **Negotiation agent** — Lets you bargain with a Claude-powered monitor that remembers prior warnings
- **First-run setup** — Checks Screenpipe and API readiness, persists settings locally, and offers a degraded-mode fallback
- **Vendored Screenpipe** — The repository now carries a vendored Screenpipe source tree under `third_party/screenpipe`
- **Persistent memory** — Stores local state, active plans, follow-up queue, and offense history in `~/.time_thief_hunter/state.json`

## Prerequisites

- Python >= 3.9
- [Screenpipe](https://github.com/mediar-ai/screenpipe) running locally (`localhost:3030`)
- An AI API key for Anthropic or Gemini

## Install

```bash
git clone https://github.com/DHCFE/project.git
cd project
pip install .
```

For development:

```bash
pip install -e .
```

## Usage

```bash
# Start monitoring
time-thief-hunter

# Test the popup (no actual procrastination needed)
time-thief-hunter --test

# Or run directly with Python
python -m time_thief_hunter
python -m time_thief_hunter --test
```

## Configuration

Edit `time_thief_hunter/config.py`:

```python
CHECK_INTERVAL = 30          # Check interval (seconds)
LOOKBACK_MINUTES = 5         # How many minutes of activity to analyze
DISTRACTION_THRESHOLD = 3    # Minimum OCR frame hits to trigger warning

DISTRACTION_APPS = [         # Apps considered distractions
    "YouTube", "Twitter", "Reddit", "Steam", ...
]
```

## Project Structure

```
time_thief_hunter/
├── main.py                  # Composition root
├── orchestrator.py          # Multi-agent scheduler / coordinator
├── memory.py                # Persistent local state and negotiation transcript store
├── settings.py              # User settings persistence
├── startup.py               # First-run checks and degraded-mode readiness
├── event_bus.py             # Internal event stream
├── models.py                # Domain models
├── runtime/
│   ├── agent_registry.py    # Agent registry + message dispatch
│   ├── executor.py          # Workflow executor
│   ├── messages.py          # Typed message envelope
│   ├── state_machine.py     # Workflow run state
│   └── traces.py            # Run trace persistence
├── agents/
│   ├── task_context.py      # Local repo / branch / dirty-state inference
│   ├── perception.py        # Screenpipe -> Observation
│   ├── classification.py    # Observation -> Classification
│   ├── policy.py            # Classification -> PolicyDecision
│   ├── planner.py           # Decision -> InterventionPlan
│   ├── enforcement.py       # InterventionPlan -> activated warning/follow-up
│   └── negotiation.py       # Popup conversation -> Claude + memory
├── tools/
│   ├── screenpipe_tool.py   # Screenpipe access
│   ├── git_tool.py          # Git/repo context access
│   ├── memory_tool.py       # Persistent memory adapter
│   └── popup_tool.py        # Desktop UI adapter
├── workflows/
│   └── intervention_graph.py # Planner-led intervention graph
├── prompts/
│   ├── planner.md           # Planner prompt scaffold
│   ├── negotiator.md        # Negotiator prompt scaffold
│   └── policy.md            # Policy rubric scaffold
├── vendor_screenpipe.py     # Vendored Screenpipe build/launch helpers
├── popup.py                 # pywebview popup (HTML/CSS/JS)
├── brain.py                 # Claude negotiation engine
├── screenpipe_client.py     # Screenpipe REST API client
└── config.py                # Configuration

third_party/
└── screenpipe/              # Vendored upstream Screenpipe source snapshot

scripts/
├── build_vendored_screenpipe.sh
└── update_vendored_screenpipe.sh
```

## How It Works

```
Workflow Executor
    ↓ typed messages
Agent Registry
    ↓
Perception Agent → Screenpipe Tool
    ↓
Task Context Agent → Git Tool
    ↓
Classification Agent
    ↓
Policy Agent
    ↓
Planner Agent → Prompt Templates
    ↓
Enforcement Agent → Popup Tool
    ↓
Memory Tool / Memory Store
    ↓
Negotiation Agent → Claude Brain
```

## Privacy

- All screen data is read from local Screenpipe only — nothing is uploaded
- During AI negotiation, only app context, warning counts, and short chat turns are sent to Claude API — no screenshots
- Your screen content never leaves your machine

## First Run

- On first launch, the app opens an AI-focused setup view.
- The user-facing setup only asks for AI provider, model, and API key.
- Monitoring is treated as an internal subsystem: by default the app prefers the vendored Screenpipe source tree instead of relying on a system-installed Screenpipe.
- End-user builds are expected to ship a prebuilt bundled binary under `time_thief_hunter/bin/<platform>/screenpipe`; the runtime no longer compiles Screenpipe on first launch.
- Development helpers:
  - `./scripts/install_bundled_screenpipe.sh` builds the vendored Screenpipe once and installs it into the bundled runtime path.
  - `./scripts/build_macos_app.sh` packages the Python app and bundled Screenpipe into `dist/macos/TimeThiefHunter.app`.
- If no AI API key is configured, negotiation and AI classification automatically fall back to a local rule-based mode.
- Settings are stored in `~/.time_thief_hunter/settings.json`.

## License

MIT
