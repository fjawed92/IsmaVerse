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

  /* ---------- tiny tone helper (Simon pads etc.) ---------- */
  let toneCtx = null;
  const tone = (freq, ms) => {
    try {
      toneCtx = toneCtx || new (window.AudioContext || window.webkitAudioContext)();
      const osc = toneCtx.createOscillator();
      const gain = toneCtx.createGain();
      osc.type = "sine";
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0.18, toneCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, toneCtx.currentTime + ms / 1000);
      osc.connect(gain).connect(toneCtx.destination);
      osc.start();
      osc.stop(toneCtx.currentTime + ms / 1000);
    } catch (e) {}
  };

  const prefersReducedMotion = () => {
    try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; }
    catch (e) { return false; }
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

  /* =====================================================
     WHACK-A-MOLE
  ===================================================== */
  function initWhack() {
    const grid = document.getElementById("whackGrid");
    if (!grid) return;
    const scoreEl  = document.getElementById("whackScore");
    const timeEl   = document.getElementById("whackTime");
    const statusEl = document.getElementById("whackStatus");
    const startBtn = document.getElementById("whackStart");

    const ROUND_SECONDS = 30;
    const MOLE = "🦹", STAR = "⭐";

    let score = 0, timeLeft = ROUND_SECONDS, running = false;
    let countdown = null, popTimer = null;
    const holes = [];

    for (let i = 0; i < 9; i++) {
      const hole = document.createElement("button");
      hole.type = "button";
      hole.className = "whack-hole";
      hole.setAttribute("aria-label", "Mole hole " + (i + 1));
      hole.innerHTML = '<span class="whack-mole"></span>';
      hole.addEventListener("pointerdown", (e) => {
        e.preventDefault();
        if (!running || !hole.classList.contains("is-up")) return;
        score += hole.dataset.star === "1" ? 5 : 1;
        if (scoreEl) scoreEl.textContent = String(score);
        sfx("pow");
        hideMole(hole);
      });
      grid.appendChild(hole);
      holes.push(hole);
    }

    function hideMole(hole) {
      hole.classList.remove("is-up");
      hole.dataset.star = "0";
      hole.querySelector(".whack-mole").textContent = "";
    }

    function popMole() {
      if (!running) return;
      const up = holes.filter((h) => h.classList.contains("is-up"));
      const down = holes.filter((h) => !h.classList.contains("is-up"));
      // Keep at most 2 moles up at once; retire the oldest first.
      if (up.length >= 2) hideMole(up[0]);
      if (down.length) {
        const hole = down[Math.floor(Math.random() * down.length)];
        const isStar = Math.random() < 0.12;
        hole.dataset.star = isStar ? "1" : "0";
        hole.querySelector(".whack-mole").textContent = isStar ? STAR : MOLE;
        hole.classList.add("is-up");
        // Mole sneaks back down if not bonked in time.
        const stay = 700 + Math.random() * 500;
        setTimeout(() => { if (running) hideMole(hole); }, stay);
      }
      // Pops speed up as the clock runs down (900ms -> 450ms).
      const progress = 1 - timeLeft / ROUND_SECONDS;
      const interval = 900 - 450 * progress;
      popTimer = setTimeout(popMole, interval);
    }

    function endRound() {
      running = false;
      clearInterval(countdown);
      clearTimeout(popTimer);
      holes.forEach(hideMole);
      sfx("pow");
      submitScore("whack-a-mole", score);
      if (statusEl) statusEl.textContent = "TIME'S UP! You bonked " + score + " points — great job!";
      if (startBtn) { startBtn.hidden = false; startBtn.textContent = "🔨 PLAY AGAIN!"; }
    }

    function startRound() {
      score = 0; timeLeft = ROUND_SECONDS; running = true;
      if (scoreEl) scoreEl.textContent = "0";
      if (timeEl) timeEl.textContent = String(ROUND_SECONDS);
      if (statusEl) statusEl.textContent = "GO GO GO!";
      if (startBtn) startBtn.hidden = true;
      awardGameBadge();
      sfx("click");
      countdown = setInterval(() => {
        timeLeft -= 1;
        if (timeEl) timeEl.textContent = String(timeLeft);
        if (timeLeft <= 0) endRound();
      }, 1000);
      popMole();
    }

    if (startBtn) startBtn.addEventListener("click", startRound);
    initBestDisplay("whack-a-mole");
  }

  /* =====================================================
     SNAKE
  ===================================================== */
  function initSnake() {
    const canvas = document.getElementById("snakeCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const W = canvas.width, H = canvas.height;
    const scoreEl = document.getElementById("snakeScore");
    const overlay = document.getElementById("snakeOverlay");
    const dpad = document.getElementById("snakeDpad");

    const CELL = 20, COLS = W / CELL, ROWS = H / CELL;
    const START_TICK = 160, MIN_TICK = 80;   // ms per move

    const DIRS = {
      up:    { x: 0, y: -1 },
      down:  { x: 0, y: 1 },
      left:  { x: -1, y: 0 },
      right: { x: 1, y: 0 },
    };

    let snake, dir, pendingDir, apple, score, running, awaitingStart, tickTimer;

    function reset() {
      const cx = Math.floor(COLS / 2), cy = Math.floor(ROWS / 2);
      snake = [{ x: cx, y: cy }, { x: cx - 1, y: cy }, { x: cx - 2, y: cy }];
      dir = DIRS.right;
      pendingDir = dir;
      score = 0;
      running = false;
      awaitingStart = true;
      placeApple();
      if (scoreEl) scoreEl.textContent = "0";
      draw();
    }

    function placeApple() {
      do {
        apple = { x: Math.floor(Math.random() * COLS), y: Math.floor(Math.random() * ROWS) };
      } while (snake.some((s) => s.x === apple.x && s.y === apple.y));
    }

    function setDir(name) {
      const d = DIRS[name];
      if (!d) return;
      // No 180° reversals — compare against the direction of the last real move.
      if (d.x === -dir.x && d.y === -dir.y) return;
      pendingDir = d;
    }

    function start() {
      if (!awaitingStart) return;
      reset();
      awaitingStart = false;
      running = true;
      if (overlay) overlay.hidden = true;
      awardGameBadge();
      tickTimer = setTimeout(tick, START_TICK);
    }

    function gameOver() {
      running = false;
      clearTimeout(tickTimer);
      sfx("pow");
      submitScore("snake", score);
      if (overlay) {
        overlay.innerHTML =
          '<span class="burst">GAME OVER!</span>' +
          '<p class="fw-bold mt-2 mb-0">Score: ' + score + '<br>Tap to slither again!</p>';
        overlay.hidden = false;
      }
      awaitingStart = true;
    }

    function tick() {
      dir = pendingDir;
      const head = { x: snake[0].x + dir.x, y: snake[0].y + dir.y };

      if (head.x < 0 || head.x >= COLS || head.y < 0 || head.y >= ROWS) return gameOver();
      if (snake.some((s) => s.x === head.x && s.y === head.y)) return gameOver();

      snake.unshift(head);
      if (head.x === apple.x && head.y === apple.y) {
        score += 1;
        sfx("pow");
        if (scoreEl) scoreEl.textContent = String(score);
        placeApple();
      } else {
        snake.pop();
      }

      draw();
      if (running) {
        // Speeds up a touch with every apple eaten.
        const speed = Math.max(MIN_TICK, START_TICK - score * 4);
        tickTimer = setTimeout(tick, speed);
      }
    }

    function draw() {
      ctx.fillStyle = "#0b2a14";
      ctx.fillRect(0, 0, W, H);
      // Apple
      ctx.font = (CELL * 1.1) + "px serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("🍎", apple.x * CELL + CELL / 2, apple.y * CELL + CELL / 2);
      // Snake
      snake.forEach((seg, i) => {
        ctx.fillStyle = i === 0 ? "#7dff9f" : "#22ff66";
        ctx.fillRect(seg.x * CELL + 1, seg.y * CELL + 1, CELL - 2, CELL - 2);
      });
      // Eyes on the head so kids can see which way it's going.
      const head = snake[0];
      ctx.fillStyle = "#0b2a14";
      const ex = head.x * CELL + CELL / 2 + dir.x * 4;
      const ey = head.y * CELL + CELL / 2 + dir.y * 4;
      ctx.fillRect(ex - 4, ey - 2, 3, 3);
      ctx.fillRect(ex + 2, ey - 2, 3, 3);
    }

    const KEY_DIRS = {
      ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right",
      w: "up", s: "down", a: "left", d: "right",
      W: "up", S: "down", A: "left", D: "right",
    };
    window.addEventListener("keydown", (e) => {
      const name = KEY_DIRS[e.key];
      if (!name) return;
      if (e.key.startsWith("Arrow")) e.preventDefault();
      start();
      setDir(name);
    });

    // Swipe controls on the canvas.
    let touchStart = null;
    canvas.addEventListener("touchstart", (e) => {
      e.preventDefault();
      start();
      const t = e.touches[0];
      touchStart = { x: t.clientX, y: t.clientY };
    }, { passive: false });
    canvas.addEventListener("touchmove", (e) => {
      e.preventDefault();
      if (!touchStart) return;
      const t = e.touches[0];
      const dx = t.clientX - touchStart.x, dy = t.clientY - touchStart.y;
      if (Math.abs(dx) < 24 && Math.abs(dy) < 24) return;
      if (Math.abs(dx) > Math.abs(dy)) setDir(dx > 0 ? "right" : "left");
      else setDir(dy > 0 ? "down" : "up");
      touchStart = { x: t.clientX, y: t.clientY };
    }, { passive: false });
    canvas.addEventListener("mousedown", (e) => { e.preventDefault(); start(); });

    if (dpad) {
      dpad.querySelectorAll("[data-dir]").forEach((btn) => {
        btn.addEventListener("pointerdown", (e) => {
          e.preventDefault();
          start();
          setDir(btn.dataset.dir);
        });
      });
    }

    initBestDisplay("snake");
    reset();
  }

  /* =====================================================
     SIMON SAYS
  ===================================================== */
  function initSimon() {
    const board = document.getElementById("simonBoard");
    if (!board) return;
    const roundEl  = document.getElementById("simonRound");
    const statusEl = document.getElementById("simonStatus");
    const startBtn = document.getElementById("simonStart");
    const pads = Array.from(board.querySelectorAll(".simon-pad"));

    const FREQS = [261.6, 329.6, 392.0, 523.3];  // C4 E4 G4 C5
    const BUZZ = 110;

    let sequence = [], playerIdx = 0, round = 0, accepting = false, playing = false;

    function litTime() {
      // Reduced motion: hold the light longer instead of relying on animation.
      const base = Math.max(280, 450 - round * 15);
      return prefersReducedMotion() ? base + 150 : base;
    }

    function light(pad, ms) {
      pad.classList.add("is-lit");
      tone(FREQS[pads.indexOf(pad)], ms);
      setTimeout(() => pad.classList.remove("is-lit"), ms);
    }

    function playSequence() {
      playing = true;
      accepting = false;
      if (statusEl) statusEl.textContent = "Watch carefully…";
      const step = litTime();
      sequence.forEach((padIdx, i) => {
        setTimeout(() => light(pads[padIdx], step * 0.8), (i + 1) * step * 1.4);
      });
      setTimeout(() => {
        playing = false;
        accepting = true;
        playerIdx = 0;
        if (statusEl) statusEl.textContent = "Your turn!";
      }, (sequence.length + 1) * step * 1.4);
    }

    function nextRound() {
      round += 1;
      if (roundEl) roundEl.textContent = String(round);
      sequence.push(Math.floor(Math.random() * 4));
      setTimeout(playSequence, 600);
    }

    function endGame() {
      accepting = false;
      const reached = round - 1;   // last fully completed round
      tone(BUZZ, 400);
      submitScore("simon-says", reached);
      if (statusEl) statusEl.textContent = "GREAT TRY! You completed " + reached + " round" + (reached === 1 ? "" : "s") + "!";
      if (startBtn) { startBtn.hidden = false; startBtn.textContent = "🎵 PLAY AGAIN!"; }
    }

    function startGame() {
      sequence = [];
      round = 0;
      if (roundEl) roundEl.textContent = "0";
      if (startBtn) startBtn.hidden = true;
      awardGameBadge();
      sfx("click");
      nextRound();
    }

    pads.forEach((pad, idx) => {
      pad.addEventListener("pointerdown", (e) => {
        e.preventDefault();
        if (!accepting || playing) return;
        light(pad, 250);
        if (idx === sequence[playerIdx]) {
          playerIdx += 1;
          if (playerIdx === sequence.length) {
            accepting = false;
            sfx("pow");
            if (statusEl) statusEl.textContent = "Nice! Get ready…";
            nextRound();
          }
        } else {
          endGame();
        }
      });
    });

    if (startBtn) startBtn.addEventListener("click", startGame);
    initBestDisplay("simon-says");
  }

  /* =====================================================
     BRICK BREAKER
  ===================================================== */
  function initBrick() {
    const canvas = document.getElementById("brickCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const W = canvas.width, H = canvas.height;
    const scoreEl = document.getElementById("brickScore");
    const livesEl = document.getElementById("brickLives");
    const overlay = document.getElementById("brickOverlay");

    const PADDLE_W = 90, PADDLE_H = 14, PADDLE_Y = H - 40;
    const BALL_R = 8;
    const ROWS = 6, COLS = 8;
    const BRICK_H = 24, BRICK_GAP = 6, BRICK_TOP = 70;
    const BRICK_W = (W - BRICK_GAP * (COLS + 1)) / COLS;
    const ROW_COLORS = ["#ff2d2d", "#ff8a00", "#ffd400", "#22ff66", "#1e6bff", "#ff5ad6"];
    const PADDLE_SPEED = 420;

    let paddleX, ball, bricks, score, lives, level, running, awaitingStart, ballHeld, last, raf;
    let leftHeld = false, rightHeld = false;

    function buildBricks() {
      bricks = [];
      for (let r = 0; r < ROWS; r++) {
        for (let c = 0; c < COLS; c++) {
          bricks.push({
            x: BRICK_GAP + c * (BRICK_W + BRICK_GAP),
            y: BRICK_TOP + r * (BRICK_H + BRICK_GAP),
            color: ROW_COLORS[r % ROW_COLORS.length],
            alive: true,
          });
        }
      }
    }

    function ballSpeed() {
      return 320 + (level - 1) * 40;   // gentle ramp per cleared wall
    }

    function serveBall() {
      ball = { x: paddleX, y: PADDLE_Y - BALL_R - 2, vx: 0, vy: 0 };
      ballHeld = true;
    }

    function launchBall() {
      if (!ballHeld) return;
      ballHeld = false;
      const angle = -Math.PI / 2 + (Math.random() * 0.6 - 0.3);
      ball.vx = Math.cos(angle) * ballSpeed();
      ball.vy = Math.sin(angle) * ballSpeed();
      sfx("click");
    }

    function reset() {
      paddleX = W / 2;
      score = 0;
      lives = 3;
      level = 1;
      running = false;
      awaitingStart = true;
      buildBricks();
      serveBall();
      if (scoreEl) scoreEl.textContent = "0";
      if (livesEl) livesEl.textContent = "3";
      draw();
    }

    function start() {
      if (awaitingStart) {
        reset();
        awaitingStart = false;
        running = true;
        if (overlay) overlay.hidden = true;
        awardGameBadge();
        last = performance.now();
        raf = requestAnimationFrame(loop);
      }
      launchBall();
    }

    function gameOver() {
      running = false;
      cancelAnimationFrame(raf);
      sfx("pow");
      submitScore("brick-breaker", score);
      if (overlay) {
        overlay.innerHTML =
          '<span class="burst">GAME OVER!</span>' +
          '<p class="fw-bold mt-2 mb-0">Score: ' + score + '<br>Tap to smash again!</p>';
        overlay.hidden = false;
      }
      awaitingStart = true;
    }

    function loseBall() {
      lives -= 1;
      if (livesEl) livesEl.textContent = String(lives);
      sfx("pow");
      if (lives <= 0) return gameOver();
      serveBall();
    }

    function levelClear() {
      fanfare();
      score += 50;
      level += 1;
      if (scoreEl) scoreEl.textContent = String(score);
      buildBricks();
      serveBall();
    }

    function loop(now) {
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;

      if (leftHeld) paddleX -= PADDLE_SPEED * dt;
      if (rightHeld) paddleX += PADDLE_SPEED * dt;
      paddleX = Math.max(PADDLE_W / 2, Math.min(W - PADDLE_W / 2, paddleX));

      if (ballHeld) {
        ball.x = paddleX;
        ball.y = PADDLE_Y - BALL_R - 2;
      } else {
        ball.x += ball.vx * dt;
        ball.y += ball.vy * dt;

        // Walls
        if (ball.x - BALL_R < 0) { ball.x = BALL_R; ball.vx = Math.abs(ball.vx); }
        if (ball.x + BALL_R > W) { ball.x = W - BALL_R; ball.vx = -Math.abs(ball.vx); }
        if (ball.y - BALL_R < 0) { ball.y = BALL_R; ball.vy = Math.abs(ball.vy); }
        if (ball.y - BALL_R > H) loseBall();

        // Paddle: bounce angle follows where the ball hits the paddle.
        if (ball.vy > 0 &&
            ball.y + BALL_R >= PADDLE_Y && ball.y + BALL_R <= PADDLE_Y + PADDLE_H + 6 &&
            ball.x >= paddleX - PADDLE_W / 2 - BALL_R && ball.x <= paddleX + PADDLE_W / 2 + BALL_R) {
          const offset = (ball.x - paddleX) / (PADDLE_W / 2);   // -1 .. 1
          const angle = -Math.PI / 2 + offset * (Math.PI / 3);  // up to ±60°
          const speed = ballSpeed();
          ball.vx = Math.cos(angle) * speed;
          ball.vy = Math.sin(angle) * speed;
          ball.y = PADDLE_Y - BALL_R;
          sfx("click");
        }

        // Bricks (axis-aligned box vs circle, flip the shallower axis).
        for (const b of bricks) {
          if (!b.alive) continue;
          if (ball.x + BALL_R < b.x || ball.x - BALL_R > b.x + BRICK_W ||
              ball.y + BALL_R < b.y || ball.y - BALL_R > b.y + BRICK_H) continue;
          b.alive = false;
          score += 10;
          if (scoreEl) scoreEl.textContent = String(score);
          sfx("pow");
          const overlapX = Math.min(ball.x + BALL_R - b.x, b.x + BRICK_W - (ball.x - BALL_R));
          const overlapY = Math.min(ball.y + BALL_R - b.y, b.y + BRICK_H - (ball.y - BALL_R));
          if (overlapX < overlapY) ball.vx = -ball.vx;
          else ball.vy = -ball.vy;
          break;
        }
        if (running && bricks.every((b) => !b.alive)) levelClear();
      }

      draw();
      if (running) raf = requestAnimationFrame(loop);
    }

    function draw() {
      ctx.fillStyle = "#1a0b2a";
      ctx.fillRect(0, 0, W, H);
      // Bricks
      for (const b of bricks) {
        if (!b.alive) continue;
        ctx.fillStyle = b.color;
        ctx.fillRect(b.x, b.y, BRICK_W, BRICK_H);
        ctx.strokeStyle = "#111";
        ctx.lineWidth = 2;
        ctx.strokeRect(b.x, b.y, BRICK_W, BRICK_H);
      }
      // Paddle
      ctx.fillStyle = "#ffd400";
      ctx.strokeStyle = "#111";
      ctx.lineWidth = 3;
      ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(paddleX - PADDLE_W / 2, PADDLE_Y, PADDLE_W, PADDLE_H, 7);
      else ctx.rect(paddleX - PADDLE_W / 2, PADDLE_Y, PADDLE_W, PADDLE_H);
      ctx.fill();
      ctx.stroke();
      // Ball
      ctx.fillStyle = "#fff";
      ctx.beginPath();
      ctx.arc(ball.x, ball.y, BALL_R, 0, Math.PI * 2);
      ctx.fill();
      // Hint while the ball waits on the paddle.
      if (ballHeld && running) {
        ctx.fillStyle = "rgba(255,255,255,0.8)";
        ctx.font = "bold 18px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("Tap to launch!", W / 2, H / 2);
      }
    }

    function pointerMove(e) {
      if (!running) return;
      const rect = canvas.getBoundingClientRect();
      const t = e.touches ? e.touches[0] : e;
      paddleX = (t.clientX - rect.left) * (W / rect.width);
      paddleX = Math.max(PADDLE_W / 2, Math.min(W - PADDLE_W / 2, paddleX));
    }

    window.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft" || e.key === "a" || e.key === "A") { e.preventDefault(); leftHeld = true; start(); }
      if (e.key === "ArrowRight" || e.key === "d" || e.key === "D") { e.preventDefault(); rightHeld = true; start(); }
      if (e.code === "Space" || e.key === " ") { e.preventDefault(); start(); }
    });
    window.addEventListener("keyup", (e) => {
      if (e.key === "ArrowLeft" || e.key === "a" || e.key === "A") leftHeld = false;
      if (e.key === "ArrowRight" || e.key === "d" || e.key === "D") rightHeld = false;
    });
    canvas.addEventListener("mousedown", (e) => { e.preventDefault(); start(); });
    canvas.addEventListener("mousemove", pointerMove);
    canvas.addEventListener("touchstart", (e) => { e.preventDefault(); start(); pointerMove(e); }, { passive: false });
    canvas.addEventListener("touchmove", (e) => { e.preventDefault(); pointerMove(e); }, { passive: false });

    initBestDisplay("brick-breaker");
    reset();
  }

  /* =====================================================
     MATH HELPERS (shared by the educational games)
  ===================================================== */
  const randInt = (lo, hi) => lo + Math.floor(Math.random() * (hi - lo + 1));
  const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];

  // 4 multiple-choice answers: the real one + 3 nearby look-alikes.
  const makeChoices = (answer) => {
    const choices = new Set([answer]);
    const spread = Math.max(3, Math.round(Math.abs(answer) * 0.25));
    let guard = 0;
    while (choices.size < 4 && guard++ < 100) {
      const d = answer + randInt(-spread, spread);
      if (d !== answer && d >= 0) choices.add(d);
    }
    // Fallback for tiny answers where the spread can't produce 3 options.
    let bump = 1;
    while (choices.size < 4) choices.add(answer + spread + bump++);
    return shuffle(Array.from(choices));
  };

  // Render answer buttons into a .math-answers grid; onPick(value, button).
  const renderChoices = (wrap, choices, onPick) => {
    wrap.innerHTML = "";
    choices.forEach((value) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "math-answer-btn";
      btn.textContent = String(value);
      btn.addEventListener("pointerdown", (e) => {
        e.preventDefault();
        onPick(value, btn);
      });
      wrap.appendChild(btn);
    });
  };

  const flashAnswers = (wrap, answer, pickedBtn) => {
    wrap.querySelectorAll(".math-answer-btn").forEach((b) => {
      b.disabled = true;
      if (parseInt(b.textContent, 10) === answer) b.classList.add("is-right");
    });
    if (pickedBtn) pickedBtn.classList.add("is-wrong");
  };

  /* =====================================================
     MATH BLITZ  (60-second arithmetic sprint)
  ===================================================== */
  function initMathBlitz() {
    const problemEl = document.getElementById("blitzProblem");
    if (!problemEl) return;
    const answersEl = document.getElementById("blitzAnswers");
    const scoreEl   = document.getElementById("blitzScore");
    const timeEl    = document.getElementById("blitzTime");
    const streakEl  = document.getElementById("blitzStreak");
    const statusEl  = document.getElementById("blitzStatus");
    const startBtn  = document.getElementById("blitzStart");

    const ROUND_SECONDS = 60;

    let score = 0, streak = 0, solved = 0, timeLeft = ROUND_SECONDS;
    let running = false, accepting = false, countdown = null, answer = 0;

    // Difficulty climbs with every few problems solved (right OR wrong moves
    // you on, so nobody gets stuck staring at the same level).
    function makeQuestion() {
      const level = solved < 5 ? 1 : solved < 10 ? 2 : solved < 16 ? 3 : solved < 23 ? 4 : 5;
      let op;
      if (level <= 2) op = pick(["+", "−"]);
      else if (level === 3) op = "×";
      else if (level === 4) op = pick(["×", "÷"]);
      else op = pick(["+", "−", "×", "÷"]);

      let a, b;
      if (op === "+") {
        const max = level === 1 ? 10 : level === 2 ? 25 : 99;
        a = randInt(1, max); b = randInt(1, max);
        answer = a + b;
      } else if (op === "−") {
        const max = level === 1 ? 10 : level === 2 ? 25 : 99;
        a = randInt(1, max); b = randInt(1, max);
        if (b > a) { const t = a; a = b; b = t; }
        answer = a - b;
      } else if (op === "×") {
        a = randInt(2, level >= 4 ? 12 : 5); b = randInt(2, 9);
        answer = a * b;
      } else {
        b = randInt(2, 9); answer = randInt(2, 12);
        a = b * answer;          // guarantees a whole-number quotient
      }
      problemEl.textContent = a + " " + op + " " + b + " = ?";
      renderChoices(answersEl, makeChoices(answer), onPick);
      accepting = true;
    }

    function onPick(value, btn) {
      if (!running || !accepting) return;
      accepting = false;
      if (value === answer) {
        streak += 1;
        score += 10 + Math.min(streak - 1, 5);   // streak bonus, capped
        solved += 1;
        if (scoreEl) scoreEl.textContent = String(score);
        if (streakEl) streakEl.textContent = String(streak);
        btn.classList.add("is-right");
        sfx("pow");
        setTimeout(() => { if (running) makeQuestion(); }, 200);
      } else {
        streak = 0;
        solved += 1;
        if (streakEl) streakEl.textContent = "0";
        flashAnswers(answersEl, answer, btn);
        tone(110, 300);
        setTimeout(() => { if (running) makeQuestion(); }, 800);
      }
    }

    function endRound() {
      running = false;
      accepting = false;
      clearInterval(countdown);
      answersEl.innerHTML = "";
      problemEl.textContent = "TIME'S UP!";
      sfx("pow");
      submitScore("math-blitz", score);
      if (statusEl) statusEl.textContent = "You scored " + score + " points — super brain power!";
      if (startBtn) { startBtn.hidden = false; startBtn.textContent = "⚡ PLAY AGAIN!"; }
    }

    function startRound() {
      score = 0; streak = 0; solved = 0; timeLeft = ROUND_SECONDS;
      running = true;
      if (scoreEl) scoreEl.textContent = "0";
      if (streakEl) streakEl.textContent = "0";
      if (timeEl) timeEl.textContent = String(ROUND_SECONDS);
      if (statusEl) statusEl.textContent = "GO GO GO!";
      if (startBtn) startBtn.hidden = true;
      awardGameBadge();
      sfx("click");
      countdown = setInterval(() => {
        timeLeft -= 1;
        if (timeEl) timeEl.textContent = String(timeLeft);
        if (timeLeft <= 0) endRound();
      }, 1000);
      makeQuestion();
    }

    if (startBtn) startBtn.addEventListener("click", startRound);
    initBestDisplay("math-blitz");
  }

  /* =====================================================
     EQUATION MATCH  (memory match: equation <-> answer)
  ===================================================== */
  function initEquationMatch() {
    const grid = document.getElementById("equationGrid");
    if (!grid) return;
    const movesEl   = document.getElementById("equationMoves");
    const matchesEl = document.getElementById("equationMatches");
    const winEl     = document.getElementById("equationWin");
    const finalEl   = document.getElementById("equationFinalMoves");
    const scoreEl   = document.getElementById("equationFinalScore");
    const restart   = document.getElementById("equationRestart");

    const PAIRS = 6;

    let first = null, lock = false, moves = 0, matches = 0;

    // Fresh equations every game, all with distinct answers so each
    // answer card matches exactly one equation.
    function makePairs() {
      const pairs = [];
      const used = new Set();
      let guard = 0;
      while (pairs.length < PAIRS && guard++ < 200) {
        const kind = pairs.length % 3;
        let a, b, text, ans;
        if (kind === 0) {
          a = randInt(2, 12); b = randInt(2, 12);
          ans = a + b; text = a + " + " + b;
        } else if (kind === 1) {
          a = randInt(5, 20); b = randInt(1, a - 1);
          ans = a - b; text = a + " − " + b;
        } else {
          a = randInt(2, 9); b = randInt(2, 9);
          ans = a * b; text = a + " × " + b;
        }
        if (used.has(ans)) continue;
        used.add(ans);
        pairs.push({ text: text, ans: ans });
      }
      return pairs;
    }

    function build() {
      grid.innerHTML = "";
      if (winEl) winEl.hidden = true;
      first = null; lock = false; moves = 0; matches = 0;
      if (movesEl) movesEl.textContent = "0";
      if (matchesEl) matchesEl.textContent = "0";

      const cards = [];
      makePairs().forEach((p, i) => {
        cards.push({ face: p.text, pair: i });
        cards.push({ face: String(p.ans), pair: i });
      });
      shuffle(cards).forEach((c) => {
        const card = document.createElement("button");
        card.type = "button";
        card.className = "memory-card";
        card.setAttribute("aria-label", "Equation card");
        card.dataset.pair = String(c.pair);
        card.innerHTML =
          '<span class="memory-card-inner">' +
            '<span class="memory-front">?</span>' +
            '<span class="memory-back">' + c.face + "</span>" +
          "</span>";
        card.addEventListener("click", () => flip(card));
        grid.appendChild(card);
      });
    }

    function flip(card) {
      if (lock || card === first || card.classList.contains("is-flipped") || card.classList.contains("is-matched")) return;
      card.classList.add("is-flipped");
      sfx("click");

      if (!first) { first = card; return; }

      moves += 1;
      if (movesEl) movesEl.textContent = String(moves);

      if (first.dataset.pair === card.dataset.pair) {
        first.classList.add("is-matched");
        card.classList.add("is-matched");
        sfx("pow");
        matches += 1;
        if (matchesEl) matchesEl.textContent = String(matches);
        first = null;
        if (matches === PAIRS) {
          // Perfect game (6 moves) = 100; each extra move costs 5.
          const score = Math.max(10, 100 - (moves - PAIRS) * 5);
          fanfare();
          awardGameBadge();
          submitScore("equation-match", score);
          if (finalEl) finalEl.textContent = String(moves);
          if (scoreEl) scoreEl.textContent = String(score);
          if (winEl) winEl.hidden = false;
        }
      } else {
        lock = true;
        const a = first, b = card;
        setTimeout(() => {
          a.classList.remove("is-flipped");
          b.classList.remove("is-flipped");
          lock = false;
        }, 900);
        first = null;
      }
    }

    if (restart) restart.addEventListener("click", () => { sfx("click"); build(); });
    initBestDisplay("equation-match");
    build();
  }

  /* =====================================================
     PATTERN QUEST  (find the missing number, 3 lives)
  ===================================================== */
  function initPatternQuest() {
    const seqEl = document.getElementById("patternSeq");
    if (!seqEl) return;
    const choicesEl = document.getElementById("patternChoices");
    const scoreEl   = document.getElementById("patternScore");
    const livesEl   = document.getElementById("patternLives");
    const statusEl  = document.getElementById("patternStatus");
    const startBtn  = document.getElementById("patternStart");

    const TERMS = 5;

    let score = 0, lives = 3, solved = 0;
    let running = false, accepting = false, answer = 0;

    function currentTier() {
      return solved < 3 ? 1 : solved < 6 ? 2 : solved < 10 ? 3 : solved < 14 ? 4 : 5;
    }

    function makeSequence(tier) {
      const seq = [];
      if (tier === 1) {
        const step = pick([1, 2, 5, 10]);
        let n = randInt(1, 10);
        for (let i = 0; i < TERMS; i++) { seq.push(n); n += step; }
      } else if (tier === 2) {
        const step = pick([2, 3, 4, 5]);
        if (Math.random() < 0.5) {
          let n = randInt(step * TERMS, step * TERMS + 20);   // descending
          for (let i = 0; i < TERMS; i++) { seq.push(n); n -= step; }
        } else {
          let n = randInt(1, 12);
          const bigStep = pick([6, 7, 8, 9]);
          for (let i = 0; i < TERMS; i++) { seq.push(n); n += bigStep; }
        }
      } else if (tier === 3) {
        let n = pick([1, 2, 3, 4, 5]);                        // doubling
        for (let i = 0; i < TERMS; i++) { seq.push(n); n *= 2; }
      } else if (tier === 4) {
        if (Math.random() < 0.5) {
          const start = randInt(1, 4);                        // square numbers
          for (let i = 0; i < TERMS; i++) seq.push((start + i) * (start + i));
        } else {
          let n = pick([1, 2, 3]);                            // tripling
          for (let i = 0; i < TERMS; i++) { seq.push(n); n *= 3; }
        }
      } else {
        let a = randInt(1, 5), b = randInt(1, 5);             // Fibonacci-style
        for (let i = 0; i < TERMS; i++) {
          seq.push(a);
          const next = a + b;
          a = b; b = next;
        }
      }
      return seq;
    }

    function makePattern() {
      const tier = currentTier();
      const seq = makeSequence(tier);
      const gap = randInt(1, TERMS - 2);   // never the first or last term
      answer = seq[gap];

      seqEl.innerHTML = seq
        .map((n, i) => (i === gap ? '<span class="pattern-gap">?</span>' : String(n)))
        .join('<span class="pattern-comma">, </span>');
      renderChoices(choicesEl, makeChoices(answer), onPick);
      if (statusEl) statusEl.textContent = "What number fills the gap? (Worth " + tier * 10 + " points)";
      accepting = true;
    }

    function drawLives() {
      if (livesEl) livesEl.textContent = lives > 0 ? "❤️".repeat(lives) : "💔";
    }

    function onPick(value, btn) {
      if (!running || !accepting) return;
      accepting = false;
      if (value === answer) {
        score += currentTier() * 10;
        solved += 1;
        if (scoreEl) scoreEl.textContent = String(score);
        btn.classList.add("is-right");
        sfx("pow");
        setTimeout(() => { if (running) makePattern(); }, 400);
      } else {
        lives -= 1;
        drawLives();
        flashAnswers(choicesEl, answer, btn);
        tone(110, 300);
        if (lives <= 0) {
          setTimeout(endGame, 900);
        } else {
          if (statusEl) statusEl.textContent = "So close! The answer was " + answer + " — keep going!";
          setTimeout(() => { if (running) makePattern(); }, 1300);
        }
      }
    }

    function endGame() {
      running = false;
      accepting = false;
      choicesEl.innerHTML = "";
      seqEl.textContent = "GAME OVER!";
      sfx("pow");
      submitScore("pattern-quest", score);
      if (statusEl) statusEl.textContent = "You solved " + solved + " pattern" + (solved === 1 ? "" : "s") + " and scored " + score + " points!";
      if (startBtn) { startBtn.hidden = false; startBtn.textContent = "🔢 PLAY AGAIN!"; }
    }

    function startGame() {
      score = 0; lives = 3; solved = 0;
      running = true;
      if (scoreEl) scoreEl.textContent = "0";
      drawLives();
      if (startBtn) startBtn.hidden = true;
      awardGameBadge();
      sfx("click");
      makePattern();
    }

    if (startBtn) startBtn.addEventListener("click", startGame);
    initBestDisplay("pattern-quest");
  }

  window.IsmaGames = {
    initMemory, initColoring, initPoppiJump, initSpaceship,
    initWhack, initSnake, initSimon, initBrick,
    initMathBlitz, initEquationMatch, initPatternQuest,
  };
})();
