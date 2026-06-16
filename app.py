import os
import time
from flask import Flask, request, jsonify, render_template
from collections import defaultdict
from groq import Groq
from dotenv import load_dotenv

from modules.guard_classifier import classify_prompt
from modules.bypass_detector import detect_bypass, normalize_text
from modules.prompt_builder import build_secure_prompt
from modules.output_validator import validate_output
from modules.attack_logger import log_attempt, get_logs, get_stats
from modules.dataset_classifier import classify_with_dataset

load_dotenv()
app = Flask(__name__)

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

attempt_counts = defaultdict(int)
request_counts = defaultdict(list)
block_timestamps = defaultdict(float)

MAX_ATTEMPTS = 5
MAX_REQUESTS_PER_MINUTE = 20
SESSION_RESET_SECONDS = 300
CONFIDENCE_THRESHOLD = 0.75
MAX_PROMPT_LENGTH = 1000

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/logs")
def logs():
    return render_template("logs.html")

@app.route("/api/stats", methods=["GET"])
def stats():
    return jsonify(get_stats())

@app.route("/api/logs", methods=["GET"])
def get_attack_logs():
    return jsonify(get_logs())

@app.route("/api/process", methods=["POST"])
def process():
    data = request.json
    user_prompt = data.get("prompt", "").strip()
    ip = request.remote_addr
    now = time.time()

    if not user_prompt:
        return jsonify({"error": "Prompt is required"}), 400

    # Rate limiting
    request_counts[ip] = [t for t in request_counts[ip] if now - t < 60]
    if len(request_counts[ip]) >= MAX_REQUESTS_PER_MINUTE:
        return jsonify({
            "status": "blocked",
            "stage": "rate_limiter",
            "reason": "Too many requests. Please wait 1 minute."
        }), 200
    request_counts[ip].append(now)

    # Session reset after timeout
    if attempt_counts[ip] >= MAX_ATTEMPTS:
        if now - block_timestamps[ip] > SESSION_RESET_SECONDS:
            attempt_counts[ip] = 0
        else:
            remaining = int(SESSION_RESET_SECONDS - (now - block_timestamps[ip]))
            return jsonify({
                "status": "session_blocked",
                "stage": "session_limiter",
                "reason": f"Session blocked. Try again in {remaining} seconds."
            }), 200

    # Long prompt protection
    if len(user_prompt) > MAX_PROMPT_LENGTH:
        log_attempt(ip, user_prompt, "input_validator", "long_prompt", "Prompt too long", "blocked")
        return jsonify({
            "status": "blocked",
            "stage": "input_validator",
            "reason": f"Prompt too long. Maximum {MAX_PROMPT_LENGTH} characters allowed."
        }), 200

    # --- Stage 1: Bypass detection ---
    bypass_result = detect_bypass(user_prompt)
    if bypass_result["is_bypass"]:
        attempt_counts[ip] += 1
        block_timestamps[ip] = now
        log_attempt(ip, user_prompt, "bypass_detector", "bypass_attempt", bypass_result["reason"], "blocked")
        return jsonify({
            "status": "blocked",
            "stage": "bypass_detector",
            "reason": bypass_result["reason"],
            "confidence": bypass_result.get("confidence", 0.95),
            "attempt_count": attempt_counts[ip]
        }), 200

    normalized = bypass_result.get("normalized_text", user_prompt)

    # --- Stage 2a: Dataset classifier ---
    dataset_result = classify_with_dataset(normalized)
    if dataset_result["verdict"] == "blocked" and dataset_result["confidence"] > 0.60:
        attempt_counts[ip] += 1
        block_timestamps[ip] = now
        log_attempt(ip, user_prompt, "dataset_classifier", "injection_pattern", dataset_result["reason"], "blocked")
        return jsonify({
            "status": "blocked",
            "stage": "dataset_classifier",
            "guard_result": {
                "verdict": "blocked",
                "category": "injection_pattern",
                "confidence": dataset_result["confidence"],
                "reason": dataset_result["reason"]
            },
            "reason": dataset_result["reason"],
            "attempt_count": attempt_counts[ip]
        }), 200

    # --- Stage 2b: Guard classifier ---
    guard_result = classify_prompt(normalized)

    if guard_result["verdict"] == "blocked":
        attempt_counts[ip] += 1
        block_timestamps[ip] = now
        log_attempt(ip, user_prompt, "guard_classifier", guard_result["category"], guard_result["reason"], "blocked")
        if attempt_counts[ip] >= MAX_ATTEMPTS:
            return jsonify({
                "status": "session_blocked",
                "stage": "guard_classifier",
                "reason": "Too many unsafe attempts. Session blocked for 5 minutes.",
                "attempt_count": attempt_counts[ip]
            }), 200
        return jsonify({
            "status": "blocked",
            "stage": "guard_classifier",
            "guard_result": guard_result,
            "reason": guard_result["reason"],
            "attempt_count": attempt_counts[ip]
        }), 200

    attempt_counts[ip] = 0

    # --- Stage 3: Build secure prompt ---
    prompt_result = build_secure_prompt(normalized)
    secure_prompt = prompt_result["secure_prompt"]

    # --- Stage 4: Groq LLM inference ---
    try:
        llm_response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": secure_prompt}],
            temperature=0.7,
            max_tokens=1024
        )
        raw_output = llm_response.choices[0].message.content.strip()
    except Exception as e:
        return jsonify({
            "status": "error",
            "stage": "llm_inference",
            "reason": f"LLM call failed: {str(e)}"
        }), 200

    # --- Stage 5: Output validation ---
    output_result = validate_output(raw_output)

    if not output_result["is_safe"]:
        log_attempt(ip, user_prompt, "output_validator", "unsafe_output", output_result["reason"], "blocked")

    log_attempt(ip, user_prompt, "complete", guard_result["category"], guard_result["reason"],
                "safe" if output_result["is_safe"] else "blocked")

    return jsonify({
        "status": "success" if output_result["is_safe"] else "blocked",
        "stage": "complete" if output_result["is_safe"] else "output_validator",
        "guard_result": guard_result,
        "final_response": output_result["sanitized_response"],
        "output_check": output_result["reason"]
    }), 200


@app.route('/api/logs', methods=['DELETE'])
def clear_logs():
    if os.path.exists('attack_logs.json'):
        os.remove('attack_logs.json')
    return jsonify({'status': 'cleared'})


if __name__ == "__main__":
    app.run(debug=True, port=5000)