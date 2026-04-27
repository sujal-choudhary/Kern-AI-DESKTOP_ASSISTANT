from flask import Flask, jsonify, request, render_template_string
import time

from config import WEB_HOST, WEB_PORT
from core.assistant_service import assistant_service

app = Flask(__name__)
_RATE_LIMIT_WINDOW_SECONDS = 10
_RATE_LIMIT_MAX_REQUESTS = 30
_CLIENT_REQUEST_LOG: dict[str, list[float]] = {}


def _rate_limit_ok(client_ip: str) -> bool:
    now = time.time()
    entries = _CLIENT_REQUEST_LOG.get(client_ip, [])
    entries = [ts for ts in entries if now - ts < _RATE_LIMIT_WINDOW_SECONDS]
    if len(entries) >= _RATE_LIMIT_MAX_REQUESTS:
        _CLIENT_REQUEST_LOG[client_ip] = entries
        return False
    entries.append(now)
    _CLIENT_REQUEST_LOG[client_ip] = entries
    return True

HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Karn Assistant Control Panel</title>
  <style>
    :root {
      --bg: #0b0f14;
      --panel: rgba(255,255,255,0.04);
      --panel2: rgba(255,255,255,0.06);
      --border: rgba(255,255,255,0.10);
      --text: rgba(255,255,255,0.92);
      --muted: rgba(255,255,255,0.70);
      --muted2: rgba(255,255,255,0.55);
      --accent: #6ea8ff;
      --good: #34d399;
      --bad: #f87171;
      --shadow: 0 10px 30px rgba(0,0,0,0.45);
      --radius: 14px;
      --radius2: 10px;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      --sans: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: var(--sans);
      background: radial-gradient(1200px 800px at 10% 0%, rgba(110,168,255,0.12), transparent 60%),
                  radial-gradient(1000px 700px at 90% 10%, rgba(52,211,153,0.10), transparent 55%),
                  var(--bg);
      color: var(--text);
    }
    .container { max-width: 1100px; margin: 0 auto; padding: 22px 18px 36px; }
    .topbar {
      display: flex; gap: 14px; align-items: center; justify-content: space-between;
      padding: 14px 16px; border: 1px solid var(--border); border-radius: var(--radius);
      background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.03));
      box-shadow: var(--shadow);
      position: sticky; top: 14px; z-index: 5; backdrop-filter: blur(10px);
    }
    .brand { display: flex; flex-direction: column; gap: 2px; }
    .brand h1 { margin: 0; font-size: 16px; letter-spacing: 0.2px; }
    .brand .sub { font-size: 12px; color: var(--muted); }
    .badge {
      display: inline-flex; align-items: center; gap: 8px;
      padding: 7px 10px; border-radius: 999px;
      background: var(--panel2); border: 1px solid var(--border);
      color: var(--muted);
      font-size: 12px;
    }
    .dot { width: 8px; height: 8px; border-radius: 999px; background: var(--bad); box-shadow: 0 0 0 3px rgba(248,113,113,0.15); }
    .dot.good { background: var(--good); box-shadow: 0 0 0 3px rgba(52,211,153,0.15); }

    .actions { display: flex; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }
    .btn {
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.06);
      color: var(--text);
      padding: 9px 12px;
      border-radius: 10px;
      cursor: pointer;
      transition: transform 0.05s ease, background 0.15s ease, border-color 0.15s ease;
      font-size: 13px;
      display: inline-flex; align-items: center; gap: 8px;
      user-select: none;
    }
    .btn:hover { background: rgba(255,255,255,0.09); border-color: rgba(255,255,255,0.18); }
    .btn:active { transform: translateY(1px); }
    .btn.primary { background: rgba(110,168,255,0.14); border-color: rgba(110,168,255,0.35); }
    .btn.primary:hover { background: rgba(110,168,255,0.18); }
    .btn.danger { background: rgba(248,113,113,0.12); border-color: rgba(248,113,113,0.28); }
    .btn.danger:hover { background: rgba(248,113,113,0.16); }

    .grid { margin-top: 14px; display: grid; grid-template-columns: 1.2fr 1fr; gap: 14px; }
    @media (max-width: 960px) { .grid { grid-template-columns: 1fr; } .actions { justify-content: flex-start; } }

    .card {
      background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.03));
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 14px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }
    .card h2 { margin: 0 0 10px; font-size: 14px; color: rgba(255,255,255,0.92); letter-spacing: 0.2px; }
    .card .hint { margin-top: 6px; color: var(--muted2); font-size: 12px; }

    .row { display: flex; gap: 10px; align-items: center; }
    .row.wrap { flex-wrap: wrap; }
    .input {
      flex: 1;
      padding: 10px 12px;
      border-radius: 12px;
      border: 1px solid var(--border);
      background: rgba(0,0,0,0.25);
      color: var(--text);
      outline: none;
      font-size: 13px;
    }
    .input::placeholder { color: rgba(255,255,255,0.35); }

    .response {
      margin-top: 10px;
      border: 1px dashed rgba(255,255,255,0.18);
      background: rgba(0,0,0,0.18);
      border-radius: 12px;
      padding: 10px 12px;
      color: var(--muted);
      font-family: var(--mono);
      font-size: 12px;
      white-space: pre-wrap;
      min-height: 42px;
    }

    .list { display: flex; flex-direction: column; gap: 10px; }
    .item {
      border: 1px solid rgba(255,255,255,0.10);
      background: rgba(0,0,0,0.18);
      border-radius: 12px;
      padding: 10px 12px;
    }
    .item .k { color: rgba(255,255,255,0.85); font-size: 12px; }
    .item .v { margin-top: 4px; color: var(--muted); font-size: 12px; white-space: pre-wrap; }
    .item .meta { margin-top: 6px; color: var(--muted2); font-size: 11px; font-family: var(--mono); }
    .empty { color: var(--muted2); font-size: 12px; padding: 6px 2px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="topbar">
      <div class="brand">
        <h1>Karn Assistant</h1>
        <div class="sub">Local control panel • Voice + automation + memory</div>
      </div>
      <div class="actions">
        <span class="badge" title="Current voice mode status">
          <span id="voiceDot" class="dot"></span>
          <span id="statusText">Loading…</span>
        </span>
        <button class="btn primary" onclick="startVoice()">Start Voice</button>
        <button class="btn danger" onclick="stopVoice()">Stop Voice</button>
        <button class="btn" onclick="refreshStatus()">Refresh</button>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <h2>Command</h2>
        <div class="row wrap">
          <input class="input" id="command" placeholder="Try: open youtube • summarize this page • when i say clean desktop, delete temp files" />
          <button class="btn primary" onclick="sendCommand()">Send</button>
        </div>
        <div class="hint">Tip: You can chain actions with “and then”, e.g. “open notepad and then type hello”.</div>
        <div id="response" class="response">—</div>
      </div>

      <div class="card">
        <h2>Learned commands</h2>
        <div id="learnedCommands" class="list"></div>
        <div class="hint">Teach: “when i say &lt;trigger&gt;, &lt;action&gt;”</div>
      </div>

      <div class="card">
        <h2>Offline Live Transcript</h2>
        <div class="item">
          <div class="k">Partial (live)</div>
          <div class="v" id="sttPartial">—</div>
          <div class="k" style="margin-top:8px;">Final transcript</div>
          <div class="v" id="sttFinal">—</div>
          <div class="meta" id="sttState">STT: unknown</div>
        </div>
        <div class="hint">Use this to verify what offline listening hears in real time.</div>
      </div>

      <div class="card">
        <h2>PowerShell (Confirm mode)</h2>
        <div class="row wrap">
          <input class="input" id="psCommand" placeholder="Example: Get-Process | Select -First 5" />
          <button class="btn" onclick="queuePowerShell()">Queue</button>
        </div>
        <div class="hint">This queues a command. You must confirm it: <span style="font-family: var(--mono);">confirm &lt;id&gt; [passphrase]</span></div>
        <div id="psPending" class="list" style="margin-top:10px;"></div>
      </div>

      <div class="card" style="grid-column: 1 / -1;">
        <h2>Recent memory</h2>
        <div id="memory" class="list"></div>
      </div>
    </div>
  </div>

<script>
async function refreshStatus() {
  const r = await fetch('/api/status');
  const data = await r.json();
  const voiceOn = !!data.voice_enabled;
  document.getElementById('statusText').innerText = voiceOn ? 'Voice ON' : 'Voice OFF';
  const dot = document.getElementById('voiceDot');
  dot.className = voiceOn ? 'dot good' : 'dot';

  const sttLive = data.stt_live || {};
  const partialText = (sttLive.partial || '').trim();
  const finalText = (sttLive.transcript || '').trim();
  const sttRunning = !!sttLive.running;
  document.getElementById('sttPartial').innerText = partialText || '—';
  document.getElementById('sttFinal').innerText = finalText || '—';
  document.getElementById('sttState').innerText = 'STT: ' + (sttRunning ? 'running' : 'stopped');

  const memory = document.getElementById('memory');
  memory.innerHTML = '';
  const memItems = (data.recent_memory || []).slice().reverse();
  if (!memItems.length) {
    memory.innerHTML = '<div class="empty">No memory yet. Try sending a command.</div>';
  }
  for (const item of memItems) {
    const div = document.createElement('div');
    div.className = 'item';
    div.innerHTML = '<div class="k">User</div><div class="v">' + (item.user || '') + '</div>'
                  + '<div class="k" style="margin-top:8px;">Assistant</div><div class="v">' + (item.assistant || '') + '</div>'
                  + (item.timestamp ? ('<div class="meta">' + item.timestamp + '</div>') : '');
    memory.appendChild(div);
  }

  const learned = document.getElementById('learnedCommands');
  learned.innerHTML = '';
  const commands = data.learned_commands || {};
  const keys = Object.keys(commands).sort((a,b) => a.localeCompare(b));
  if (!keys.length) {
    learned.innerHTML = '<div class="empty">No learned commands yet.</div>';
  }
  for (const key of keys) {
    const div = document.createElement('div');
    div.className = 'item';
    div.innerHTML = '<div class="k">Trigger</div><div class="v" style="font-family: var(--mono);">' + key + '</div>'
                  + '<div class="k" style="margin-top:8px;">Action</div><div class="v">' + commands[key] + '</div>';
    learned.appendChild(div);
  }

  const pending = document.getElementById('psPending');
  pending.innerHTML = '';
  const ps = data.pending_powershell || {};
  const psKeys = Object.keys(ps).sort((a,b) => a.localeCompare(b));
  if (!psKeys.length) {
    pending.innerHTML = '<div class="empty">No pending PowerShell commands.</div>';
  }
  for (const id of psKeys) {
    const item = ps[id];
    const risky = (item.risky === 'true');
    const div = document.createElement('div');
    div.className = 'item';
    div.innerHTML = '<div class="k">ID</div><div class="v" style="font-family: var(--mono);">' + id + '</div>'
                  + '<div class="k" style="margin-top:8px;">Command</div><div class="v" style="font-family: var(--mono);">' + (item.command || '') + '</div>'
                  + '<div class="meta">' + (risky ? 'RISKY (passphrase required)' : 'Normal') + '</div>'
                  + '<div class="meta">Run: confirm ' + id + (risky ? ' &lt;passphrase&gt;' : '') + '</div>';
    pending.appendChild(div);
  }
}

async function sendCommand() {
  const command = document.getElementById('command').value;
  if (!command) return;
  const r = await fetch('/api/command', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({command})
  });
  const data = await r.json();
  const text = data.response || data.error || '—';
  document.getElementById('response').innerText = text;
  refreshStatus();
}

async function startVoice() {
  await fetch('/api/voice/start', { method: 'POST' });
  refreshStatus();
}

async function stopVoice() {
  await fetch('/api/voice/stop', { method: 'POST' });
  refreshStatus();
}

document.getElementById('command').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') sendCommand();
});

document.getElementById('psCommand').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') queuePowerShell();
});

async function queuePowerShell() {
  const cmd = document.getElementById('psCommand').value;
  if (!cmd) return;
  const r = await fetch('/api/command', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({command: 'ps: ' + cmd})
  });
  const data = await r.json();
  document.getElementById('response').innerText = data.response || data.error || '—';
  refreshStatus();
}

refreshStatus();
setInterval(refreshStatus, 1200);
</script>
</body>
</html>
"""


@app.get("/")
def index():
    return render_template_string(HTML)


@app.post("/api/command")
def run_command():
    client_ip = request.remote_addr or "unknown"
    if not _rate_limit_ok(client_ip):
        return jsonify({"error": "rate limit exceeded"}), 429
    payload = request.get_json(silent=True) or {}
    command = (payload.get("command") or "").strip()
    if not command or len(command) > 1000:
        return jsonify({"error": "command is required"}), 400
    try:
        response = assistant_service.handle_text_command(command, speak_response=False)
        return jsonify({"response": response})
    except Exception:
        return jsonify({"error": "internal server error"}), 500


@app.post("/api/voice/start")
def start_voice():
    started = assistant_service.start_voice()
    return jsonify({"started": started, "voice_enabled": assistant_service.voice_enabled})


@app.post("/api/voice/stop")
def stop_voice():
    stopped = assistant_service.stop_voice()
    return jsonify({"stopped": stopped, "voice_enabled": assistant_service.voice_enabled})


@app.get("/api/status")
def status():
    return jsonify(assistant_service.status())


def run_web_panel() -> None:
    import logging

    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    app.logger.setLevel(logging.WARNING)
    app.run(host=WEB_HOST, port=WEB_PORT, debug=False, use_reloader=False, threaded=True)


if __name__ == "__main__":
    run_web_panel()
