const delay = ms => new Promise(r => setTimeout(r, ms));

function setPrompt(text) {
  document.getElementById('promptInput').value = text;
}

function clearAll() {
  document.getElementById('promptInput').value = '';
  document.getElementById('pipeline').classList.add('hidden');
  document.getElementById('result-card').classList.add('hidden');
  ['s1','s2','s3','s4','s5'].forEach(id => {
    const s = document.getElementById(id);
    s.className = 'stage';
    s.querySelector('.stage-detail').textContent = 'Waiting...';
  });
}

function setStage(id, status, text) {
  const s = document.getElementById(id);
  s.className = 'stage ' + status;
  if (text) s.querySelector('.stage-detail').textContent = text;
}

async function analyze() {
  const prompt = document.getElementById('promptInput').value.trim();
  if (!prompt) return;
  const btn = document.getElementById('submitBtn');
  btn.disabled = true;
  document.getElementById('pipeline').classList.remove('hidden');
  document.getElementById('result-card').classList.add('hidden');
  ['s1','s2','s3','s4','s5'].forEach(id => {
    document.getElementById(id).className = 'stage';
    document.getElementById(id).querySelector('.stage-detail').textContent = 'Waiting...';
  });

  setStage('s1', 'processing', 'Scanning for encoding tricks and obfuscation...');
  await delay(500);

  let data;
  try {
    const res = await fetch('/api/process', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt })
    });
    data = await res.json();
  } catch(e) {
    setStage('s1', 'blocked', 'Server connection failed.');
    btn.disabled = false;
    return;
  }

  const stage = data.stage;
  const status = data.status;

  // Rate limiter or session blocked
  if (stage === 'rate_limiter' || stage === 'session_limiter') {
    setStage('s1', 'blocked', data.reason);
    setStage('s2', 'skipped', 'Skipped.');
    setStage('s3', 'skipped', 'Skipped.');
    setStage('s4', 'skipped', 'Skipped.');
    setStage('s5', 'skipped', 'Skipped.');
    showResult('blocked', 'Access Limited', data.reason);
    btn.disabled = false;
    return;
  }

  // Input validator (long prompt)
  if (stage === 'input_validator') {
    setStage('s1', 'blocked', data.reason);
    setStage('s2', 'skipped', 'Skipped.');
    setStage('s3', 'skipped', 'Skipped.');
    setStage('s4', 'skipped', 'Skipped.');
    setStage('s5', 'skipped', 'Skipped.');
    showResult('blocked', 'Input Rejected', data.reason);
    btn.disabled = false;
    return;
  }

  // Bypass detector blocked
  if (stage === 'bypass_detector') {
    const conf = data.confidence ? (data.confidence * 100).toFixed(0) + '%' : '';
    setStage('s1', 'blocked', 'Bypass detected! Confidence: ' + conf + ' | ' + data.reason);
    setStage('s2', 'skipped', 'Skipped â€” blocked at bypass detection.');
    setStage('s3', 'skipped', 'Skipped.');
    setStage('s4', 'skipped', 'Skipped â€” no CPU used.');
    setStage('s5', 'skipped', 'Skipped.');
    showResult('blocked', 'Blocked at bypass detector', data.reason);
    btn.disabled = false;
    return;
  }

  // Bypass passed
  setStage('s1', 'success', 'No encoding tricks detected. Passed.');
  await delay(400);
  setStage('s2', 'processing', 'Sending to Groq LLM classifier...');
  await delay(900);

  // Guard classifier blocked
  if (stage === 'dataset_classifier') {
    const g = data.guard_result || {};
    const conf = g.confidence ? (g.confidence * 100).toFixed(0) + '%' : '99%';
    setStage('s2', 'blocked', 'Dataset ML classifier blocked | Confidence: ' + conf + ' | ' + data.reason);
    setStage('s3', 'skipped', 'Skipped — blocked before LLM.');
    setStage('s4', 'skipped', 'Skipped — zero CPU wasted.');
    setStage('s5', 'skipped', 'Skipped.');
    showResult('blocked', 'Blocked by dataset classifier', 'Category: injection_pattern\n\nReason: ' + data.reason);
    btn.disabled = false;
    return;
  }

  if (stage === 'guard_classifier') {
    const g = data.guard_result || {};
    const cat = g.category || 'unknown';
    const conf = g.confidence ? (g.confidence * 100).toFixed(0) + '%' : '99%';
    setStage('s2', 'blocked', 'Category: ' + cat + ' | Confidence: ' + conf + ' | ' + data.reason);
    setStage('s3', 'skipped', 'Skipped â€” blocked before LLM.');
    setStage('s4', 'skipped', 'Skipped â€” zero CPU wasted.');
    setStage('s5', 'skipped', 'Skipped.');
    showResult('blocked', 'Blocked by guard classifier', 'Category: ' + cat + '\n\nReason: ' + data.reason);
    btn.disabled = false;
    return;
  }

  // Session blocked after many attempts
  if (status === 'session_blocked') {
    setStage('s2', 'blocked', data.reason);
    setStage('s3', 'skipped', 'Skipped.');
    setStage('s4', 'skipped', 'Skipped.');
    setStage('s5', 'skipped', 'Skipped.');
    showResult('blocked', 'Session Blocked', data.reason);
    btn.disabled = false;
    return;
  }

  // Guard passed
  const g = data.guard_result || {};
  const cat = g.category || 'safe';
  const conf = g.confidence ? (g.confidence * 100).toFixed(0) + '%' : '95%';
  setStage('s2', 'success', 'Safe â€” Category: ' + cat + ' | Confidence: ' + conf);
  await delay(400);
  setStage('s3', 'processing', 'Wrapping with secure system prompt...');
  await delay(500);
  setStage('s3', 'success', 'Secure prompt built with UUID delimiter.');
  await delay(400);
  setStage('s4', 'processing', 'Calling Groq Llama 3...');
  await delay(1200);

  // LLM error
  if (stage === 'llm_inference') {
    setStage('s4', 'blocked', data.reason);
    showResult('blocked', 'LLM inference error', data.reason);
    btn.disabled = false;
    return;
  }

  setStage('s4', 'success', 'Response received from Groq.');
  await delay(400);
  setStage('s5', 'processing', 'Validating output for leaks...');
  await delay(500);

  if (status === 'blocked') {
    setStage('s5', 'blocked', data.output_check || 'Unsafe content in output.');
    showResult('blocked', 'Blocked at output validator', data.output_check);
  } else {
    setStage('s5', 'success', data.output_check || 'Output passed all safety checks.');
    showResult('safe', 'Safe response', data.final_response);
  }

  btn.disabled = false;
}

function showResult(type, title, body) {
  const card = document.getElementById('result-card');
  const header = document.getElementById('result-header');
  const bodyEl = document.getElementById('result-body');
  card.classList.remove('hidden');
  header.className = 'result-header ' + type;
  header.textContent = (type === 'safe' ? 'âœ“ ' : '✕ ') + title;
  bodyEl.textContent = body || '';
}