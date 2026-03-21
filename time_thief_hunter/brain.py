"""AI 谈判大脑 - Claude API"""

import anthropic
from time_thief_hunter.config import CLAUDE_MODEL


class AgentBrain:
    def __init__(self):
        self.client = anthropic.Anthropic()
        self.history = []
        self.system_prompt = ""

    def start_negotiation(self, context):
        """开始新一轮谈判"""
        self.history = []
        app = context.get("app", "未知应用")
        duration = context.get("duration", "?")

        self.system_prompt = f"""你是"时间小偷猎人"，一个严格但可以谈判的生产力监工。

当前状况：
- 用户被发现在用：{app}
- 摸鱼时长：约 {duration} 分钟

你的性格：
- 毒舌，讽刺，但本质上为用户好
- 可以被说服，但不轻易妥协
- 用户提出具体交换条件（"再玩5分钟，然后写完PR"）你可以考虑
- 回复简短有力，2-3句话
- 用中文

规则：
- 最多允许延长15分钟
- 用户必须提出具体交换条件
- 态度不好就更严格"""

    def negotiate(self, user_message):
        """发送一条谈判消息，返回 AI 回复"""
        self.history.append({"role": "user", "content": user_message})

        try:
            response = self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=200,
                system=self.system_prompt,
                messages=self.history,
            )
            reply = response.content[0].text
        except Exception as e:
            reply = f"（AI 暂时掉线了：{e}）"

        self.history.append({"role": "assistant", "content": reply})
        return reply

    def reset(self):
        self.history = []
        self.system_prompt = ""
