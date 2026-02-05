from flask import Flask, request, jsonify, abort
from datetime import datetime, timezone
import json, os, hashlib

app = Flask(__name__)

SECRET = os.environ.get("TRACK_KEY", "cambia_esta_clave")
LOG_FILE = os.environ.get("TRACK_LOG", "events.jsonl")
SALT = os.environ.get("TRACK_SALT", "otra_clave_para_hash")

def anon_id():
    # No guardamos IP. Creamos un id estable pero no reversible a partir de remote_addr + user-agent.
    base = (request.remote_addr or "") + "|" + (request.headers.get("User-Agent") or "")
    return hashlib.sha256((SALT + base).encode("utf-8")).hexdigest()[:16]

@app.post("/track")
def track():
    data = request.get_json(silent=True) or {}
    if data.get("key") != SECRET:
        abort(401)

    evt = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": data.get("event", "unknown"),
        "session": data.get("session", "unknown"),
        "meta": data.get("meta", {}),
        "origin": anon_id(),   # anonimizado (no IP)
    }

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(evt, ensure_ascii=False) + "\n")

    return jsonify({"ok": True})

@app.get("/stats")
def stats():
    key = request.args.get("key")
    if key != SECRET:
        abort(401)

    counts = {}
    total = 0
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                total += 1
                try:
                    obj = json.loads(line)
                    name = obj.get("event", "unknown")
                except Exception:
                    name = "bad_json"
                counts[name] = counts.get(name, 0) + 1
    except FileNotFoundError:
        pass

    return jsonify({"total": total, "counts": counts})
