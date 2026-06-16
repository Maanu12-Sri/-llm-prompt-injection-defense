import json
import os
from datetime import datetime

LOG_FILE = "attack_logs.json"

def log_attempt(ip: str, prompt: str, stage: str, category: str, reason: str, verdict: str):
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip": ip,
        "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
        "stage": stage,
        "category": category,
        "reason": reason,
        "verdict": verdict
    }
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                logs = json.load(f)
        except:
            logs = []
    logs.insert(0, log_entry)
    logs = logs[:100]
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)
    return log_entry

def get_logs():
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def get_stats():
    logs = get_logs()
    total = len(logs)
    blocked = len([l for l in logs if l["verdict"] == "blocked"])
    safe = len([l for l in logs if l["verdict"] == "safe"])
    categories = {}
    for l in logs:
        cat = l["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "total": total,
        "blocked": blocked,
        "safe": safe,
        "categories": categories
    }