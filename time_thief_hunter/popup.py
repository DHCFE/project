"""弹窗系统 - pywebview + HTML/CSS 暗黑监控风格"""

import webview
import json

POPUP_HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<style>
  *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

  :root {
    --bg: #08080c;
    --surface: #111118;
    --surface2: #1a1a24;
    --red: #ff3b30;
    --red-glow: rgba(255, 59, 48, 0.12);
    --blue: #4a9eff;
    --text: #eaeaea;
    --dim: #555;
    --radius: 10px;
  }

  @font-face {
    font-family: 'Mono';
    src: local('SF Mono'), local('Menlo'), local('Consolas');
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg);
    color: var(--text);
    height: 100vh;
    overflow: hidden;
    -webkit-user-select: none;
    user-select: none;
  }

  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
    pointer-events: none;
    z-index: 9999;
  }

  .view { display: none; height: 100vh; flex-direction: column; }
  .view.active { display: flex; }
  button, input { -webkit-app-region: no-drag; }

  /* ═══ WARNING ═══ */
  #warning {
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 28px 32px;
    position: relative;
    background: radial-gradient(ellipse at top, var(--red-glow) 0%, transparent 60%);
  }

  @keyframes scan { from{top:-2px} to{top:100%} }
  #warning::after {
    content: '';
    position: absolute;
    left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent 5%, rgba(255,59,48,0.08) 50%, transparent 95%);
    animation: scan 4s linear infinite;
    pointer-events: none;
  }

  @keyframes fadeUp { from{opacity:0;transform:translateY(14px)} to{opacity:1;transform:translateY(0)} }
  @keyframes pulse { 0%,100%{opacity:.5} 50%{opacity:1} }

  .w-icon {
    font-size: 44px;
    margin-bottom: 10px;
    animation: fadeUp .4s ease both;
    filter: drop-shadow(0 0 24px rgba(255,59,48,0.4));
  }
  .w-badge {
    display: inline-block;
    background: var(--red);
    color: #fff;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 3px;
    margin-bottom: 14px;
    animation: fadeUp .4s ease .05s both;
    font-family: 'Mono', monospace;
  }
  .w-title {
    font-size: 24px;
    font-weight: 800;
    color: var(--text);
    margin-bottom: 6px;
    animation: fadeUp .4s ease .1s both;
    letter-spacing: 1px;
  }
  .w-app {
    font-size: 14px;
    color: var(--dim);
    margin-bottom: 6px;
    animation: fadeUp .4s ease .15s both;
  }
  .w-app b { color: var(--red); font-weight: 600; }
  .w-count {
    font-family: 'Mono', monospace;
    font-size: 11px;
    color: #444;
    margin-bottom: 24px;
    animation: fadeUp .4s ease .2s both;
  }
  .w-count span { color: var(--red); animation: pulse 2s ease-in-out infinite; }
  .w-buttons {
    display: flex;
    gap: 10px;
    animation: fadeUp .4s ease .25s both;
  }

  .btn {
    padding: 9px 22px;
    border: none;
    border-radius: var(--radius);
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all .15s ease;
    font-family: inherit;
    outline: none;
  }
  .btn-red {
    background: var(--red);
    color: #fff;
    box-shadow: 0 2px 12px rgba(255,59,48,0.25);
  }
  .btn-red:hover { background:#ff5147; box-shadow:0 4px 20px rgba(255,59,48,0.35); transform:translateY(-1px); }
  .btn-red:active { transform:translateY(0); }
  .btn-ghost {
    background: var(--surface2);
    color: #999;
    border: 1px solid #2a2a34;
  }
  .btn-ghost:hover { background:#222230; color:#ccc; border-color:#3a3a48; transform:translateY(-1px); }

  /* ═══ NEGOTIATION ═══ */
  .n-header {
    padding: 12px 16px;
    background: var(--surface);
    border-bottom: 1px solid #1e1e28;
    display: flex;
    align-items: center;
    gap: 9px;
    -webkit-app-region: drag;
  }
  .n-dot {
    width: 7px; height: 7px;
    background: var(--red);
    border-radius: 50%;
    animation: pulse 1.5s ease-in-out infinite;
    box-shadow: 0 0 6px rgba(255,59,48,0.4);
  }
  .n-title {
    font-size: 12px;
    font-weight: 600;
    color: var(--dim);
    letter-spacing: .5px;
    text-transform: uppercase;
    font-family: 'Mono', monospace;
  }
  .n-close {
    margin-left: auto;
    -webkit-app-region: no-drag;
    background: none;
    border: none;
    color: #444;
    font-size: 16px;
    cursor: pointer;
    padding: 2px 6px;
    border-radius: 4px;
    transition: all .15s;
  }
  .n-close:hover { color:var(--red); background:rgba(255,59,48,0.08); }

  .n-messages {
    flex: 1;
    overflow-y: auto;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .msg {
    max-width: 82%;
    padding: 10px 13px;
    border-radius: 10px;
    font-size: 13.5px;
    line-height: 1.55;
    animation: fadeUp .2s ease both;
  }
  .msg-hunter {
    align-self: flex-start;
    background: var(--surface);
    border-left: 2.5px solid var(--red);
  }
  .msg-user {
    align-self: flex-end;
    background: #121a28;
    border-right: 2.5px solid var(--blue);
  }
  .msg-tag {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin-bottom: 4px;
    font-family: 'Mono', monospace;
  }
  .msg-hunter .msg-tag { color: var(--red); }
  .msg-user .msg-tag { color: var(--blue); }

  @keyframes dot { 0%,80%{opacity:.15} 40%{opacity:.8} }
  .typing-dots { display:flex; gap:5px; padding:4px 0; }
  .typing-dots i {
    width:5px; height:5px;
    background:#555;
    border-radius:50%;
    animation:dot 1.4s infinite;
    font-style:normal;
    display:block;
  }
  .typing-dots i:nth-child(2){animation-delay:.2s}
  .typing-dots i:nth-child(3){animation-delay:.4s}

  .n-input {
    padding: 10px 14px;
    background: var(--surface);
    border-top: 1px solid #1e1e28;
    display: flex;
    gap: 8px;
  }
  .n-input input {
    flex: 1;
    background: var(--bg);
    border: 1px solid #2a2a34;
    border-radius: 8px;
    padding: 9px 13px;
    color: var(--text);
    font-size: 13.5px;
    font-family: inherit;
    outline: none;
    transition: border-color .2s, box-shadow .2s;
  }
  .n-input input:focus { border-color:var(--blue); box-shadow:0 0 0 2px rgba(74,158,255,0.1); }
  .n-input input::placeholder { color:#3a3a44; }
  .n-input input:disabled { opacity:.4; }
  .btn-send {
    background: var(--blue);
    color: #fff;
    padding: 9px 16px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    border: none;
    cursor: pointer;
    transition: all .15s;
  }
  .btn-send:hover { background:#5aadff; }
  .btn-send:disabled { opacity:.3; cursor:not-allowed; }

  .n-messages::-webkit-scrollbar { width:3px; }
  .n-messages::-webkit-scrollbar-track { background:transparent; }
  .n-messages::-webkit-scrollbar-thumb { background:#222; border-radius:3px; }
</style>
</head>
<body>

<div id="warning" class="view">
  <div class="w-icon">&#128680;</div>
  <div class="w-badge">&#9679; DETECTED</div>
  <div class="w-title">&#25235;&#21040;&#20320;&#20102;</div>
  <p class="w-app">&#20320;&#22312; <b id="w-app"></b> &#19978;&#25720;&#40060;&#65281;</p>
  <p class="w-count">&#21629;&#20013; <span id="w-count">0</span> &#24103;</p>
  <div class="w-buttons">
    <button class="btn btn-red" onclick="dismiss()">&#22909;&#21543;&#24178;&#27963;</button>
    <button class="btn btn-ghost" onclick="negotiate()">&#128591; &#27714;&#24773;</button>
  </div>
</div>

<div id="negotiation" class="view">
  <div class="n-header">
    <div class="n-dot"></div>
    <div class="n-title">negotiating...</div>
    <button class="n-close" onclick="closeChat()">&#10005;</button>
  </div>
  <div class="n-messages" id="msgs"></div>
  <div class="n-input">
    <input id="inp" placeholder="&#35828;&#28857;&#20160;&#20040;..." onkeydown="if(event.key==='Enter')sendMsg()" />
    <button class="btn-send" id="sbtn" onclick="sendMsg()">&#21457;&#36865;</button>
  </div>
</div>

<script>
  var curApp = '';

  function showWarning(app, count) {
    curApp = app;
    document.getElementById('w-app').textContent = app;
    document.getElementById('w-count').textContent = count;
    document.getElementById('warning').className = 'view active';
    document.getElementById('negotiation').className = 'view';
  }

  function dismiss() { pywebview.api.dismiss(); }

  function negotiate() {
    document.getElementById('warning').className = 'view';
    document.getElementById('negotiation').className = 'view active';
    document.getElementById('msgs').textContent = '';
    addMsg('hunter', '\u6211\u770b\u5230\u4f60\u5728\u7528 ' + curApp + '\u3002\u8bf4\u5427\uff0c\u6709\u4ec0\u4e48\u597d\u7684\u7406\u7531\uff1f');
    document.getElementById('inp').focus();
    pywebview.api.open_negotiation();
  }

  function addMsg(type, text) {
    var c = document.getElementById('msgs');
    var d = document.createElement('div');
    d.className = 'msg msg-' + type;

    var tag = document.createElement('div');
    tag.className = 'msg-tag';
    tag.textContent = type === 'hunter' ? '\u730e\u4eba' : '\u4f60';
    d.appendChild(tag);

    var body = document.createElement('span');
    body.textContent = text;
    d.appendChild(body);

    c.appendChild(d);
    c.scrollTop = c.scrollHeight;
  }

  function showTyping() {
    var c = document.getElementById('msgs');
    var d = document.createElement('div');
    d.className = 'msg msg-hunter';
    d.id = 'typing';

    var tag = document.createElement('div');
    tag.className = 'msg-tag';
    tag.textContent = '\u730e\u4eba';
    d.appendChild(tag);

    var dots = document.createElement('div');
    dots.className = 'typing-dots';
    for (var i = 0; i < 3; i++) {
      dots.appendChild(document.createElement('i'));
    }
    d.appendChild(dots);
    c.appendChild(d);
    c.scrollTop = c.scrollHeight;
  }

  function rmTyping() {
    var e = document.getElementById('typing');
    if (e) e.remove();
  }

  async function sendMsg() {
    var inp = document.getElementById('inp');
    var btn = document.getElementById('sbtn');
    var msg = inp.value.trim();
    if (!msg) return;

    inp.value = '';
    addMsg('user', msg);
    inp.disabled = true;
    btn.disabled = true;
    showTyping();

    try {
      var reply = await pywebview.api.send_message(msg);
      rmTyping();
      addMsg('hunter', reply);
    } catch(e) {
      rmTyping();
      addMsg('hunter', '(\u901a\u4fe1\u6545\u969c)');
    }

    inp.disabled = false;
    btn.disabled = false;
    inp.focus();
  }

  function closeChat() { pywebview.api.close_chat(); }
</script>
</body>
</html>
"""


class _Api:
    """JS - Python bridge"""

    def __init__(self, manager):
        self.m = manager

    def dismiss(self):
        self.m.is_showing = False
        self.m.window.hide()

    def open_negotiation(self):
        self.m.brain.start_negotiation({
            "app": self.m._cur_app,
            "duration": self.m._cur_count,
        })
        self.m.window.resize(500, 520)

    def send_message(self, message):
        return self.m.brain.negotiate(message)

    def close_chat(self):
        self.m.brain.reset()
        self.m.is_showing = False
        self.m.window.hide()
        self.m.window.resize(460, 300)


class PopupManager:
    def __init__(self, brain):
        self.brain = brain
        self.window = None
        self.is_showing = False
        self._cur_app = ""
        self._cur_count = 0

    def trigger_warning(self, app, count):
        self._cur_app = app
        self._cur_count = count
        self.is_showing = True
        self.window.resize(460, 300)
        self.window.evaluate_js(
            f"showWarning({json.dumps(app)}, {count})"
        )
        self.window.show()

    def start(self, background_func=None):
        api = _Api(self)
        self.window = webview.create_window(
            "",
            html=POPUP_HTML,
            js_api=api,
            width=460,
            height=300,
            hidden=True,
            on_top=True,
            background_color="#08080c",
            resizable=False,
            frameless=True,
            easy_drag=True,
        )
        webview.start(func=background_func, debug=False)
