console.log("IsmaVerse loaded");

/* =====================================================
   BADGE TRACKING (Local Storage for anonymous users)
===================================================== */
const PROGRESS_KEY = "ismaverseProgress";

const defaultProgress = {
  comicReads: 0,
  visitedCharacters: false,
  createdHero: false,
  visits: 0,
};

const loadProgress = () => {
  const stored = localStorage.getItem(PROGRESS_KEY);
  if (!stored) return { ...defaultProgress };
  try {
    return { ...defaultProgress, ...JSON.parse(stored) };
  } catch {
    return { ...defaultProgress };
  }
};

const saveProgress = (progress) => {
  localStorage.setItem(PROGRESS_KEY, JSON.stringify(progress));
};

const updateProgressFromPage = () => {
  const progress = loadProgress();
  const path = window.location.pathname;
  progress.visits += 1;
  if (path.includes("/characters")) progress.visitedCharacters = true;
  if (path.includes("/characters/create")) progress.createdHero = true;
  if (path.includes("/comics")) progress.comicReads += 1;
  saveProgress(progress);
  return progress;
};

const getUnlockedBadges = (progress) => ({
  "comic-reader": progress.comicReads >= 3,
  "character-explorer": progress.visitedCharacters,
  "hero-maker": progress.createdHero,
  "secret-visitor": progress.visits >= 5,
});

const updateBadgeStrip = (progress) => {
  const badgeElements = document.querySelectorAll("[data-badge-id]");
  const badgeStrip = document.querySelector(".badge-strip");
  const badgeSource = badgeStrip?.dataset?.badgeSource;
  if (!badgeElements.length || badgeSource === "server") return;

  const unlocked = getUnlockedBadges(progress);
  badgeElements.forEach((badgeEl) => {
    const badgeId = badgeEl.dataset.badgeId;
    const isUnlocked = Boolean(unlocked[badgeId]);
    badgeEl.classList.toggle("is-locked", !isUnlocked);
    const statusEl = badgeEl.querySelector(".badge-status");
    if (statusEl) statusEl.textContent = isUnlocked ? "Unlocked!" : "Locked";
  });
};



/* =====================================================
   COMIC SOUND EFFECTS
===================================================== */
const SOUNDS = {
  boom: [160, 80, 0.18],
  pow: [300, 150, 0.12],
  click: [440, 330, 0.06],
  unlock: [523, 659, 0.1],
};

let audioCtx = null;

const getAudioCtx = () => {
  if (!audioCtx) {
    try {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    } catch {
      return null;
    }
  }
  return audioCtx;
};

const playSound = (name = "click") => {
  const ctx = getAudioCtx();
  if (!ctx) return;

  const [startFreq, endFreq, gain] = SOUNDS[name] || SOUNDS.click;

  const osc = ctx.createOscillator();
  const gainNode = ctx.createGain();

  osc.connect(gainNode);
  gainNode.connect(ctx.destination);

  osc.type = "square";
  osc.frequency.setValueAtTime(startFreq, ctx.currentTime);
  osc.frequency.exponentialRampToValueAtTime(endFreq, ctx.currentTime + 0.15);

  gainNode.gain.setValueAtTime(gain, ctx.currentTime);
  gainNode.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.2);

  osc.start(ctx.currentTime);
  osc.stop(ctx.currentTime + 0.22);
};

const playUnlockFanfare = () => {
  const ctx = getAudioCtx();
  if (!ctx) return;

  const notes = [523, 659, 784, 1047];
  notes.forEach((freq, i) => {
    const osc = ctx.createOscillator();
    const gainNode = ctx.createGain();
    osc.connect(gainNode);
    gainNode.connect(ctx.destination);
    osc.type = "triangle";
    const start = ctx.currentTime + i * 0.12;
    osc.frequency.setValueAtTime(freq, start);
    gainNode.gain.setValueAtTime(0.12, start);
    gainNode.gain.exponentialRampToValueAtTime(0.001, start + 0.18);
    osc.start(start);
    osc.stop(start + 0.2);
  });
};


/* =====================================================
   REACTION BUTTON ANIMATION
===================================================== */
const addReactionAnimations = () => {
  document.querySelectorAll(".reaction-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const name = Math.random() > 0.5 ? "boom" : "pow";
      playSound(name);

      // Comic burst pop-up animation
      const burst = document.createElement("div");
      burst.className = "comic-sound-burst";
      burst.textContent = name === "boom" ? "BOOM!" : "POW!";
      btn.style.position = "relative";
      btn.appendChild(burst);
      setTimeout(() => burst.remove(), 700);
    });
  });
};


/* =====================================================
   GENERAL BUTTON SOUNDS
===================================================== */
const addButtonSounds = () => {
  document.querySelectorAll(".btn-comic-cta, .btn-comic-cta").forEach((btn) => {
    btn.addEventListener("mousedown", () => playSound("click"));
  });
};


/* =====================================================
   BADGE UNLOCK ANIMATION
===================================================== */
const checkBadgeUnlocks = () => {
  const previouslyUnlocked = JSON.parse(localStorage.getItem("ismaverseUnlocked") || "{}");
  const badgeStrip = document.querySelector(".badge-strip");
  if (!badgeStrip) return;

  document.querySelectorAll(".badge-item:not(.is-locked)").forEach((el) => {
    const id = el.dataset.badgeId;
    if (!previouslyUnlocked[id]) {
      previouslyUnlocked[id] = true;
      el.classList.add("badge-just-unlocked");
      playUnlockFanfare();
      setTimeout(() => el.classList.remove("badge-just-unlocked"), 1500);
    }
  });

  localStorage.setItem("ismaverseUnlocked", JSON.stringify(previouslyUnlocked));
};


/* =====================================================
   INIT
===================================================== */
document.addEventListener("DOMContentLoaded", () => {
  // Badge tracking (anonymous)
  const badgeStrip = document.querySelector(".badge-strip");
  const badgeSource = badgeStrip?.dataset?.badgeSource;
  if (badgeSource !== "server") {
    const progress = updateProgressFromPage();
    updateBadgeStrip(progress);
  }

  // Check for newly unlocked badges
  setTimeout(checkBadgeUnlocks, 300);

  // Sounds
  addReactionAnimations();
  addButtonSounds();
});
