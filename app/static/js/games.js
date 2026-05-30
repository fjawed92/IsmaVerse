/* =====================================================
   ISMAVERSE — MINI-GAMES
   Memory Match + Coloring. Pure client-side. Reuses the
   Web Audio helpers exposed by main.js (window.playSound /
   window.playUnlockFanfare) and awards the game-player badge.
===================================================== */
(function () {
  "use strict";

  const sfx = (name) => { try { window.playSound && window.playSound(name); } catch (e) {} };
  const fanfare = () => { try { window.playUnlockFanfare && window.playUnlockFanfare(); } catch (e) {} };

  let badgeAwarded = false;
  const awardGameBadge = () => {
    if (badgeAwarded) return;
    badgeAwarded = true;
    // Logged-in users get the server badge; anonymous users get the
    // localStorage one (mirrors the existing badge dual-source pattern).
    fetch("/games/played", { method: "POST", headers: { "X-Requested-With": "XMLHttpRequest" } })
      .catch(() => {});
    try {
      const unlocked = JSON.parse(localStorage.getItem("ismaverseUnlocked") || "{}");
      unlocked["game-player"] = true;
      localStorage.setItem("ismaverseUnlocked", JSON.stringify(unlocked));
    } catch (e) {}
  };

  /* ---------- shuffle helper ---------- */
  const shuffle = (arr) => {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  };

  /* =====================================================
     MEMORY MATCH
  ===================================================== */
  const MEMORY_FACES = ["🦸", "🦹", "⚡", "🛡️", "🚀", "🌟", "💥", "🔥"];

  function initMemory() {
    const grid = document.getElementById("memoryGrid");
    if (!grid) return;

    const movesEl   = document.getElementById("memoryMoves");
    const matchesEl = document.getElementById("memoryMatches");
    const winEl     = document.getElementById("memoryWin");
    const finalEl   = document.getElementById("memoryFinalMoves");
    const restart   = document.getElementById("memoryRestart");

    let first = null, lock = false, moves = 0, matches = 0;

    function build() {
      grid.innerHTML = "";
      if (winEl) winEl.hidden = true;
      first = null; lock = false; moves = 0; matches = 0;
      if (movesEl) movesEl.textContent = "0";
      if (matchesEl) matchesEl.textContent = "0";

      const deck = shuffle(MEMORY_FACES.concat(MEMORY_FACES));
      deck.forEach((face) => {
        const card = document.createElement("button");
        card.type = "button";
        card.className = "memory-card";
        card.setAttribute("aria-label", "Memory card");
        card.dataset.face = face;
        card.innerHTML =
          '<span class="memory-card-inner">' +
            '<span class="memory-front">?</span>' +
            '<span class="memory-back">' + face + "</span>" +
          "</span>";
        card.addEventListener("click", () => flip(card));
        grid.appendChild(card);
      });
    }

    function flip(card) {
      if (lock || card.classList.contains("is-flipped") || card.classList.contains("is-matched")) return;
      card.classList.add("is-flipped");
      sfx("click");

      if (!first) { first = card; return; }

      moves += 1;
      if (movesEl) movesEl.textContent = String(moves);

      if (first.dataset.face === card.dataset.face) {
        first.classList.add("is-matched");
        card.classList.add("is-matched");
        sfx("pow");
        matches += 1;
        if (matchesEl) matchesEl.textContent = String(matches);
        first = null;
        if (matches === MEMORY_FACES.length) {
          fanfare();
          awardGameBadge();
          if (finalEl) finalEl.textContent = String(moves);
          if (winEl) winEl.hidden = false;
        }
      } else {
        lock = true;
        const a = first, b = card;
        setTimeout(() => {
          a.classList.remove("is-flipped");
          b.classList.remove("is-flipped");
          lock = false;
        }, 800);
        first = null;
      }
    }

    if (restart) restart.addEventListener("click", () => { sfx("click"); build(); });
    build();
  }

  /* =====================================================
     COLORING
  ===================================================== */
  const PALETTE = [
    "#ff2d2d", "#ff8a00", "#ffd400", "#22ff66", "#1e6bff",
    "#7a3cff", "#ff5ad6", "#00c2c2", "#7a4a25", "#111111", "#ffffff",
  ];

  // Outline scenes drawn directly on the canvas (no image assets needed).
  const SCENES = [
    function star(ctx, w, h) {
      ctx.beginPath();
      const cx = w / 2, cy = h / 2, R = Math.min(w, h) * 0.38, r = R * 0.45, spikes = 5;
      for (let i = 0; i < spikes * 2; i++) {
        const rad = (i % 2 === 0) ? R : r;
        const a = (Math.PI / spikes) * i - Math.PI / 2;
        const x = cx + Math.cos(a) * rad, y = cy + Math.sin(a) * rad;
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      ctx.closePath(); ctx.stroke();
    },
    function shield(ctx, w, h) {
      const cx = w / 2, top = h * 0.16, bw = w * 0.5;
      ctx.beginPath();
      ctx.moveTo(cx - bw / 2, top);
      ctx.lineTo(cx + bw / 2, top);
      ctx.lineTo(cx + bw / 2, h * 0.55);
      ctx.quadraticCurveTo(cx + bw / 2, h * 0.82, cx, h * 0.86);
      ctx.quadraticCurveTo(cx - bw / 2, h * 0.82, cx - bw / 2, h * 0.55);
      ctx.closePath(); ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(cx, top + 12); ctx.lineTo(cx, h * 0.8); ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(cx - bw / 2 + 10, h * 0.4); ctx.lineTo(cx + bw / 2 - 10, h * 0.4); ctx.stroke();
    },
    function bolt(ctx, w, h) {
      ctx.beginPath();
      ctx.moveTo(w * 0.55, h * 0.12);
      ctx.lineTo(w * 0.38, h * 0.52);
      ctx.lineTo(w * 0.52, h * 0.52);
      ctx.lineTo(w * 0.42, h * 0.88);
      ctx.lineTo(w * 0.66, h * 0.42);
      ctx.lineTo(w * 0.52, h * 0.42);
      ctx.lineTo(w * 0.62, h * 0.12);
      ctx.closePath(); ctx.stroke();
    },
  ];

  function initColoring() {
    const canvas = document.getElementById("coloringCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const paletteEl = document.getElementById("colorPalette");
    const brushEl   = document.getElementById("brushSize");
    const eraserBtn = document.getElementById("eraserBtn");
    const clearBtn  = document.getElementById("clearBtn");
    const sceneBtn  = document.getElementById("sceneBtn");
    const saveBtn   = document.getElementById("saveBtn");

    let color = "#ff2d2d";
    let erasing = false;
    let sceneIdx = 0;
    let drawing = false;
    let awarded = false;

    function drawScene() {
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.save();
      ctx.strokeStyle = "#111111";
      ctx.lineWidth = 6;
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      SCENES[sceneIdx % SCENES.length](ctx, canvas.width, canvas.height);
      ctx.restore();
    }

    function buildPalette() {
      PALETTE.forEach((c, i) => {
        const sw = document.createElement("button");
        sw.type = "button";
        sw.className = "color-swatch" + (i === 0 ? " is-active" : "");
        sw.style.background = c;
        sw.setAttribute("aria-label", "Color " + c);
        sw.addEventListener("click", () => {
          color = c; erasing = false;
          paletteEl.querySelectorAll(".color-swatch").forEach((s) => s.classList.remove("is-active"));
          sw.classList.add("is-active");
          if (eraserBtn) eraserBtn.classList.remove("is-active");
          sfx("click");
        });
        paletteEl.appendChild(sw);
      });
    }

    function pos(e) {
      const rect = canvas.getBoundingClientRect();
      const t = e.touches ? e.touches[0] : e;
      return {
        x: (t.clientX - rect.left) * (canvas.width / rect.width),
        y: (t.clientY - rect.top) * (canvas.height / rect.height),
      };
    }

    function stroke(e) {
      if (!drawing) return;
      e.preventDefault();
      const p = pos(e);
      const size = parseInt(brushEl ? brushEl.value : 18, 10);
      ctx.globalCompositeOperation = "source-over";
      ctx.fillStyle = erasing ? "#ffffff" : color;
      ctx.beginPath();
      ctx.arc(p.x, p.y, size / 2, 0, Math.PI * 2);
      ctx.fill();
      if (!awarded) { awarded = true; awardGameBadge(); }
    }

    function start(e) { drawing = true; stroke(e); }
    function end() { drawing = false; }

    canvas.addEventListener("mousedown", start);
    canvas.addEventListener("mousemove", stroke);
    window.addEventListener("mouseup", end);
    canvas.addEventListener("touchstart", start, { passive: false });
    canvas.addEventListener("touchmove", stroke, { passive: false });
    canvas.addEventListener("touchend", end);

    if (eraserBtn) eraserBtn.addEventListener("click", () => {
      erasing = !erasing;
      eraserBtn.classList.toggle("is-active", erasing);
      sfx("click");
    });
    if (clearBtn) clearBtn.addEventListener("click", () => { drawScene(); sfx("pow"); });
    if (sceneBtn) sceneBtn.addEventListener("click", () => { sceneIdx++; drawScene(); sfx("click"); });
    if (saveBtn) saveBtn.addEventListener("click", () => {
      sfx("pow");
      const link = document.createElement("a");
      link.download = "ismaverse-coloring.png";
      link.href = canvas.toDataURL("image/png");
      link.click();
    });

    buildPalette();
    drawScene();
  }

  window.IsmaGames = { initMemory, initColoring };
})();
