const $ = (id) => document.getElementById(id);
let currentQuestion = null;
let timerInterval = null;
let timeLeft = 0;
let isSubmitting = false;
let tabSwitchCount = 0;
let fullscreenExitCount = 0;
let isQuizStarted = false;
let isFullscreenPaused = false;

async function getJSON(url, options = {}) {
  const r = await fetch(url, options);
  const data = await r.json();
  if (!r.ok) throw new Error(data.error || "Request failed");
  return data;
}

// Security logging to backend (Admin panel me show hoga)
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
  if (!banner) return;
  $("violationMsg").textContent = msg;
  banner.style.display = "flex";
  setTimeout(() => { banner.classList.add("show"); }, 10);
}

$("dismissWarningBtn").addEventListener("click", () => {
  const banner = $("violationWarning");
  if (!banner) return;
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
      isFullscreenPaused = true;
      fullscreenExitCount++;
      stopTimer();

      const modal = $("fsModal");
      const title = $("fsModalTitle");
      const sub = $("fsModalSubtitle");
      const btn = $("enterFsBtn");

      if (title) title.textContent = "⚠️ Fullscreen Required!";
      if (sub) sub.innerHTML = `<span style="color:var(--danger); font-weight:700;">Quiz is paused!</span> You exited fullscreen (${fullscreenExitCount} time(s)). Click below to resume fullscreen.`;
      if (btn) btn.textContent = "RE-ENTER FULLSCREEN ⛶";

      modal.style.display = "flex";
      modal.style.opacity = "1";
      modal.style.pointerEvents = "auto";

      showViolationWarning(`Fullscreen exited (${fullscreenExitCount} time(s)). Logged to Admin.`);
      sendSecurityLog("FULLSCREEN_EXIT", `Exited fullscreen mode. Total: ${fullscreenExitCount}`);
    } else {
      isFullscreenPaused = false;
      const modal = $("fsModal");
      if (modal) modal.style.display = "none";
      
      if (currentQuestion && timeLeft > 0) {
        startTimer(timeLeft);
      } else {
        loadQuestion();
      }
    }
  }
});

// 1. Tab Switch Tracking (Logged to Admin Panel)
document.addEventListener("visibilitychange", () => {
  if (document.hidden && isQuizStarted) {
    tabSwitchCount++;
    showViolationWarning(`Tab switch detected (${tabSwitchCount} time(s))! Logged to Admin.`);
    sendSecurityLog("TAB_SWITCH", `User switched tab or minimized window. Total switches: ${tabSwitchCount}`);
  }
});

// 2. Block Screenshots & Snipping Tool Shortcuts
window.addEventListener("keydown", (e) => {
  if (!isQuizStarted) return;

  // PrintScreen
  if (e.key === "PrintScreen" || e.keyCode === 44) {
    e.preventDefault();
    showViolationWarning("⚠️ Screenshots are prohibited during the quiz!");
    sendSecurityLog("SCREENSHOT_ATTEMPT", "PrintScreen captured attempt");
    return false;
  }

  // Windows + Shift + S (Snipping Tool) or Alt + PrtScn
  if ((e.shiftKey && (e.metaKey || e.key === "Meta") && e.key.toLowerCase() === "s") || (e.altKey && e.key === "PrintScreen")) {
    e.preventDefault();
    showViolationWarning("⚠️ Snipping tool is blocked during the quiz!");
    sendSecurityLog("SCREENSHOT_ATTEMPT", "Snipping tool shortcut attempted");
    return false;
  }

  // F12 / DevTools
  if (
    e.key === "F12" ||
    (e.ctrlKey && e.shiftKey && (e.key === "I" || e.key === "i" || e.key === "J" || e.key === "j" || e.key === "C" || e.key === "c")) ||
    (e.ctrlKey && (e.key === "U" || e.key === "u"))
  ) {
    e.preventDefault();
    showViolationWarning("Developer tools are disabled!");
    sendSecurityLog("DEVTOOLS_ATTEMPT", `Attempted key: ${e.key}`);
    return false;
  }
});

// 3. Block Copy, Cut, Paste & Right Click
document.addEventListener("copy", (e) => {
  if (isQuizStarted) {
    e.preventDefault();
    showViolationWarning("Copying question text is disabled!");
    sendSecurityLog("COPY_ATTEMPT", "User tried copying text");
  }
});

document.addEventListener("cut", (e) => {
  if (isQuizStarted) {
    e.preventDefault();
    showViolationWarning("Cutting text is disabled!");
    sendSecurityLog("CUT_ATTEMPT", "User tried cutting text");
  }
});

document.addEventListener("paste", (e) => {
  if (isQuizStarted) {
    e.preventDefault();
    showViolationWarning("Pasting is disabled in the quiz arena!");
    sendSecurityLog("PASTE_ATTEMPT", "User tried pasting text");
  }
});

document.addEventListener("contextmenu", (e) => {
  if (isQuizStarted) {
    e.preventDefault();
    showViolationWarning("Right-click context menu is disabled!");
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

// 3-Stage Smart Quiz Loader
async function loadQuestion() {
  try {
    const data = await getJSON("/api/quiz");
    
    $("playerScore").textContent = `${data.current_score || 0} PTS`;
    
    // 1. Stage Waiting Room (Waiting for Admin to launch Stage simultaneously)
    if (data.status === "waiting_room") {
      stopTimer();
      isQuizActive = false;
      const sNum = data.stage;
      $("statusPill").textContent = `STAGE 0${sNum} WAITING`;
      $("roundLabel").textContent = "WAITING FOR ADMIN KICKOFF";
      $("progressBar").style.width = `${Math.round(((sNum - 1) / 3) * 100)}%`;
      $("questionCount").textContent = `STAGE 0${sNum} · ${data.stage_name.toUpperCase()}`;
      $("questionText").textContent = `⏳ Stage ${sNum} Waiting Room`;
      $("timer").textContent = "⏳";
      $("feedback").textContent = "";

      $("options").innerHTML = `
        <div style="background: radial-gradient(circle at 50% 20%, rgba(56, 189, 248, 0.12), rgba(15, 23, 42, 0.95)); border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 18px; padding: 34px 24px; text-align: center; margin-top: 10px; box-shadow: 0 15px 40px rgba(0,0,0,0.5);">
          <div style="font-size: 52px; margin-bottom: 12px; filter: drop-shadow(0 0 15px rgba(56,189,248,0.6)); animation: pulseNeon 2.5s infinite ease-in-out;">⏳</div>
          <h3 style="font-size: 24px; font-weight:800; color: var(--cyan); margin-bottom: 8px;">Waiting for Admin to Start Stage ${sNum}</h3>
          <p class="muted" style="max-width: 500px; margin: 0 auto 18px; font-size: 14px; line-height: 1.65; color:#cbd5e1;">
            ${data.message || `You are ready for Stage ${sNum}! The stage will start automatically for all participants once the Admin gives the command.`}
          </p>
          <div style="display:inline-flex; align-items:center; gap:8px; background:rgba(56,189,248,0.1); border:1px solid rgba(56,189,248,0.25); padding:8px 16px; border-radius:20px; font-size:12px; font-weight:700; color:var(--cyan);">
            <span class="live-dot"></span> Auto-Syncing with Host Room...
          </div>
        </div>
      `;

      // Auto-poll every 3 seconds to check if Admin has started the stage
      setTimeout(() => {
        if (!isQuizActive) loadQuestion();
      }, 3000);
      return;
    }

    // 1.5 Question Pacing Waiting Room (Waiting for Admin to Release Next Question)
    if (data.status === "waiting_for_next_question") {
      stopTimer();
      isQuizActive = false;
      const sNum = data.stage;
      $("statusPill").textContent = `STAGE 0${sNum} · Q${data.waiting_for_q} LOCKED`;
      $("roundLabel").textContent = "WAITING FOR QUESTION RELEASE";
      let progPercent = (data.answered_q / data.stage_total) * 100;
      $("progressBar").style.width = `${Math.min(100, progPercent)}%`;
      $("questionCount").textContent = `STAGE 0${sNum} · ${data.stage_name.toUpperCase()}`;
      $("questionText").textContent = `⏳ Question ${data.waiting_for_q} will start when Admin allows`;
      $("timer").textContent = "⏳";
      $("feedback").textContent = "";

      $("options").innerHTML = `
        <div style="background: radial-gradient(circle at 50% 20%, rgba(168, 85, 247, 0.12), rgba(15, 23, 42, 0.95)); border: 1px solid rgba(168, 85, 247, 0.35); border-radius: 18px; padding: 32px 22px; text-align: center; margin-top: 10px; box-shadow: 0 15px 40px rgba(0,0,0,0.5);">
          <div style="font-size: 50px; margin-bottom: 12px; filter: drop-shadow(0 0 15px rgba(168,85,247,0.6)); animation: pulseNeon 2.5s infinite ease-in-out;">⏸️</div>
          <h3 style="font-size: 22px; font-weight:800; color: #d8b4fe; margin-bottom: 8px;">Question ${data.answered_q} Submitted!</h3>
          <p class="muted" style="max-width: 500px; margin: 0 auto 18px; font-size: 14px; line-height: 1.65; color:#cbd5e1;">
            ${data.message || `Please wait on this screen. As soon as the Admin releases Question ${data.waiting_for_q}, it will appear here automatically for all participants.`}
          </p>
          <div style="display:inline-flex; align-items:center; gap:8px; background:rgba(168,85,247,0.12); border:1px solid rgba(168,85,247,0.3); padding:8px 16px; border-radius:20px; font-size:12px; font-weight:700; color:#d8b4fe;">
            <span class="live-dot" style="background:#c084fc; box-shadow:0 0 10px #c084fc;"></span> Listening for Admin Signal...
          </div>
        </div>
      `;

      // Auto-poll every 1.5 seconds to detect when admin clicks "RELEASE NEXT Q"
      setTimeout(() => {
        loadQuestion();
      }, 1500);
      return;
    }

    // 2. Participant Cutoff / Eliminated Screen
    if (data.status === "eliminated") {
      stopTimer();
      isQuizActive = false;
      $("statusPill").textContent = "EVALUATION COMPLETED";
      $("roundLabel").textContent = "STAGE CUTOFF";
      $("progressBar").style.width = "100%";
      $("questionCount").textContent = "ROUND CONCLUDED";
      $("questionText").textContent = `🏁 Thank you for competing in TECHNERD 2026!`;
      $("timer").textContent = "★";
      $("feedback").textContent = "";

      $("options").innerHTML = `
        <div style="background: radial-gradient(circle at 50% 20%, rgba(244, 63, 94, 0.12), rgba(15, 23, 42, 0.95)); border: 1px solid rgba(244, 63, 94, 0.35); border-radius: 18px; padding: 36px 24px; text-align: center; margin-top: 10px; box-shadow: 0 15px 40px rgba(0,0,0,0.5);">
          <div style="font-size: 52px; margin-bottom: 12px; filter: drop-shadow(0 0 15px rgba(244,63,94,0.6));">🎯</div>
          <h3 style="font-size: 26px; font-weight:800; color: #fda4af; margin-bottom: 8px;">Final Score: ${data.current_score} Points</h3>
          <p class="muted" style="max-width: 480px; margin: 0 auto 20px; font-size: 14px; line-height: 1.65; color:#cbd5e1;">
            ${data.message || 'Round completed. High competition cutoff reached. Your score and performance have been recorded on the live leaderboard.'}
          </p>
          <a href="/logout" class="btn ghost" style="padding:12px 24px; border-color:rgba(255,255,255,0.2);">RETURN TO HOME ➔</a>
        </div>
      `;
      return;
    }

    // 3. Stage Intermission Screen (Stage 2 or any non-topic stage kickoff)
    if (data.status === "stage_intro") {
      stopTimer();
      isQuizActive = false;
      const sNum = data.stage;
      $("statusPill").textContent = `STAGE 0${sNum} READY`;
      $("roundLabel").textContent = data.stage_title;
      $("progressBar").style.width = `${Math.round(((sNum - 1) / 3) * 100)}%`;
      $("questionCount").textContent = `STAGE 0${sNum} UNLOCKED`;
      $("questionText").textContent = `🎉 Welcome to Stage ${sNum}: ${data.stage_name}`;
      $("timer").textContent = "🚀";
      $("feedback").textContent = "";

      $("options").innerHTML = `
        <div style="background: rgba(14, 165, 233, 0.08); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 14px; padding: 28px 20px; text-align: center; margin-top: 10px; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
          <div style="font-size: 42px; margin-bottom: 10px;">⚡</div>
          <h3 style="font-size: 22px; color: var(--cyan); margin-bottom: 8px;">${data.stage_title}</h3>
          <p class="muted" style="max-width: 440px; margin: 0 auto; font-size: 14px; line-height: 1.6;">
            You have successfully completed ${data.prev_stage_name}! This round contains <strong>${data.question_count} Questions</strong>. Get ready!
          </p>
          <button type="button" class="btn primary" onclick="acknowledgeStage(${sNum})" style="margin-top: 20px; padding: 14px 28px; font-weight: 700; letter-spacing: 1px;">
            START STAGE ${sNum} NOW ➔
          </button>
        </div>
      `;
      return;
    }

    // 2. Stage Topic Selection Screen (e.g., Stage 3 Specialization)
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
      return;
    }

    // 2. All Stages Completed Screen
    if (data.status === "completed") {
      stopTimer();
      isQuizActive = false;
      $("statusPill").textContent = "ALL STAGES COMPLETED";
      $("roundLabel").textContent = "QUIZ CONQUERED";
      $("progressBar").style.width = "100%";
      $("questionCount").textContent = "3 OF 3 STAGES CLEARED";
      $("questionText").textContent = `🏆 Congratulations! You have conquered all 3 stages.`;
      $("options").innerHTML = `
        <div style="background: linear-gradient(135deg, rgba(14, 165, 233, 0.12), rgba(168, 85, 247, 0.12)); border: 1px solid var(--border); border-radius: 16px; padding: 34px 20px; text-align: center; margin-top: 15px; box-shadow: 0 15px 35px rgba(0,0,0,0.4);">
          <div style="font-size: 48px; margin-bottom: 12px; filter:drop-shadow(0 0 15px rgba(56,189,248,0.5));">🏆</div>
          <h3 style="font-size: 30px; font-weight:800; color: var(--cyan); margin-bottom: 6px;">Total Score: ${data.current_score} Points</h3>
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

    // 3. Question In Progress
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
    
    let baseProg = (data.stage - 1) * 33.3;
    let stageProg = ((data.stage_index - 1) / data.stage_total) * 33.3;
    $("progressBar").style.width = `${Math.min(100, baseProg + stageProg)}%`;
    
    $("questionCount").textContent = `${data.stage_title} · Q${data.stage_index}/${data.stage_total} (${q.points} PTS)`;
    $("questionText").textContent = q.question;
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

// Acknowledge starting a new stage section
async function acknowledgeStage(stageNum) {
  try {
    await fetch("/api/start-stage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stage: stageNum })
    });
    loadQuestion();
  } catch (e) {
    loadQuestion();
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

    if (res.correct) {
      if (clickedBtn) clickedBtn.classList.add("is-correct");
      $("feedback").textContent = `🎉 Correct! +${res.points} points awarded.`;
      $("feedback").className = "feedback correct";
    } else {
      if (clickedBtn) clickedBtn.classList.add("is-wrong");
      if (isTimeout) {
        $("feedback").textContent = `⏰ Time expired! Moving to next question...`;
      } else {
        $("feedback").textContent = `❌ Submitted. Moving to next question...`;
      }
      $("feedback").className = "feedback wrong";
    }

    setTimeout(() => {
      loadQuestion();
    }, 900);

  } catch (err) {
    $("feedback").textContent = err.message;
    setTimeout(loadQuestion, 1500);
  }
}

// Start Quiz Button
$("enterFsBtn").addEventListener("click", async () => {
  await requestFullScreen();
  $("fsModal").style.display = "none";
  isQuizStarted = true;
  isFullscreenPaused = false;
  
  if (!currentQuestion) {
    loadQuestion();
  } else if (timeLeft > 0) {
    startTimer(timeLeft);
  } else {
    loadQuestion();
  }
});
