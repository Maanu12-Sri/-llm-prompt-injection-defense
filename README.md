# LLM Prompt Injection Defense

A multi-layer security middleware system that detects and blocks prompt injection attacks before they reach a Large Language Model (LLM). Built as a final year project for Cybersecurity specialization.

## Problem Statement

LLM-based applications are vulnerable to prompt injection attacks, where malicious users attempt to override system instructions, extract sensitive information, or generate harmful content. Existing defenses often rely on simple keyword matching, which is easily bypassed using obfuscation techniques like leetspeak or unicode tricks. This project builds a robust, multi-layered defense pipeline that combines a trained machine learning classifier with a real-time LLM-based intent classifier to catch both known and novel attack patterns — while ensuring zero computational cost is wasted on requests that are blocked early.

## Architecture

The system uses a 5-layer defense pipeline:

1. **Bypass Detector** — Detects unicode tricks, leetspeak, and encoding-based obfuscation attempts
2. **Dataset ML Classifier** — A trained scikit-learn model (TF-IDF + Logistic Regression) that recognizes known injection patterns instantly, without any API calls
3. **Guard Classifier (LLM)** — Uses Groq's Llama 3.3 model to understand intent and context, catching novel attacks that keyword-based systems would miss
4. **Secure Prompt Builder** — Wraps validated prompts with UUID-based delimiters and a hardened system prompt before sending to the main LLM
5. **Output Validator** — Scans the LLM's response for policy violations or system prompt leaks before returning it to the user

Harmful prompts are blocked at the earliest possible layer, ensuring zero LLM tokens are wasted on malicious requests.

## Features

- Real-time attack detection and blocking
- Live dashboard with attack statistics and category breakdown
- Searchable and filterable attack logs
- Per-IP rate limiting and session timeout
- Confidence scoring at every detection layer

## Tech Stack

- **Backend**: Python, Flask
- **LLM**: Groq API (Llama 3.3 70B)
- **Machine Learning**: scikit-learn (TF-IDF + Logistic Regression)
- **Frontend**: HTML, CSS, JavaScript, Chart.js

## Setup

1. Clone this repository
2. Install dependencies:
```bash
   pip install -r requirements.txt
```
3. Create a `.env` file with your Groq API key:
GROQ_API_KEY=your_key_here

4. Run the app:
```bash
   python app.py
```
5. Open `http://127.0.0.1:5000` in your browser

## Pages

- `/` — Test the defense system live
- `/dashboard` — View attack statistics and trends
- `/logs` — Full attack history with filters

## Author

Maanusri — Final Year Computer Science and Engineering (Cybersecurity Specialization)