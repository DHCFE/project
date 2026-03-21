"""时间小偷猎人 - 主入口"""

import sys
import time
from config import (
    CHECK_INTERVAL, LOOKBACK_MINUTES,
    DISTRACTION_APPS, DISTRACTION_KEYWORDS, DISTRACTION_THRESHOLD,
)
from screenpipe_client import ScreenpipeClient
from brain import AgentBrain
from popup import PopupManager


def detect_distraction(activity_data):
    """检测是否在摸鱼（简单规则匹配）"""
    counts = {}

    for item in activity_data:
        content = item.get("content", {})
        app = content.get("app_name", "")
        window = content.get("window_name", "")

        hit = False
        for d in DISTRACTION_APPS:
            if d.lower() in app.lower():
                hit = True
                break
        if not hit:
            for k in DISTRACTION_KEYWORDS:
                if k.lower() in window.lower():
                    hit = True
                    break
        if hit:
            counts[app] = counts.get(app, 0) + 1

    if counts:
        worst = max(counts, key=counts.get)
        if counts[worst] >= DISTRACTION_THRESHOLD:
            return {"is_distracted": True, "app": worst, "count": counts[worst]}
    return {"is_distracted": False}


def main():
    test_mode = "--test" in sys.argv

    screenpipe = ScreenpipeClient()
    brain = AgentBrain()
    popup = PopupManager(brain)

    if test_mode:
        def test_fn():
            time.sleep(1)
            popup.trigger_warning("YouTube (测试)", 10)

        print("[测试模式] 1秒后弹出警告...")
        popup.start(background_func=test_fn)
    else:
        def monitor():
            print("时间小偷猎人已启动！")
            print(f"每 {CHECK_INTERVAL} 秒检查一次，监控最近 {LOOKBACK_MINUTES} 分钟")
            print("关闭终端或 Ctrl+C 退出\n")
            while True:
                if not popup.is_showing:
                    data = screenpipe.get_recent_activity(LOOKBACK_MINUTES)
                    result = detect_distraction(data)
                    if result["is_distracted"]:
                        print(f"[!] 摸鱼: {result['app']} ({result['count']} 帧)")
                        popup.trigger_warning(result["app"], result["count"])
                    else:
                        print("[ok] 正常工作中...")
                time.sleep(CHECK_INTERVAL)

        popup.start(background_func=monitor)


if __name__ == "__main__":
    main()
