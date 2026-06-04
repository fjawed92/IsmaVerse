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

  /* ---------- arcade score helpers ---------- */
  // Local best mirrors the badge dual-source pattern: anonymous players keep
  // a per-game best in localStorage; logged-in players also persist server-side.
  const GAME_BEST_KEY = "ismaverseGameBest";
  const readLocalBest = (game) => {
    try { return JSON.parse(localStorage.getItem(GAME_BEST_KEY) || "{}")[game] || 0; }
    catch (e) { return 0; }
  };
  const writeLocalBest = (game, score) => {
    try {
      const m = JSON.parse(localStorage.getItem(GAME_BEST_KEY) || "{}");
      if (score > (m[game] || 0)) {
        m[game] = score;
        localStorage.setItem(GAME_BEST_KEY, JSON.stringify(m));
      }
    } catch (e) {}
  };

  const bestEl = (game) => {
    const wrap = document.querySelector('[data-game="' + game + '"]');
    return wrap ? { wrap, value: wrap.querySelector("[data-best-value]") } : null;
  };

  const setBest = (game, value) => {
    const el = bestEl(game);
    if (el && el.value) {
      const shown = parseInt(el.value.textContent, 10) || 0;
      if (value > shown) el.value.textContent = String(value);
    }
  };

  // Show the local best on load for anonymous players (server best is rendered
  // server-side for logged-in players).
  const initBestDisplay = (game) => {
    const el = bestEl(game);
    if (el && el.wrap.dataset.bestSource !== "server") setBest(game, readLocalBest(game));
  };

  const submitScore = (game, score) => {
    writeLocalBest(game, score);
    setBest(game, score);
    fetch("/games/score", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
      body: JSON.stringify({ game: game, score: score }),
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d && d.ok) {
          if (d.level_up) fanfare();
          if (typeof d.best === "number") setBest(game, d.best);
        }
      })
      .catch(() => {});
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

  /* =====================================================
     POPPI JUMP  (flappy-style jumper)
  ===================================================== */
  function initPoppiJump() {
    const canvas = document.getElementById("poppiCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const W = canvas.width, H = canvas.height;
    const scoreEl = document.getElementById("poppiScore");
    const overlay = document.getElementById("poppiOverlay");

    const GRAVITY = 1500;       // px / s^2
    const FLAP = -430;          // px / s impulse
    const PIPE_GAP = 180;
    const PIPE_W = 70;
    const PIPE_SPEED = 190;     // px / s
    const PIPE_SPACING = 250;   // px between pipes

    let bird, pipes, score, running, awaitingStart, last, raf;

    function reset() {
      bird = { x: 120, y: H / 2, vy: 0, r: 16 };
      pipes = [];
      score = 0;
      running = false;
      awaitingStart = true;
      if (scoreEl) scoreEl.textContent = "0";
      spawnPipe(W + 40);
      draw();
    }

    function spawnPipe(x) {
      const margin = 70;
      const gapY = margin + Math.random() * (H - PIPE_GAP - margin * 2);
      pipes.push({ x: x, gapY: gapY, passed: false });
    }

    function flap() {
      if (awaitingStart) {
        reset();                 // fresh board on first play AND on replay
        awaitingStart = false;
        running = true;
        if (overlay) overlay.hidden = true;
        awardGameBadge();
        last = performance.now();
        raf = requestAnimationFrame(loop);
      }
      if (running) { bird.vy = FLAP; sfx("click"); }
    }

    function gameOver() {
      running = false;
      cancelAnimationFrame(raf);
      sfx("pow");
      submitScore("poppi-jump", score);
      if (overlay) {
        overlay.innerHTML =
          '<span class="burst">GAME OVER!</span>' +
          '<p class="fw-bold mt-2 mb-0">Score: ' + score + '<br>Tap to play again!</p>';
        overlay.hidden = false;
      }
      awaitingStart = true;
    }

    function loop(now) {
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;

      bird.vy += GRAVITY * dt;
      bird.y += bird.vy * dt;

      for (const p of pipes) p.x -= PIPE_SPEED * dt;
      if (pipes.length && pipes[pipes.length - 1].x < W - PIPE_SPACING) spawnPipe(W + PIPE_W);
      if (pipes.length && pipes[0].x < -PIPE_W) pipes.shift();

      for (const p of pipes) {
        if (!p.passed && p.x + PIPE_W < bird.x) {
          p.passed = true; score += 1; sfx("pow");
          if (scoreEl) scoreEl.textContent = String(score);
        }
      }

      // Collisions: floor / ceiling / pipes.
      if (bird.y + bird.r > H || bird.y - bird.r < 0) return gameOver();
      for (const p of pipes) {
        const inX = bird.x + bird.r > p.x && bird.x - bird.r < p.x + PIPE_W;
        const inGap = bird.y - bird.r > p.gapY && bird.y + bird.r < p.gapY + PIPE_GAP;
        if (inX && !inGap) return gameOver();
      }

      draw();
      if (running) raf = requestAnimationFrame(loop);
    }

    function draw() {
      ctx.fillStyle = "#9be7ff";
      ctx.fillRect(0, 0, W, H);
      // Pipes
      ctx.fillStyle = "#22aa44";
      ctx.strokeStyle = "#0d5e24";
      ctx.lineWidth = 4;
      for (const p of pipes) {
        ctx.fillRect(p.x, 0, PIPE_W, p.gapY);
        ctx.strokeRect(p.x, 0, PIPE_W, p.gapY);
        ctx.fillRect(p.x, p.gapY + PIPE_GAP, PIPE_W, H - p.gapY - PIPE_GAP);
        ctx.strokeRect(p.x, p.gapY + PIPE_GAP, PIPE_W, H - p.gapY - PIPE_GAP);
      }
      // Bird (a little frog/hero blob)
      ctx.font = (bird.r * 2.2) + "px serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("🐸", bird.x, bird.y);
    }

    window.addEventListener("keydown", (e) => {
      if (e.code === "Space" || e.key === " ") { e.preventDefault(); flap(); }
    });
    canvas.addEventListener("mousedown", (e) => { e.preventDefault(); flap(); });
    canvas.addEventListener("touchstart", (e) => { e.preventDefault(); flap(); }, { passive: false });

    initBestDisplay("poppi-jump");
    reset();
  }

  /* =====================================================
     SPACESHIP DODGE
  ===================================================== */
  function initSpaceship() {
    const canvas = document.getElementById("spaceCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const W = canvas.width, H = canvas.height;
    const scoreEl = document.getElementById("spaceScore");
    const overlay = document.getElementById("spaceOverlay");

    const SHIP_W = 44, SHIP_H = 40;
    const BASE_FALL = 200;      // px / s
    const SHIP_SPEED = 360;     // px / s for keyboard

    let ship, rocks, score, spawnTimer, running, awaitingStart, last, raf;
    let leftHeld = false, rightHeld = false;

    function reset() {
      ship = { x: W / 2, y: H - 70 };
      rocks = [];
      score = 0;
      spawnTimer = 0;
      running = false;
      awaitingStart = true;
      if (scoreEl) scoreEl.textContent = "0";
      draw();
    }

    function start() {
      if (!awaitingStart) return;
      reset();                 // fresh board on first play AND on replay
      awaitingStart = false;
      running = true;
      if (overlay) overlay.hidden = true;
      awardGameBadge();
      last = performance.now();
      raf = requestAnimationFrame(loop);
    }

    function gameOver() {
      running = false;
      cancelAnimationFrame(raf);
      sfx("pow");
      submitScore("spaceship", score);
      if (overlay) {
        overlay.innerHTML =
          '<span class="burst">CRASH!</span>' +
          '<p class="fw-bold mt-2 mb-0">Score: ' + score + '<br>Tap to fly again!</p>';
        overlay.hidden = false;
      }
      awaitingStart = true;
    }

    function loop(now) {
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;

      const fall = BASE_FALL + score * 4;   // gets faster as you survive
      if (leftHeld) ship.x -= SHIP_SPEED * dt;
      if (rightHeld) ship.x += SHIP_SPEED * dt;
      ship.x = Math.max(SHIP_W / 2, Math.min(W - SHIP_W / 2, ship.x));

      spawnTimer -= dt;
      if (spawnTimer <= 0) {
        const r = 18 + Math.random() * 16;
        rocks.push({ x: r + Math.random() * (W - r * 2), y: -r, r: r });
        spawnTimer = 0.55 + Math.random() * 0.4;
      }

      for (const rock of rocks) rock.y += fall * dt;

      // Score for each rock that clears the bottom (dodged).
      for (let i = rocks.length - 1; i >= 0; i--) {
        if (rocks[i].y - rocks[i].r > H) {
          rocks.splice(i, 1);
          score += 1; sfx("click");
          if (scoreEl) scoreEl.textContent = String(score);
        }
      }

      // Collision (circle vs ship box, approximated by closest point).
      for (const rock of rocks) {
        const cx = Math.max(ship.x - SHIP_W / 2, Math.min(rock.x, ship.x + SHIP_W / 2));
        const cy = Math.max(ship.y - SHIP_H / 2, Math.min(rock.y, ship.y + SHIP_H / 2));
        const dx = rock.x - cx, dy = rock.y - cy;
        if (dx * dx + dy * dy < rock.r * rock.r) return gameOver();
      }

      draw();
      if (running) raf = requestAnimationFrame(loop);
    }

    function draw() {
      ctx.fillStyle = "#0b0f2a";
      ctx.fillRect(0, 0, W, H);
      // Starfield (cheap deterministic dots)
      ctx.fillStyle = "rgba(255,255,255,0.6)";
      for (let i = 0; i < 40; i++) {
        const x = (i * 97) % W, y = (i * 53 + (score * 2)) % H;
        ctx.fillRect(x, y, 2, 2);
      }
      // Rocks
      ctx.font = "0px serif";
      for (const rock of rocks) {
        ctx.font = (rock.r * 2) + "px serif";
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        ctx.fillText("☄️", rock.x, rock.y);
      }
      // Ship
      ctx.font = SHIP_H + "px serif";
      ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText("🚀", ship.x, ship.y);
    }

    function pointerMove(e) {
      if (!running) return;
      const rect = canvas.getBoundingClientRect();
      const t = e.touches ? e.touches[0] : e;
      ship.x = (t.clientX - rect.left) * (W / rect.width);
      ship.x = Math.max(SHIP_W / 2, Math.min(W - SHIP_W / 2, ship.x));
    }

    window.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft" || e.key === "a" || e.key === "A") { leftHeld = true; start(); }
      if (e.key === "ArrowRight" || e.key === "d" || e.key === "D") { rightHeld = true; start(); }
    });
    window.addEventListener("keyup", (e) => {
      if (e.key === "ArrowLeft" || e.key === "a" || e.key === "A") leftHeld = false;
      if (e.key === "ArrowRight" || e.key === "d" || e.key === "D") rightHeld = false;
    });
    canvas.addEventListener("mousedown", (e) => { e.preventDefault(); start(); });
    canvas.addEventListener("mousemove", pointerMove);
    canvas.addEventListener("touchstart", (e) => { e.preventDefault(); start(); pointerMove(e); }, { passive: false });
    canvas.addEventListener("touchmove", (e) => { e.preventDefault(); pointerMove(e); }, { passive: false });

    initBestDisplay("spaceship");
    reset();
  }

  window.IsmaGames = { initMemory, initColoring, initPoppiJump, initSpaceship };
})();
