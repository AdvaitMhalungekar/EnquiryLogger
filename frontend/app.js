/**
 * Voice Enquiry Recorder - Frontend Client Application
 * Handles MediaRecorder, live audio waveform, API communication, and state management.
 */

// Application State
const state = {
  mediaRecorder: null,
  audioChunks: [],
  recordingStartTime: null,
  timerInterval: null,
  audioContext: null,
  analyser: null,
  sourceNode: null,
  animationFrameId: null,
  enquiryTimestamp: null,
  currentTranscript: "",
  selectedTechnologies: new Set(),
  maxRecordingSeconds: 120, // 2 minutes limit
};

// DOM Elements
const elements = {
  // Sections
  guideSection: document.getElementById("guideSection"),
  recorderSection: document.getElementById("recorderSection"),
  reviewSection: document.getElementById("reviewSection"),
  successSection: document.getElementById("successSection"),

  // Recorder states
  stateIdle: document.getElementById("stateIdle"),
  stateRecording: document.getElementById("stateRecording"),
  stateProcessing: document.getElementById("stateProcessing"),

  // Buttons
  startRecordBtn: document.getElementById("startRecordBtn"),
  stopRecordBtn: document.getElementById("stopRecordBtn"),
  cancelRecordBtn: document.getElementById("cancelRecordBtn"),
  rerecordBtn: document.getElementById("rerecordBtn"),
  recordAnotherBtn: document.getElementById("recordAnotherBtn"),
  submitEnquiryBtn: document.getElementById("submitEnquiryBtn"),
  toggleTranscriptBtn: document.getElementById("toggleTranscriptBtn"),
  alertCloseBtn: document.getElementById("alertCloseBtn"),

  // Recording feedback
  recordingTimer: document.getElementById("recordingTimer"),
  visualizerCanvas: document.getElementById("visualizerCanvas"),
  processingStatusText: document.getElementById("processingStatusText"),
  submitSpinner: document.getElementById("submitSpinner"),

  // Alert
  alertBanner: document.getElementById("alertBanner"),
  alertIcon: document.getElementById("alertIcon"),
  alertMessage: document.getElementById("alertMessage"),
  missingNotice: document.getElementById("missingNotice"),

  // Transcript
  transcriptBody: document.getElementById("transcriptBody"),
  transcriptText: document.getElementById("transcriptText"),

  // Form Elements
  enquiryForm: document.getElementById("enquiryForm"),
  inputName: document.getElementById("inputName"),
  selectProfile: document.getElementById("selectProfile"),
  techChipsContainer: document.getElementById("techChipsContainer"),
  displayEnquiryTime: document.getElementById("displayEnquiryTime"),
  inputEnquiryTime: document.getElementById("inputEnquiryTime"),

  // Form Badges & Groups
  groupName: document.getElementById("groupName"),
  badgeName: document.getElementById("badgeName"),
  groupProfile: document.getElementById("groupProfile"),
  badgeProfile: document.getElementById("badgeProfile"),
  groupTech: document.getElementById("groupTech"),
  badgeTech: document.getElementById("badgeTech"),

  // Success summary
  summaryName: document.getElementById("summaryName"),
  summaryProfile: document.getElementById("summaryProfile"),
  summaryTech: document.getElementById("summaryTech"),
  summaryTime: document.getElementById("summaryTime"),
  summaryRowNumber: document.getElementById("summaryRowNumber"),
};

// ============================================================================
// Initialization & Event Listeners
// ============================================================================

document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  checkBrowserSupport();
});

function setupEventListeners() {
  elements.startRecordBtn.addEventListener("click", startRecording);
  elements.stopRecordBtn.addEventListener("click", stopRecording);
  elements.cancelRecordBtn.addEventListener("click", cancelRecording);
  elements.rerecordBtn.addEventListener("click", resetToRecordingMode);
  elements.recordAnotherBtn.addEventListener("click", resetToIdle);

  // Transcript accordion toggle
  elements.toggleTranscriptBtn.addEventListener("click", toggleTranscriptAccordion);

  // Form submit
  elements.enquiryForm.addEventListener("submit", handleFormSubmit);

  // Alert banner close
  elements.alertCloseBtn.addEventListener("click", dismissAlert);

  // Tech chips toggle
  elements.techChipsContainer.addEventListener("click", (e) => {
    const chip = e.target.closest(".chip-btn") || e.target.closest(".tech-chip");
    if (!chip) return;
    const tech = chip.dataset.tech;
    toggleTechnology(tech, chip);
  });

  // Real-time form input corrections remove error highlights
  elements.inputName.addEventListener("input", () => {
    if (elements.inputName.value.trim()) {
      elements.groupName.classList.remove("has-error");
      elements.badgeName.textContent = "Entered";
      elements.badgeName.classList.remove("missing");
      elements.badgeName.classList.remove("neutral");
      checkOverallMissingStatus();
    }
  });

  elements.selectProfile.addEventListener("change", () => {
    if (elements.selectProfile.value) {
      elements.groupProfile.classList.remove("has-error");
      elements.badgeProfile.textContent = "Selected";
      elements.badgeProfile.classList.remove("missing");
      elements.badgeProfile.classList.remove("neutral");
      checkOverallMissingStatus();
    }
  });
}

function checkBrowserSupport() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
    showAlert(
      "Your browser does not support audio recording via MediaRecorder. Please use a modern browser like Chrome, Firefox, Edge, or Safari.",
      "error"
    );
    elements.startRecordBtn.disabled = true;
    elements.startRecordBtn.style.opacity = "0.5";
    elements.startRecordBtn.style.cursor = "not-allowed";
  }
}

// ============================================================================
// Audio Recording Logic
// ============================================================================

async function startRecording() {
  dismissAlert();

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    // Capture Enquiry Timestamp at the moment recording starts
    state.enquiryTimestamp = formatCurrentTimestamp();

    // Determine audio MIME type
    const mimeTypes = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/ogg;codecs=opus",
      "audio/mp4",
      "audio/wav",
    ];
    let selectedMime = "";
    for (const type of mimeTypes) {
      if (MediaRecorder.isTypeSupported(type)) {
        selectedMime = type;
        break;
      }
    }

    state.audioChunks = [];
    state.mediaRecorder = selectedMime
      ? new MediaRecorder(stream, { mimeType: selectedMime })
      : new MediaRecorder(stream);

    state.mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        state.audioChunks.push(event.data);
      }
    };

    state.mediaRecorder.onstop = handleRecordingStopped;

    state.mediaRecorder.start(250); // collect chunks every 250ms
    state.recordingStartTime = Date.now();

    // Initialize Web Audio Visualizer
    initAudioVisualizer(stream);

    // Start Timer
    startRecordingTimer();

    // Switch UI to Recording state
    switchRecorderState("recording");

  } catch (err) {
    console.error("Microphone access error:", err);
    if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
      showAlert(
        "Microphone permission was denied. Please allow microphone access in your browser settings to record your voice note.",
        "error"
      );
    } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
      showAlert("No microphone found on your system. Please connect an audio input device.", "error");
    } else {
      showAlert(`Unable to access microphone: ${err.message || err}`, "error");
    }
  }
}

function stopRecording() {
  if (state.mediaRecorder && state.mediaRecorder.state !== "inactive") {
    state.mediaRecorder.stop();
  }
  cleanupAudioStream();
}

function cancelRecording() {
  if (state.mediaRecorder && state.mediaRecorder.state !== "inactive") {
    state.mediaRecorder.stop();
  }
  cleanupAudioStream();
  state.audioChunks = [];
  switchRecorderState("idle");
}

function cleanupAudioStream() {
  clearInterval(state.timerInterval);
  if (state.animationFrameId) {
    cancelAnimationFrame(state.animationFrameId);
  }
  if (state.audioContext && state.audioContext.state !== "closed") {
    state.audioContext.close().catch(() => {});
  }
  if (state.mediaRecorder && state.mediaRecorder.stream) {
    state.mediaRecorder.stream.getTracks().forEach((track) => track.stop());
  }
}

function startRecordingTimer() {
  elements.recordingTimer.textContent = "00:00";
  state.timerInterval = setInterval(() => {
    const elapsedSeconds = Math.floor((Date.now() - state.recordingStartTime) / 1000);
    const mins = String(Math.floor(elapsedSeconds / 60)).padStart(2, "0");
    const secs = String(elapsedSeconds % 60).padStart(2, "0");
    elements.recordingTimer.textContent = `${mins}:${secs}`;

    // Auto-stop at max limit (2 minutes)
    if (elapsedSeconds >= state.maxRecordingSeconds) {
      stopRecording();
      showAlert("Reached maximum 2-minute recording limit. Processing your audio note.", "warning");
    }
  }, 500);
}

// Live Canvas Waveform Visualizer
function initAudioVisualizer(stream) {
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    state.audioContext = new AudioCtx();
    state.analyser = state.audioContext.createAnalyser();
    state.analyser.fftSize = 64;
    state.sourceNode = state.audioContext.createMediaStreamSource(stream);
    state.sourceNode.connect(state.analyser);

    const canvas = elements.visualizerCanvas;
    const canvasCtx = canvas.getContext("2d");
    const bufferLength = state.analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    function draw() {
      state.animationFrameId = requestAnimationFrame(draw);
      state.analyser.getByteFrequencyData(dataArray);

      canvasCtx.clearRect(0, 0, canvas.width, canvas.height);

      const barWidth = (canvas.width / bufferLength) * 2;
      let x = 0;

      for (let i = 0; i < bufferLength; i++) {
        const barHeight = (dataArray[i] / 255) * (canvas.height - 8) + 4;

        canvasCtx.fillStyle = "#475569";
        canvasCtx.beginPath();
        canvasCtx.roundRect(x, canvas.height - barHeight, barWidth - 3, barHeight, [2, 2, 0, 0]);
        canvasCtx.fill();

        x += barWidth;
      }
    }

    draw();
  } catch (e) {
    console.warn("Visualizer init failed:", e);
  }
}

// ============================================================================
// Server Processing Call: POST /api/process
// ============================================================================

async function handleRecordingStopped() {
  if (state.audioChunks.length === 0) {
    switchRecorderState("idle");
    showAlert("No audio data recorded. Please try speaking again.", "warning");
    return;
  }

  const mimeType = state.mediaRecorder.mimeType || "audio/webm";
  const audioBlob = new Blob(state.audioChunks, { type: mimeType });

  switchRecorderState("processing");
  elements.processingStatusText.textContent = "Uploading audio & transcribing with Groq Whisper...";

  const formData = new FormData();
  const fileExt = mimeType.includes("mp4") ? "mp4" : mimeType.includes("wav") ? "wav" : "webm";
  formData.append("audio", audioBlob, `enquiry.${fileExt}`);
  formData.append("enquiry_time", state.enquiryTimestamp);

  try {
    const response = await fetch("/api/process", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      let errorMsg = `Server error (${response.status})`;
      try {
        const errorData = await response.json();
        errorMsg = errorData.detail || errorMsg;
      } catch (_) {}
      throw new Error(errorMsg);
    }

    const data = await response.json();
    populateConfirmationForm(data);

  } catch (err) {
    console.error("Processing failure:", err);
    switchRecorderState("idle");
    showAlert(`Processing failed: ${err.message}. Please check API keys or try again.`, "error");
  }
}

// ============================================================================
// Confirmation Review & Form Logic
// ============================================================================

function populateConfirmationForm(data) {
  state.currentTranscript = data.transcript || "";
  elements.transcriptText.textContent = state.currentTranscript || "No audible transcript detected.";

  // Populate Name
  const nameVal = data.name || "";
  elements.inputName.value = nameVal;
  updateFieldStatus(
    elements.groupName,
    elements.badgeName,
    Boolean(nameVal),
    nameVal ? "Extracted" : "Missing"
  );

  // Populate Profile Type
  const profileVal = data.profile_type || "";
  elements.selectProfile.value = profileVal;
  updateFieldStatus(
    elements.groupProfile,
    elements.badgeProfile,
    Boolean(profileVal),
    profileVal ? "Extracted" : "Missing"
  );

  // Populate Technologies
  state.selectedTechnologies.clear();
  const techs = Array.isArray(data.technologies) ? data.technologies : [];
  techs.forEach((t) => state.selectedTechnologies.add(t));
  renderSelectedTechnologies();
  updateFieldStatus(
    elements.groupTech,
    elements.badgeTech,
    state.selectedTechnologies.size > 0,
    state.selectedTechnologies.size > 0 ? "Extracted" : "Missing"
  );

  // Populate Enquiry Timestamp
  const timestamp = data.enquiry_time || state.enquiryTimestamp || formatCurrentTimestamp();
  elements.displayEnquiryTime.textContent = timestamp;
  elements.inputEnquiryTime.value = timestamp;

  // Show missing notice if any field is missing
  const hasMissing = !nameVal || !profileVal || state.selectedTechnologies.size === 0;
  if (hasMissing) {
    elements.missingNotice.classList.remove("hidden");
  } else {
    elements.missingNotice.classList.add("hidden");
  }

  // Hide recorder section and guide, show review form
  elements.recorderSection.classList.add("hidden");
  elements.reviewSection.classList.remove("hidden");
  elements.reviewSection.scrollIntoView({ behavior: "smooth" });
}

function updateFieldStatus(groupEl, badgeEl, isValid, labelText) {
  badgeEl.textContent = labelText;
  if (isValid) {
    groupEl.classList.remove("has-error");
    badgeEl.classList.remove("missing");
    badgeEl.classList.remove("neutral");
  } else {
    groupEl.classList.add("has-error");
    badgeEl.classList.add("missing");
  }
}

function toggleTechnology(tech, chipEl) {
  if (state.selectedTechnologies.has(tech)) {
    state.selectedTechnologies.delete(tech);
    chipEl.classList.remove("selected");
  } else {
    state.selectedTechnologies.add(tech);
    chipEl.classList.add("selected");
  }

  const hasTech = state.selectedTechnologies.size > 0;
  updateFieldStatus(
    elements.groupTech,
    elements.badgeTech,
    hasTech,
    hasTech ? "Selected" : "Missing"
  );

  checkOverallMissingStatus();
}

function renderSelectedTechnologies() {
  const chips = elements.techChipsContainer.querySelectorAll(".chip-btn, .tech-chip");
  chips.forEach((chip) => {
    const tech = chip.dataset.tech;
    if (state.selectedTechnologies.has(tech)) {
      chip.classList.add("selected");
    } else {
      chip.classList.remove("selected");
    }
  });
}

function checkOverallMissingStatus() {
  const nameVal = elements.inputName.value.trim();
  const profileVal = elements.selectProfile.value;
  const hasTech = state.selectedTechnologies.size > 0;

  if (nameVal && profileVal && hasTech) {
    elements.missingNotice.classList.add("hidden");
  } else {
    elements.missingNotice.classList.remove("hidden");
  }
}

function toggleTranscriptAccordion() {
  const isExpanded = elements.toggleTranscriptBtn.getAttribute("aria-expanded") === "true";
  elements.toggleTranscriptBtn.setAttribute("aria-expanded", !isExpanded);
  elements.toggleTranscriptBtn.classList.toggle("expanded", !isExpanded);
  elements.transcriptBody.classList.toggle("hidden", isExpanded);
}

// ============================================================================
// Form Submission: POST /api/submit
// ============================================================================

async function handleFormSubmit(e) {
  e.preventDefault();
  dismissAlert();

  const name = elements.inputName.value.trim();
  const profileType = elements.selectProfile.value;
  const technologies = Array.from(state.selectedTechnologies);
  const enquiryTime = elements.inputEnquiryTime.value || state.enquiryTimestamp;

  // Client-side validation check
  let hasErrors = false;
  if (!name) {
    elements.groupName.classList.add("has-error");
    hasErrors = true;
  }
  if (!profileType) {
    elements.groupProfile.classList.add("has-error");
    hasErrors = true;
  }
  if (technologies.length === 0) {
    elements.groupTech.classList.add("has-error");
    hasErrors = true;
  }

  if (hasErrors) {
    showAlert("Please fill in all required fields before saving.", "warning");
    return;
  }

  // Set submitting state
  setSubmitting(true);

  const payload = {
    name: name,
    profile_type: profileType,
    technologies: technologies,
    enquiry_time: enquiryTime,
  };

  try {
    const response = await fetch("/api/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const result = await response.json();

    if (!response.ok) {
      const errDetail = result.detail ? (typeof result.detail === "string" ? result.detail : JSON.stringify(result.detail)) : "Failed to save submission";
      throw new Error(errDetail);
    }

    // Show Success State
    showSuccessScreen(payload, result.sheet_row);

  } catch (err) {
    console.error("Submission failed:", err);
    showAlert(`Submission error: ${err.message}`, "error");
  } finally {
    setSubmitting(false);
  }
}

function setSubmitting(isSubmitting) {
  elements.submitEnquiryBtn.disabled = isSubmitting;
  if (isSubmitting) {
    elements.submitSpinner.classList.remove("hidden");
    elements.submitEnquiryBtn.querySelector(".btn-text").textContent = "Saving to Google Sheets...";
  } else {
    elements.submitSpinner.classList.add("hidden");
    elements.submitEnquiryBtn.querySelector(".btn-text").textContent = "Save to Google Sheets";
  }
}

function showSuccessScreen(data, sheetRow) {
  elements.summaryName.textContent = data.name;
  elements.summaryProfile.textContent = data.profile_type;
  elements.summaryTech.textContent = data.technologies.join(", ");
  elements.summaryTime.textContent = data.enquiry_time;
  elements.summaryRowNumber.textContent = sheetRow ? `Row #${sheetRow}` : "Appended";

  elements.reviewSection.classList.add("hidden");
  elements.successSection.classList.remove("hidden");
  elements.successSection.scrollIntoView({ behavior: "smooth" });
}

// ============================================================================
// State Reset Helpers
// ============================================================================

function resetToRecordingMode() {
  elements.reviewSection.classList.add("hidden");
  elements.recorderSection.classList.remove("hidden");
  switchRecorderState("idle");
  elements.recorderSection.scrollIntoView({ behavior: "smooth" });
}

function resetToIdle() {
  elements.successSection.classList.add("hidden");
  elements.reviewSection.classList.add("hidden");
  elements.recorderSection.classList.remove("hidden");
  switchRecorderState("idle");

  // Reset form inputs
  elements.enquiryForm.reset();
  state.selectedTechnologies.clear();
  renderSelectedTechnologies();
  dismissAlert();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function switchRecorderState(newState) {
  elements.stateIdle.classList.add("hidden");
  elements.stateRecording.classList.add("hidden");
  elements.stateProcessing.classList.add("hidden");

  if (newState === "idle") {
    elements.stateIdle.classList.remove("hidden");
  } else if (newState === "recording") {
    elements.stateRecording.classList.remove("hidden");
  } else if (newState === "processing") {
    elements.stateProcessing.classList.remove("hidden");
  }
}

// ============================================================================
// Utility Functions
// ============================================================================

function formatCurrentTimestamp() {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const hours = String(d.getHours()).padStart(2, "0");
  const mins = String(d.getMinutes()).padStart(2, "0");
  const secs = String(d.getSeconds()).padStart(2, "0");
  return `${year}-${month}-${day} ${hours}:${mins}:${secs}`;
}

function showAlert(message, type = "error") {
  elements.alertBanner.className = `alert-banner ${type}`;
  if (elements.alertIcon) {
    elements.alertIcon.textContent = "";
  }
  elements.alertMessage.textContent = message;
  elements.alertBanner.classList.remove("hidden");
}

function dismissAlert() {
  elements.alertBanner.classList.add("hidden");
}
