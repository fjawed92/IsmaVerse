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
   VILLAIN CREATION LOADING SCREEN
===================================================== */
const VILLAIN_CREATION_MESSAGES = [
  { main: "PLOTTING THE EVIL PLAN...",   sub: "Every mastermind needs a scheme!" },
  { main: "STITCHING THE COSTUME...",    sub: "Picking the most sinister colours!" },
  { main: "CHARGING UP EVIL POWERS...", sub: "This villain is going to be unstoppable!" },
  { main: "BUILDING THE SECRET LAIR...", sub: "Location: top secret!" },
  { main: "DRAWING YOUR VILLAIN...",     sub: "The AI is sketching your bad guy now!" },
  { main: "ADDING VILLAINOUS DETAILS...", sub: "Those evil eyebrows are looking perfect!" },
  { main: "INKING THE OUTLINE...",       sub: "Bold lines for a bold villain!" },
  { main: "FINAL EVIL TOUCHES...",       sub: "Almost ready to cause chaos!" },
  { main: "UPLOADING TO ISMAVERSE...",   sub: "The world should be very afraid!" },
];

const initVillainCreationOverlay = () => {
  const form    = document.getElementById("villainCreationForm");
  const overlay = document.getElementById("villainCreationOverlay");
  if (!form || !overlay) return;

  const starsContainer = document.getElementById("vcoStars");
  if (starsContainer) {
    for (let i = 0; i < 40; i++) {
      const star = document.createElement("span");
      star.className = "hco-star";
      star.style.left   = `${Math.random() * 100}%`;
      star.style.width  = `${1 + Math.random() * 3}px`;
      star.style.height = star.style.width;
      const dur   = 6 + Math.random() * 10;
      const delay = Math.random() * 12;
      star.style.animationDuration = `${dur}s`;
      star.style.animationDelay    = `-${delay}s`;
      starsContainer.appendChild(star);
    }
  }

  let msgInterval   = null;
  let progInterval  = null;
  let currentMsgIdx = 0;
  let currentProg   = 0;

  const msgEl   = document.getElementById("vcoMessage");
  const subEl   = document.getElementById("vcoSubMsg");
  const barEl   = document.getElementById("vcoProgressBar");
  const labelEl = document.getElementById("vcoProgressLabel");

  const cycleMessage = () => {
    if (!msgEl) return;
    msgEl.classList.add("fading");
    setTimeout(() => {
      currentMsgIdx = (currentMsgIdx + 1) % VILLAIN_CREATION_MESSAGES.length;
      const { main, sub } = VILLAIN_CREATION_MESSAGES[currentMsgIdx];
      msgEl.textContent = main;
      if (subEl) subEl.textContent = sub;
      msgEl.classList.remove("fading");
    }, 300);
  };

  const tickProgress = () => {
    if (currentProg < 30)      currentProg += 3 + Math.random() * 4;
    else if (currentProg < 60) currentProg += 1.5 + Math.random() * 2.5;
    else if (currentProg < 85) currentProg += 0.8 + Math.random() * 1.2;
    else if (currentProg < 95) currentProg += 0.3 + Math.random() * 0.5;
    currentProg = Math.min(currentProg, 95);
    const pct = Math.round(currentProg);
    if (barEl)   barEl.style.width = `${pct}%`;
    if (labelEl) labelEl.textContent = `${pct}%`;
  };

  const onBeforeUnload = (e) => {
    e.preventDefault();
    e.returnValue = "Your villain is being created! Are you sure you want to leave?";
  };

  const showOverlay = () => {
    overlay.classList.add("is-visible");
    overlay.setAttribute("aria-hidden", "false");
    msgInterval  = setInterval(cycleMessage, 3500);
    progInterval = setInterval(tickProgress, 1200);
    window.addEventListener("beforeunload", onBeforeUnload);
  };

  form.addEventListener("submit", (e) => {
    if (!form.checkValidity()) return;
    // Skip the "AI is drawing" overlay when the user uploaded their own picture.
    const fileInput = form.querySelector('input[type="file"][name="image"]');
    if (fileInput && fileInput.files && fileInput.files.length > 0) return;
    setTimeout(showOverlay, 10);
    const submitBtn = document.getElementById("villainSubmitBtn");
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "😈 UNLEASHING... PLEASE WAIT 😈";
    }
  });
};


/* =====================================================
   HERO CREATION LOADING SCREEN
===================================================== */
const HERO_CREATION_MESSAGES = [
  { main: "ASSEMBLING COSTUME...",      sub: "Picking the perfect colours and style!" },
  { main: "ACTIVATING SUPERPOWERS...",  sub: "Charging up those incredible abilities!" },
  { main: "WRITING ORIGIN STORY...",    sub: "Making it more epic than ever!" },
  { main: "DRAWING YOUR HERO...",       sub: "The AI artist is sketching right now!" },
  { main: "ADDING ENERGY EFFECTS...",   sub: "Those power blasts are looking AMAZING!" },
  { main: "INKING THE OUTLINE...",      sub: "Bold lines for a bold hero!" },
  { main: "COLOURING THE COSTUME...",   sub: "Adding those awesome colours you chose!" },
  { main: "FINAL DETAILS...",           sub: "Almost done — your hero looks incredible!" },
  { main: "UPLOADING TO ISMAVERSE...",  sub: "Your legend is about to be born!" },
];

const initHeroCreationOverlay = () => {
  const form    = document.getElementById("heroCreationForm");
  const overlay = document.getElementById("heroCreationOverlay");
  if (!form || !overlay) return;

  // Spawn star particles
  const starsContainer = document.getElementById("hcoStars");
  if (starsContainer) {
    for (let i = 0; i < 40; i++) {
      const star = document.createElement("span");
      star.className = "hco-star";
      star.style.left   = `${Math.random() * 100}%`;
      star.style.width  = `${1 + Math.random() * 3}px`;
      star.style.height = star.style.width;
      const dur   = 6 + Math.random() * 10;
      const delay = Math.random() * 12;
      star.style.animationDuration = `${dur}s`;
      star.style.animationDelay    = `-${delay}s`;
      starsContainer.appendChild(star);
    }
  }

  let msgInterval   = null;
  let progInterval  = null;
  let currentMsgIdx = 0;
  let currentProg   = 0;

  const msgEl    = document.getElementById("hcoMessage");
  const subEl    = document.getElementById("hcoSubMsg");
  const barEl    = document.getElementById("hcoProgressBar");
  const labelEl  = document.getElementById("hcoProgressLabel");

  const cycleMessage = () => {
    if (!msgEl) return;
    msgEl.classList.add("fading");
    setTimeout(() => {
      currentMsgIdx = (currentMsgIdx + 1) % HERO_CREATION_MESSAGES.length;
      const { main, sub } = HERO_CREATION_MESSAGES[currentMsgIdx];
      msgEl.textContent = main;
      if (subEl) subEl.textContent = sub;
      msgEl.classList.remove("fading");
    }, 300);
  };

  const tickProgress = () => {
    // Fake progress: crawls fast early, slows near 95%
    if (currentProg < 30)      currentProg += 3 + Math.random() * 4;
    else if (currentProg < 60) currentProg += 1.5 + Math.random() * 2.5;
    else if (currentProg < 85) currentProg += 0.8 + Math.random() * 1.2;
    else if (currentProg < 95) currentProg += 0.3 + Math.random() * 0.5;
    // Never reach 100% (server will redirect when done)
    currentProg = Math.min(currentProg, 95);
    const pct = Math.round(currentProg);
    if (barEl)   barEl.style.width = `${pct}%`;
    if (labelEl) labelEl.textContent = `${pct}%`;
  };

  const showOverlay = () => {
    overlay.classList.add("is-visible");
    overlay.setAttribute("aria-hidden", "false");

    // Start message cycling every 3.5 s
    msgInterval  = setInterval(cycleMessage, 3500);
    // Start progress ticking every 1.2 s
    progInterval = setInterval(tickProgress, 1200);

    // Warn if user tries to leave
    window.addEventListener("beforeunload", onBeforeUnload);
  };

  const onBeforeUnload = (e) => {
    e.preventDefault();
    e.returnValue = "Your hero is being created! Are you sure you want to leave?";
  };

  form.addEventListener("submit", (e) => {
    // Let HTML5 built-in validation run first
    if (!form.checkValidity()) return;

    // Skip the "AI is drawing" overlay when the user uploaded their own picture.
    const fileInput = form.querySelector('input[type="file"][name="image"]');
    if (fileInput && fileInput.files && fileInput.files.length > 0) return;

    // Show overlay after a tiny tick so the browser can show validation UI
    setTimeout(showOverlay, 10);

    // Disable the submit button to prevent double-submission
    const submitBtn = document.getElementById("heroSubmitBtn");
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "⚡ CREATING... PLEASE WAIT ⚡";
    }
  });
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

  // Hero creation loading screen
  initHeroCreationOverlay();

  // Villain creation loading screen
  initVillainCreationOverlay();
});
