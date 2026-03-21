# 时间小偷猎人 Time Thief Hunter

> 一个运行在本地的 AI Agent，通过 Screenpipe 监控你的屏幕活动，发现摸鱼就弹窗警告，还能跟你谈判。

## 它能干什么

- **实时监控** — 每 30 秒通过 Screenpipe 检测你当前在用什么应用
- **摸鱼检测** — 发现你在刷 YouTube / Bilibili / Reddit / Twitter 等就触发警告
- **弹窗警告** — 暗黑监控风格的桌面弹窗，无法忽视
- **AI 谈判** — 点「求情」可以跟 Claude AI 谈判，但它很毒舌，你得拿出交换条件

## 前置要求

- Python >= 3.9
- [Screenpipe](https://github.com/mediar-ai/screenpipe) 运行中（本地 `localhost:3030`）
- Anthropic API Key（设置环境变量 `ANTHROPIC_API_KEY`）

## 安装

```bash
git clone https://github.com/DHCFE/project.git
cd project
pip install .
```

或者开发模式：

```bash
pip install -e .
```

## 使用

```bash
# 启动监控
time-thief-hunter

# 测试弹窗效果（不需要真的摸鱼）
time-thief-hunter --test

# 或者直接用 Python 运行
python -m time_thief_hunter
python -m time_thief_hunter --test
```

## 配置

编辑 `time_thief_hunter/config.py`：

```python
CHECK_INTERVAL = 30          # 检查间隔（秒）
LOOKBACK_MINUTES = 5         # 查看最近几分钟的活动
DISTRACTION_THRESHOLD = 3    # 命中几帧才触发警告

DISTRACTION_APPS = [         # 分心应用列表
    "YouTube", "Twitter", "Reddit", "Steam", ...
]
```

## 项目结构

```
time_thief_hunter/
├── main.py               # 入口 + 监控循环
├── popup.py              # pywebview 弹窗 (HTML/CSS/JS)
├── brain.py              # Claude AI 谈判大脑
├── screenpipe_client.py  # Screenpipe REST API 客户端
└── config.py             # 配置
```

## 工作原理

```
Screenpipe (屏幕录制 + OCR)
    ↓ REST API
监控循环 (每30秒查一次)
    ↓ 规则匹配
摸鱼检测 → 弹窗警告
              ↓ 用户点「求情」
          Claude AI 谈判
```

## 隐私

- 所有数据只通过本地 Screenpipe 获取，不上传任何屏幕内容
- AI 谈判时只发送应用名和摸鱼时长给 Claude API，不发送屏幕截图
- 你的屏幕内容永远不会离开你的电脑

## License

MIT
