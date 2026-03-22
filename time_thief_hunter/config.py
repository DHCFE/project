"""时间小偷猎人 - 配置"""

import os
from pathlib import Path

SCREENPIPE_URL = os.getenv("SCREENPIPE_URL", "http://localhost:3030")
SCREENPIPE_HEALTH_TIMEOUT_SECONDS = float(os.getenv("SCREENPIPE_HEALTH_TIMEOUT_SECONDS", "1.5"))
SCREENPIPE_REQUEST_TIMEOUT_SECONDS = float(os.getenv("SCREENPIPE_REQUEST_TIMEOUT_SECONDS", "20"))
ALLOW_LOCAL_NEGOTIATION_FALLBACK = os.getenv("ALLOW_LOCAL_NEGOTIATION_FALLBACK", "1") != "0"

# 检查间隔（秒）
CHECK_INTERVAL = 20

# 查看最近多少分钟的活动
LOOKBACK_MINUTES = 5

# 摸鱼帧数超过此值才进入高风险状态
DISTRACTION_THRESHOLD = 3

# 进入警告后的冷却时间。当前为本地联调模式，固定 20 秒。
BASE_COOLDOWN_SECONDS = 20

# 工作时间。policy agent 会在这个时段更严格地拦截。
WORKDAY_START_HOUR = 9
WORKDAY_END_HOUR = 19

# 本地记忆和事件日志存储目录
STATE_DIR = Path.home() / ".time_thief_hunter"
STATE_FILE = STATE_DIR / "state.json"
TRACE_FILE = STATE_DIR / "traces.jsonl"
SETTINGS_FILE = STATE_DIR / "settings.json"
SCREENSHOT_DIR = STATE_DIR / "screenshots"

# 分心应用（不区分大小写，匹配 app_name）
DISTRACTION_APPS = [
    "YouTube", "Twitter", "Reddit", "Steam", "Discord",
    "抖音", "TikTok", "Bilibili", "哔哩哔哩",
    "Netflix", "Twitch", "Instagram", "Facebook",
    "微博", "小红书",
]

# 分心关键词（匹配 window_name 或 OCR text）
DISTRACTION_KEYWORDS = [
    "youtube.com", "twitter.com", "x.com", "reddit.com",
    "bilibili.com", "douyin.com", "tiktok.com",
    "netflix.com", "twitch.tv", "instagram.com",
    "weibo.com", "xiaohongshu.com",
]

DEFAULT_AI_PROVIDER = "anthropic"
DEFAULT_AI_MODEL = "claude-sonnet-4-20250514"
