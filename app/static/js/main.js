console.log("IsmaVerse loaded");

const PROGRESS_KEY = "ismaverseProgress";

const defaultProgress = {
  comicReads: 0,
  visitedCharacters: false,
  createdHero: false,
  visits: 0,
};

const loadProgress = () => {
  const stored = localStorage.getItem(PROGRESS_KEY);
  if (!stored) {
    return { ...defaultProgress };
  }
  try {
    return { ...defaultProgress, ...JSON.parse(stored) };
  } catch (error) {
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

  if (path.includes("/characters")) {
    progress.visitedCharacters = true;
  }

  if (path.includes("/characters/create")) {
    progress.createdHero = true;
  }

  if (path.includes("/comics")) {
    progress.comicReads += 1;
  }

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
  if (!badgeElements.length || badgeSource === "server") {
    return;
  }

  const unlocked = getUnlockedBadges(progress);

  badgeElements.forEach((badgeEl) => {
    const badgeId = badgeEl.dataset.badgeId;
    const isUnlocked = Boolean(unlocked[badgeId]);
    badgeEl.classList.toggle("is-locked", !isUnlocked);

    const statusEl = badgeEl.querySelector(".badge-status");
    if (statusEl) {
      statusEl.textContent = isUnlocked ? "Unlocked!" : "Locked";
    }
  });
};

document.addEventListener("DOMContentLoaded", () => {
  const badgeStrip = document.querySelector(".badge-strip");
  const badgeSource = badgeStrip?.dataset?.badgeSource;
  if (badgeSource === "server") {
    return;
  }

  const progress = updateProgressFromPage();
  updateBadgeStrip(progress);
});
