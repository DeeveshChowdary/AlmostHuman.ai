let mediaRecorder;
let chunks = [];
let sessionId = null;

const sessionValue = document.getElementById("sessionValue");
const output = document.getElementById("output");
const player = document.getElementById("player");
const assistantTextEl = document.getElementById("assistantText");
const statusEl = document.getElementById("status");
const summaryOutputEl = document.getElementById("summaryOutput");
let currentAudioUrl = null;
player.muted = false;
player.volume = 1.0;

function setStatus(text) {
  statusEl.textContent = text;
}

function base64ToBlobUrl(base64, mimeType) {
  const binary = atob(base64);
  const len = binary.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  const blob = new Blob([bytes], { type: mimeType || "audio/mpeg" });
  return URL.createObjectURL(blob);
}

function setAudioSource(base64Audio, mimeType) {
  if (currentAudioUrl) {
    URL.revokeObjectURL(currentAudioUrl);
    currentAudioUrl = null;
  }
  if (!base64Audio) {
    player.removeAttribute("src");
    player.load();
    return false;
  }
  currentAudioUrl = base64ToBlobUrl(base64Audio, mimeType);
  player.src = currentAudioUrl;
  player.load();
  return true;
}

player.addEventListener("error", () => {
  const mediaErr = player.error;
  if (!mediaErr) {
    setStatus("Audio error: unknown media error");
    return;
  }
  setStatus(`Audio error code ${mediaErr.code}`);
});

function buildOutputForScreen(data) {
  const copy = { ...data };
  if (copy.tts_audio_b64) {
    copy.tts_audio_b64 = `<<base64 audio omitted: ${copy.tts_audio_b64.length} chars>>`;
  }
  return JSON.stringify(copy, null, 2);
}

async function startSession() {
  setStatus("Creating session...");
  const response = await fetch("/api/v1/voice-loop/sessions/start", { method: "POST" });
  const data = await response.json();
  sessionId = data.session_id;
  sessionValue.textContent = sessionId;
  setStatus("Session ready");
}

document.getElementById("newSession").onclick = async () => {
  try {
    await startSession();
    summaryOutputEl.textContent = "No summary generated yet.";
  } catch (err) {
    setStatus(`Session error: ${err}`);
  }
};

document.getElementById("summarize").onclick = async () => {
  try {
    if (!sessionId) {
      await startSession();
    }
    setStatus("Generating summary...");
    const response = await fetch(`/api/v1/voice-loop/sessions/${encodeURIComponent(sessionId)}/summary`, {
      method: "POST",
    });
    if (!response.ok) {
      const failure = await response.json().catch(() => ({}));
      throw new Error(failure.detail || `HTTP ${response.status}`);
    }
    const data = await response.json();
    summaryOutputEl.textContent = data.summary || "No summary available.";
    setStatus("Summary generated");
  } catch (err) {
    setStatus(`Summary error: ${err}`);
  }
};

document.getElementById("start").onclick = async () => {
  try {
    if (!sessionId) {
      await startSession();
    }
    setStatus("Requesting mic permission...");
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
    chunks = [];
    mediaRecorder.ondataavailable = (event) => chunks.push(event.data);
    mediaRecorder.start();
    setStatus("Recording...");
    document.getElementById("start").disabled = true;
    document.getElementById("stop").disabled = false;
  } catch (err) {
    setStatus(`Mic error: ${err}`);
  }
};

document.getElementById("stop").onclick = async () => {
  mediaRecorder.onstop = async () => {
    try {
      setStatus("Sending audio to voice loop...");
      const blob = new Blob(chunks, { type: "audio/webm" });
      const response = await fetch(`/api/v1/voice-loop/process?session_id=${encodeURIComponent(sessionId)}`, {
        method: "POST",
        headers: { "Content-Type": "audio/webm" },
        body: blob,
      });
      if (!response.ok) {
        const failure = await response.json().catch(() => ({}));
        throw new Error(failure.detail || `HTTP ${response.status}`);
      }
      const data = await response.json();
      output.textContent = buildOutputForScreen(data);

      const assistantText =
        data?.llm_response?.text ||
        data?.response ||
        data?.message ||
        "No assistant text in response.";
      assistantTextEl.textContent = assistantText;

      const hasAudio = setAudioSource(data.tts_audio_b64, data.tts_mime_type);
      if (hasAudio) {
        const provider = data.tts_provider || "unknown_provider";
        const b64Len = data.tts_audio_b64.length;
        try {
          await player.play();
          setStatus(`Done (provider: ${provider}, mime: ${data.tts_mime_type || "unknown"}, b64: ${b64Len})`);
        } catch (err) {
          setStatus(`Audio ready; click play (mime: ${data.tts_mime_type || "unknown"}, b64: ${b64Len}). ${err}`);
        }
      } else {
        setStatus("Done (no audio returned)");
      }
    } catch (err) {
      setStatus(`Process error: ${err}`);
    }
  };

  mediaRecorder.stop();
  document.getElementById("start").disabled = false;
  document.getElementById("stop").disabled = true;
};
