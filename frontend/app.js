let mediaRecorder;
let chunks = [];
let sessionId = null;

const sessionValue = document.getElementById("sessionValue");
const output = document.getElementById("output");
const player = document.getElementById("player");
const statusEl = document.getElementById("status");

function setStatus(text) {
  statusEl.textContent = text;
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
  } catch (err) {
    setStatus(`Session error: ${err}`);
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
      const data = await response.json();
      output.textContent = JSON.stringify(data, null, 2);
      if (data.tts_audio_b64 && data.tts_mime_type) {
        player.src = `data:${data.tts_mime_type};base64,${data.tts_audio_b64}`;
        player.play().catch(() => {});
      }
      setStatus("Done");
    } catch (err) {
      setStatus(`Process error: ${err}`);
    }
  };

  mediaRecorder.stop();
  document.getElementById("start").disabled = false;
  document.getElementById("stop").disabled = true;
};

