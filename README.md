# Time Thief Hunter

> A local AI agent that monitors your screen activity via Screenpipe, catches you procrastinating, and pops up a warning — with an AI you can negotiate with.

## What It Does

- **Real-time monitoring** — Checks your active app every 30 seconds via Screenpipe
- **Distraction detection** — Triggers when you're on YouTube / Bilibili / Reddit / Twitter / Steam etc.
- **Desktop popup** — Dark surveillance-themed alert you can't ignore
- **AI negotiation** — Click "Plead" to negotiate with a Claude-powered AI that's sarcastic, strict, but open to deals

## Prerequisites

- Python >= 3.9
- [Screenpipe](https://github.com/mediar-ai/screenpipe) running locally (`localhost:3030`)
- Anthropic API key (set `ANTHROPIC_API_KEY` environment variable)

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
├── main.py               # Entry point + monitoring loop
├── popup.py              # pywebview popup (HTML/CSS/JS)
├── brain.py              # Claude AI negotiation brain
├── screenpipe_client.py  # Screenpipe REST API client
└── config.py             # Configuration
```

## How It Works

```
Screenpipe (screen capture + OCR)
    ↓ REST API
Monitoring loop (every 30s)
    ↓ Rule matching
Distraction detected → Popup warning
                         ↓ User clicks "Plead"
                     Claude AI negotiation
```

## Privacy

- All screen data is read from local Screenpipe only — nothing is uploaded
- During AI negotiation, only the app name and duration are sent to Claude API — no screenshots
- Your screen content never leaves your machine

## License

MIT
