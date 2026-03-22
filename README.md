# Time Thief Hunter

> A local AI agent that watches your screen, catches you procrastinating, and forces you to negotiate your way out — complete with pixel art characters, boss raid encounters, and Matrix easter eggs.

## What It Does

- **Perception agent** — Monitors your screen activity via OCR every 30 seconds
- **Task context agent** — Inspects local repo/branch/workspace signals to infer what you should be doing
- **Classification agent** — Scores distraction risk from app hits, OCR signals, and prior history
- **Policy agent** — Decides whether to ignore, observe, cool down, or interrupt
- **Planner agent** — Builds an intervention contract with follow-up timing and negotiation constraints
- **Enforcement agent** — Activates plans, schedules follow-ups, and fires an on-top desktop popup
- **Negotiation agent** — Lets you bargain with a Claude-powered monitor that remembers prior warnings
- **Persistent memory** — Stores local state, active plans, follow-up queue, and offense history in `~/.time_thief_hunter/state.json`

## Prerequisites

- Python >= 3.9
- macOS (primary platform)
- An AI API key (Anthropic or compatible provider)

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

# Demo mode — auto-cycles through all warning types
time-thief-hunter --demo

# Or run directly with Python
python -m time_thief_hunter
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
│   ├── perception.py        # Screen OCR -> Observation
│   ├── classification.py    # Observation -> Classification
│   ├── policy.py            # Classification -> PolicyDecision
│   ├── planner.py           # Decision -> InterventionPlan
│   ├── enforcement.py       # InterventionPlan -> activated warning/follow-up
│   └── negotiation.py       # Popup conversation -> Claude + memory
├── tools/
│   ├── git_tool.py          # Git/repo context access
│   ├── memory_tool.py       # Persistent memory adapter
│   └── popup_tool.py        # Desktop UI adapter
├── workflows/
│   └── intervention_graph.py # Planner-led intervention graph
├── prompts/
│   ├── planner.md           # Planner prompt scaffold
│   ├── negotiator.md        # Negotiator prompt scaffold
│   └── policy.md            # Policy rubric scaffold
├── popup.py                 # pywebview popup (HTML/CSS/JS)
├── ui/
│   └── index.html           # Pixel art UI with boss raid & matrix modes
├── brain.py                 # Claude negotiation engine
└── config.py                # Configuration
```

## How It Works

```
Workflow Executor
    ↓ typed messages
Agent Registry
    ↓
Perception Agent → Screen OCR
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

- All screen data is processed locally — nothing is uploaded
- During AI negotiation, only app context, warning counts, and short chat turns are sent to the AI API — no screenshots
- Your screen content never leaves your machine

## First Run

- On first launch, the app opens an AI-focused setup view.
- Configure your AI provider, model, and API key.
- If no API key is configured, negotiation automatically falls back to a local rule-based mode.
- Settings are stored in `~/.time_thief_hunter/settings.json`.

## License

MIT
