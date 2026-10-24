const $ = (id) => document.getElementById(id);
let currentQuestion = null;
let timerInterval = null;
let timeLeft = 0;
let isSubmitting = false;
let tabSwitchCount = 0;
let fullscreenExitCount = 0;
let isQuizStarted = false;
let isFullscreenPaused = false;
let isScreenShareBlocked = false;

async function getJSON(url, options = {}) {
  const r = await fetch(url, options);
  const data = await r.json();
  if (!r.ok) throw new Error(data.error || "Request failed");
  return data;
}

// Security logging to backend
async function sendSecurityLog(eventType, details) {
  try {
    await fetch("/api/security-log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event: eventType, details: details })
    });
  } catch (e) {
    console.warn("Security log error:", e);
  }
}

function showViolationWarning(msg) {
  const banner = $("violationWarning");
  $("violationMsg").textContent = msg;
  banner.style.display = "flex";
  setTimeout(() => { banner.classList.add("show"); }, 10);
}

$("dismissWarningBtn").addEventListener("click", () => {
  const banner = $("violationWarning");
  banner.classList.remove("show");
  setTimeout(() => { banner.style.display = "none"; }, 300);
});

// Fullscreen Management
async function requestFullScreen() {
  const el = document.documentElement;
  try {
    if (el.requestFullscreen) {
      await el.requestFullscreen();
    } else if (el.mozRequestFullScreen) {
      await el.mozRequestFullScreen();
    } else if (el.webkitRequestFullscreen) {
      await el.webkitRequestFullscreen();
    } else if (el.msRequestFullscreen) {
      await el.msRequestFullscreen();
    }
  } catch (err) {
    console.warn("Fullscreen request:", err);
  }
}

function checkFullscreen() {
  return !!(document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement);
}

document.addEventListener("fullscreenchange", () => {
  const isFs = checkFullscreen();
  const badge = $("fsStatusBadge");
  if (badge) {
    badge.textContent = isFs ? "⛶ FULLSCREEN" : "⚠️ NOT FULLSCREEN";
    badge.className = isFs ? "fs-indicator active" : "fs-indicator inactive";
  }

  if (isQuizStarted) {
    if (!isFs) {
      // User exited fullscreen during the quiz
      isFullscreenPaused = true;
      fullscreenExitCount++;
      stopTimer();

      // Show Fullscreen Lock Overlay
      const modal = $("fsModal");
      const title = $("fsModalTitle");
      const sub = $("fsModalSubtitle");
      const btn = $("enterFsBtn");

      if (title) title.textContent = "⚠️ Fullscreen Required!";
      if (sub) sub.innerHTML = `<span style="color:var(--danger); font-weight:700;">Quiz is paused!</span> You exited fullscreen (${fullscreenExitCount} time(s)). You MUST re-enter fullscreen to resume your quiz.`;
      if (btn) btn.textContent = "RE-ENTER FULLSCREEN TO RESUME ⛶";

      modal.style.display = "flex";
      modal.style.opacity = "1";
      modal.style.pointerEvents = "auto";

      const msg = `Fullscreen mode exited (${fullscreenExitCount} time(s))! Quiz paused until fullscreen resumed.`;
      showViolationWarning(msg);
      sendSecurityLog("FULLSCREEN_EXIT", `Exited fullscreen mode. Total: ${fullscreenExitCount}`);
    } else {
      // Re-entered fullscreen
      isFullscreenPaused = false;
      const modal = $("fsModal");
      if (modal) modal.style.display = "none";
      
      // Resume timer if question active or refresh state
      if (currentQuestion && timeLeft > 0) {
        startTimer(timeLeft);
      } else {
        loadQuestion();
      }
    }
  }
});

// Anti-Cheat Events
document.addEventListener("visibilitychange", () => {
  if (document.hidden && isQuizStarted) {
    tabSwitchCount++;
    showViolationWarning(`Tab switch detected (${tabSwitchCount} time(s))!`);
    sendSecurityLog("TAB_SWITCH", `User switched tab. Total: ${tabSwitchCount}`);
  }
});

// Anti-Screenshare / Screen Recording Detection
function triggerScreenshareBlock(reason = "Screenshare or capture detected") {
  if (isScreenShareBlocked) return;
  isScreenShareBlocked = true;
  stopTimer();

  const blocker = $("screenShareBlocker");
  if (blocker) blocker.style.display = "flex";

  const quizArea = $("quizContainer");
  if (quizArea) quizArea.style.filter = "blur(18px) grayscale(80%)";

  sendSecurityLog("SCREENSHARE_ATTEMPT", reason);
}

function resolveScreenshareBlock() {
  if (!isScreenShareBlocked) return;
  isScreenShareBlocked = false;

  const blocker = $("screenShareBlocker");
  if (blocker) blocker.style.display = "none";

  const quizArea = $("quizContainer");
  if (quizArea) quizArea.style.filter = "none";

  if (currentQuestion && timeLeft > 0) {
    startTimer(timeLeft);
  }
}

// 1. Prevent Screen Capture API if triggered by apps
if (navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia) {
  const originalGetDisplayMedia = navigator.mediaDevices.getDisplayMedia.bind(navigator.mediaDevices);
  navigator.mediaDevices.getDisplayMedia = function() {
    triggerScreenshareBlock("Browser screen-capture API invoked");
    return Promise.reject(new DOMException("Screen sharing is restricted by Proctor policy.", "NotAllowedError"));
  };
}

// 2. Window Blur & Dual Monitor Screen-Share Detection
window.addEventListener("blur", () => {
  if (isQuizStarted) {
    // If user clicks on another monitor or discord/meet sharing overlay
    sendSecurityLog("WINDOW_BLUR", "Focus lost to external application / screen");
  }
});

// 3. Block Developer Tools & Screenshot Shortcuts
window.addEventListener("keydown", (e) => {
  if (!isQuizStarted) return;

  // PrintScreen Key
  if (e.key === "PrintScreen" || e.keyCode === 44) {
    e.preventDefault();
    triggerScreenshareBlock("PrintScreen / Screenshot captured");
    return false;
  }

  // Windows Key + Shift + S (Snipping Tool) or Alt + PrtScn
  if ((e.shiftKey && (e.metaKey || e.key === "Meta") && e.key.toLowerCase() === "s") || (e.altKey && e.key === "PrintScreen")) {
    e.preventDefault();
    triggerScreenshareBlock("Screen snippet or capture shortcut attempted");
    return false;
  }

  // Developer Tools: F12, Ctrl+Shift+I, Ctrl+Shift+J, Ctrl+U
  if (
    e.key === "F12" ||
    (e.ctrlKey && e.shiftKey && (e.key === "I" || e.key === "i" || e.key === "J" || e.key === "j" || e.key === "C" || e.key === "c")) ||
    (e.ctrlKey && (e.key === "U" || e.key === "u"))
  ) {
    e.preventDefault();
    sendSecurityLog("DEVTOOLS_ATTEMPT", `Attempted key: ${e.key}`);
    showViolationWarning("Developer tools and inspect element are disabled!");
    return false;
  }
});

document.addEventListener("copy", (e) => {
  if (isQuizStarted) {
    e.preventDefault();
    showViolationWarning("Copying text is restricted during the quiz!");
    sendSecurityLog("COPY_ATTEMPT", "Copy attempted");
  }
});

document.addEventListener("paste", (e) => {
  if (isQuizStarted) {
    e.preventDefault();
    showViolationWarning("Pasting is disabled in the quiz arena!");
    sendSecurityLog("PASTE_ATTEMPT", "Paste attempted");
  }
});

document.addEventListener("contextmenu", (e) => {
  if (isQuizStarted) {
    e.preventDefault();
    showViolationWarning("Right-click context menu is disabled for integrity!");
    sendSecurityLog("CONTEXT_MENU", "Right-click attempted");
  }
});

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
  const timerEl = $("timer");
  if (timerEl && timerEl.parentElement) {
    timerEl.parentElement.classList.remove("urgent");
  }
}

function startTimer(seconds) {
  stopTimer();
  timeLeft = seconds;
  const timerEl = $("timer");
  const timerBox = timerEl.parentElement;
  timerEl.textContent = String(timeLeft).padStart(2, "0");

  timerInterval = setInterval(() => {
    timeLeft--;
    if (timeLeft <= 5 && timeLeft > 0) {
      timerBox.classList.add("urgent");
    } else {
      timerBox.classList.remove("urgent");
    }

    if (timeLeft <= 0) {
      stopTimer();
      timerEl.textContent = "00";
      handleTimeout();
    } else {
      timerEl.textContent = String(timeLeft).padStart(2, "0");
    }
  }, 1000);
}

function handleTimeout() {
  if (!currentQuestion || isSubmitting) return;
  $("feedback").textContent = "⏰ Time is up! Moving to next question...";
  $("feedback").className = "feedback timeout";
  
  [...$("options").children].forEach(b => b.disabled = true);
  submitAnswer("timeout", null, true);
}

// Anti-AI / Anti-OCR Canvas Renderer (Defeats Gemini Live Vision / Screen Readers)
function renderAntiOcrQuestion(text) {
  const canvas = $("antiOcrCanvas");
  const wrapper = $("canvasQuestionWrapper");
  if (!canvas || !wrapper) return;

  const ctx = canvas.getContext("2d");
  const width = Math.min(840, window.innerWidth - 60);
  
  // Word wrap calculation
  ctx.font = "bold 20px 'Plus Jakarta Sans', system-ui, sans-serif";
  const words = text.split(" ");
  let lines = [];
  let currentLine = words[0];

  for (let i = 1; i < words.length; i++) {
    const word = words[i];
    const testLine = currentLine + " " + word;
    if (ctx.measureText(testLine).width < width - 60) {
      currentLine = testLine;
    } else {
      lines.push(currentLine);
      currentLine = word;
    }
  }
  lines.push(currentLine);

  const lineHeight = 32;
  const height = Math.max(120, lines.length * lineHeight + 48);

  // High DPI scaling
  const dpr = window.devicePixelRatio || 1;
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  canvas.style.width = width + "px";
  canvas.style.height = height + "px";
  ctx.scale(dpr, dpr);

  // Background
  const gradient = ctx.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, "#0c1527");
  gradient.addColorStop(1, "#111c35");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);

  // Subtle cryptographic micro-noise grid (Confuses Gemini / OCR Vision Models)
  ctx.strokeStyle = "rgba(56, 189, 248, 0.04)";
  ctx.lineWidth = 1;
  for (let x = 0; x < width; x += 16) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }
  for (let y = 0; y < height; y += 16) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }

  // Watermark micro-dots
  for (let i = 0; i < 40; i++) {
    ctx.fillStyle = "rgba(56, 189, 248, 0.06)";
    ctx.beginPath();
    ctx.arc((i * 37) % width, (i * 23) % height, 1.5, 0, Math.PI * 2);
    ctx.fill();
  }

  // Draw Text with slight contrast glow
  ctx.font = "bold 20px 'Plus Jakarta Sans', system-ui, sans-serif";
  ctx.fillStyle = "#f8fafc";
  ctx.shadowColor = "rgba(0,0,0,0.8)";
  ctx.shadowBlur = 4;

  lines.forEach((line, index) => {
    ctx.fillText(line, 24, 38 + (index * lineHeight));
  });

  wrapper.style.display = "block";
  $("questionText").style.display = "none"; // Hide raw HTML text to defeat DOM-scraping AI
}
async function loadQuestion() {
  try {
    const data = await getJSON("/api/quiz");
    
    // Update score
    $("playerScore").textContent = `${data.current_score || 0} PTS`;
    
    // 1. Topic Selection Screen (e.g., Stage 3 or any topic-gated stage)
    if (data.status === "topic_selection" || data.status === "stage3_topic_selection") {
      stopTimer();
      isQuizActive = false;
      const sNum = data.stage || 3;
      $("statusPill").textContent = `STAGE ${sNum} TOPIC`;
      $("roundLabel").textContent = data.stage_title || `STAGE 0${sNum} / SPECIALIZATION`;
      $("progressBar").style.width = `${Math.round(((sNum - 1) / (data.total_stages || 3)) * 100)}%`;
      $("questionCount").textContent = `STAGE ${sNum} UNLOCKED`;
      $("questionText").textContent = data.message || `Choose Your Specialization Domain for Stage ${sNum}`;
      $("timer").textContent = "★";
      $("feedback").textContent = "";

      let topicsHtml = `
        <div style="margin-top: 10px; display:flex; flex-direction:column; gap:12px;">
          <p class="muted" style="margin-bottom: 8px;">
            🎉 Great job completing the previous stage! Select one specialization topic below to unlock your questions:
          </p>
          <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:12px;">
      `;

      (data.available_topics || ["General"]).forEach(t => {
        topicsHtml += `
          <button type="button" class="option topic-select-btn" onclick="selectStage3Topic('${t}')" style="justify-content:center; text-align:center; padding:18px 14px; font-weight:700; border-color:var(--cyan);">
            <span>🚀 ${t}</span>
          </button>
        `;
      });

      topicsHtml += `</div></div>`;
      $("options").innerHTML = topicsHtml;
      const cWrap = $("canvasQuestionWrapper");
      if (cWrap) cWrap.style.display = "none";
      $("questionText").style.display = "block";
      return;
    }

    // 2. All 3 Stages Completed Screen
    if (data.status === "completed") {
      stopTimer();
      isQuizActive = false;
      const cWrap = $("canvasQuestionWrapper");
      if (cWrap) cWrap.style.display = "none";
      $("questionText").style.display = "block";
      $("statusPill").textContent = "ALL STAGES COMPLETED";
      $("roundLabel").textContent = "QUIZ CONQUERED";
      $("progressBar").style.width = "100%";
      $("questionCount").textContent = "3 OF 3 STAGES CLEARED";
      $("questionText").textContent = `🏆 Congratulations! You have conquered all 3 stages.`;
      $("options").innerHTML = `
        <div style="background: linear-gradient(135deg, rgba(14, 165, 233, 0.12), rgba(168, 85, 247, 0.12)); border: 1px solid var(--border); border-radius: 16px; padding: 34px 20px; text-align: center; margin-top: 15px; box-shadow: 0 15px 35px rgba(0,0,0,0.4);">
          <div style="font-size: 48px; margin-bottom: 12px; filter:drop-shadow(0 0 15px rgba(56,189,248,0.5));">🏆</div>
          <h3 style="font-size: 30px; font-family: 'Space Grotesk', sans-serif; color: var(--cyan); margin-bottom: 6px;">Total Score: ${data.current_score} Points</h3>
          <p class="muted" style="max-width: 460px; margin: 0 auto; font-size:14px;">
            Specialization Domain: <strong style="color:#ffffff;">${data.chosen_topic || 'Specialized Tech'}</strong><br>
            All stage answers and anti-cheat verification have been logged directly into the Admin Live Leaderboard.
          </p>
          <a href="/logout" class="btn primary" style="margin-top: 24px; padding:14px 24px;">RETURN TO HOME SCREEN ↗</a>
        </div>
      `;
      $("timer").textContent = "✔";
      $("feedback").textContent = "";
      return;
    }

    // 3. Question In Progress (Stage 1, 2, or 3)
    const q = data.question;
    if (!q) {
      $("feedback").textContent = data.message || "No questions found for this stage.";
      return;
    }
    isQuizActive = true;
    currentQuestion = q;
    isSubmitting = false;

    $("statusPill").textContent = `STAGE ${data.stage} ACTIVE`;
    $("roundLabel").textContent = data.stage_title;
    
    // Smooth multi-stage progress computation
    let baseProg = (data.stage - 1) * 33.3;
    let stageProg = ((data.stage_index - 1) / data.stage_total) * 33.3;
    $("progressBar").style.width = `${Math.min(100, baseProg + stageProg)}%`;
    
    $("questionCount").textContent = `${data.stage_title} · Q${data.stage_index}/${data.stage_total} (${q.points} PTS)`;
    
    // Render as Anti-OCR protected canvas to prevent Gemini AI screenshare reading
    renderAntiOcrQuestion(q.question);
    
    $("feedback").textContent = "";
    $("feedback").className = "feedback";

    // Populate Options
    $("options").innerHTML = "";
    ["a", "b", "c", "d"].forEach((key) => {
      const button = document.createElement("button");
      button.className = "option";
      button.type = "button";
      button.dataset.key = key;

      const badge = document.createElement("span");
      badge.className = "option-key";
      badge.textContent = key.toUpperCase();

      const label = document.createElement("span");
      label.textContent = q[key];

      button.append(badge, label);
      button.addEventListener("click", () => submitAnswer(key, button));
      $("options").append(button);
    });

    startTimer(q.seconds || 25);
  } catch (err) {
    $("feedback").textContent = err.message;
  }
}

// Stage 3 Topic Selection handler
async function selectStage3Topic(topicName) {
  try {
    const res = await getJSON("/api/choose-topic", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic: topicName })
    });
    if (res.ok) {
      loadQuestion();
    }
  } catch (err) {
    alert("Could not select topic: " + err.message);
  }
}

async function submitAnswer(choice, clickedBtn, isTimeout = false) {
  if (isSubmitting || !currentQuestion) return;
  isSubmitting = true;
  stopTimer();

  const optionsContainer = $("options");
  [...optionsContainer.children].forEach(b => b.disabled = true);
  if (clickedBtn) clickedBtn.classList.add("selected");

  try {
    const res = await getJSON("/api/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question_id: currentQuestion.id,
        choice: choice
      })
    });

    const correctBtn = optionsContainer.querySelector(`[data-key="${res.correct_answer}"]`);
    if (correctBtn) correctBtn.classList.add("is-correct");

    if (res.correct) {
      $("feedback").textContent = `🎉 Correct! +${res.points} points awarded.`;
      $("feedback").className = "feedback correct";
    } else {
      if (clickedBtn) clickedBtn.classList.add("is-wrong");
      if (isTimeout) {
        $("feedback").textContent = `⏰ Time expired! Option ${res.correct_answer.toUpperCase()} was the correct answer.`;
      } else {
        $("feedback").textContent = `❌ Incorrect! Option ${res.correct_answer.toUpperCase()} was the correct answer.`;
      }
      $("feedback").className = "feedback wrong";
    }

    setTimeout(() => {
      loadQuestion();
    }, 1400);

  } catch (err) {
    $("feedback").textContent = err.message;
    setTimeout(loadQuestion, 2000);
  }
}

// Fullscreen Modal Activation
$("enterFsBtn").addEventListener("click", async () => {
  await requestFullScreen();
  $("fsModal").style.display = "none";
  isQuizStarted = true;
  isFullscreenPaused = false;
  
  // Always trigger loadQuestion or refresh active question
  if (!currentQuestion) {
    loadQuestion();
  } else {
    // If returning to an existing question
    if (timeLeft > 0) {
      startTimer(timeLeft);
    } else {
      loadQuestion();
    }
  }
});
