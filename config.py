"""时间小偷猎人 - 配置"""

SCREENPIPE_URL = "http://localhost:3030"

# 检查间隔（秒）
CHECK_INTERVAL = 30

# 查看最近多少分钟的活动
LOOKBACK_MINUTES = 5

# 摸鱼帧数超过此值才触发警告
DISTRACTION_THRESHOLD = 3

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

CLAUDE_MODEL = "claude-sonnet-4-20250514"
