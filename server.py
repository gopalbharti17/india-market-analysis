"""
server.py — Local web server for the India Market Analysis dashboard.

Usage:
    python server.py

Then open http://localhost:5000 in your browser.
Keep the terminal open while using the dashboard.
The "Run Analysis" button will trigger the full pipeline and refresh the page.
"""

import json
import queue
import threading
from datetime import datetime
from flask import Flask, Response, jsonify, send_file

app = Flask(__name__)

_run_lock = threading.Lock()
_log_queue: queue.Queue = queue.Queue()
_running = False


def _pipeline_thread():
    global _running
    import sys
    import io

    class QueueWriter(io.TextIOBase):
        def write(self, s):
            if s.strip():
                _log_queue.put(s.rstrip())
            return len(s)

    old_stdout = sys.stdout
    sys.stdout = QueueWriter()
    try:
        # Re-import fresh so config changes are picked up
        import importlib
        import main as m
        importlib.reload(m)
        m.run_stocks()
        m.run_mutual_funds()
        if m._stock_scored is not None and m._mf_scored is not None:
            import report as r
            importlib.reload(r)
            r.generate(
                stock_df=m._stock_scored,
                mf_df=m._mf_scored,
                stock_changes=m._stock_changes,
                mf_changes=m._mf_changes,
                run_ts=m._last_run_ts,
            )
        _log_queue.put("__DONE__")
    except Exception as e:
        _log_queue.put(f"ERROR: {e}")
        _log_queue.put("__DONE__")
    finally:
        sys.stdout = old_stdout
        _running = False


@app.route("/")
def index():
    try:
        return send_file("report.html")
    except FileNotFoundError:
        return """
        <html><body style="font-family:sans-serif;padding:40px;text-align:center">
        <h2>No report yet</h2>
        <p>Click the button below to run your first analysis.</p>
        <button onclick="fetch('/api/run',{method:'POST'}).then(()=>window.location.reload())"
          style="padding:12px 28px;font-size:1rem;background:#1a1a2e;color:#fff;
                 border:none;border-radius:8px;cursor:pointer">
          Run Analysis
        </button>
        </body></html>"""


@app.route("/api/run", methods=["POST"])
def api_run():
    global _running
    if _running:
        return jsonify({"status": "already_running"})
    with _run_lock:
        _running = True
        while not _log_queue.empty():
            _log_queue.get_nowait()
        t = threading.Thread(target=_pipeline_thread, daemon=True)
        t.start()
    return jsonify({"status": "started"})


@app.route("/api/stream")
def api_stream():
    """SSE endpoint — streams pipeline log lines to the browser."""
    def generate():
        while True:
            try:
                msg = _log_queue.get(timeout=60)
                yield f"data: {json.dumps(msg)}\n\n"
                if msg == "__DONE__":
                    break
            except queue.Empty:
                yield "data: \"__TIMEOUT__\"\n\n"
                break
    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/status")
def api_status():
    return jsonify({"running": _running})


if __name__ == "__main__":
    print("=" * 50)
    print("  India Market Analysis — Dashboard Server")
    print("  Open http://localhost:5000 in your browser")
    print("  Press Ctrl+C to stop")
    print("=" * 50)
    app.run(debug=False, port=5000, threaded=True)
