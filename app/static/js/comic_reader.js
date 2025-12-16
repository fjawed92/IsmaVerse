(() => {
  const canvas = document.getElementById("pdfCanvas");
  const ctx = canvas.getContext("2d");
  const prevBtn = document.getElementById("prevBtn");
  const nextBtn = document.getElementById("nextBtn");
  const pageNumEl = document.getElementById("pageNum");
  const pageCountEl = document.getElementById("pageCount");
  const zoomLabel = document.getElementById("zoomLabel");
  const zoomIn = document.getElementById("zoomIn");
  const zoomOut = document.getElementById("zoomOut");
  const pageFrame = document.getElementById("pageFrame");

  const pdfUrl = window.COMIC_READER?.pdfUrl;
  if (!pdfUrl) {
    console.error("Comic Reader: missing pdfUrl");
    return;
  }

  // PDF.js worker (CDN)
  // This is required for performance.
  pdfjsLib.GlobalWorkerOptions.workerSrc = window.COMIC_READER.workerUrl;


  let pdfDoc = null;
  let pageNum = 1;
  let pageCount = 0;
  let scale = 1.0;        // “base” scale
  let fitScale = 1.0;     // auto-fit scale
  let renderTask = null;

  function setFlip() {
    pageFrame.classList.remove("is-flipping");
    // restart animation reliably
    void pageFrame.offsetWidth;
    pageFrame.classList.add("is-flipping");
    setTimeout(() => pageFrame.classList.remove("is-flipping"), 260);
  }

  function updateUI() {
    pageNumEl.textContent = String(pageNum);
    pageCountEl.textContent = String(pageCount || "?");
    zoomLabel.textContent = `${Math.round(scale * 100)}%`;
    prevBtn.disabled = (pageNum <= 1);
    nextBtn.disabled = (pageNum >= pageCount);
  }

  async function renderPage(num) {
    if (!pdfDoc) return;

    // cancel prior render if still running
    if (renderTask) {
      try { renderTask.cancel(); } catch (e) {}
    }

    const page = await pdfDoc.getPage(num);

    // Fit page width to container
    const containerWidth = pageFrame.clientWidth;
    const viewportAt1 = page.getViewport({ scale: 1.0 });
    fitScale = (containerWidth / viewportAt1.width);

    const viewport = page.getViewport({ scale: fitScale * scale });

    // Proper canvas sizing for crispness
    const devicePixelRatio = window.devicePixelRatio || 1;
    canvas.width = Math.floor(viewport.width * devicePixelRatio);
    canvas.height = Math.floor(viewport.height * devicePixelRatio);
    canvas.style.width = `${Math.floor(viewport.width)}px`;
    canvas.style.height = `${Math.floor(viewport.height)}px`;

    ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);

    renderTask = page.render({ canvasContext: ctx, viewport });
    await renderTask.promise;

    updateUI();
  }

  async function loadPdf() {
    const loadingTask = pdfjsLib.getDocument(pdfUrl);
    pdfDoc = await loadingTask.promise;
    pageCount = pdfDoc.numPages;
    pageNum = 1;
    updateUI();
    await renderPage(pageNum);
  }

  function nextPage() {
    if (!pdfDoc || pageNum >= pageCount) return;
    pageNum += 1;
    setFlip();
    renderPage(pageNum);
  }

  function prevPage() {
    if (!pdfDoc || pageNum <= 1) return;
    pageNum -= 1;
    setFlip();
    renderPage(pageNum);
  }

  function zoom(delta) {
    scale = Math.min(2.5, Math.max(0.6, +(scale + delta).toFixed(2)));
    renderPage(pageNum);
  }

  // Buttons
  nextBtn.addEventListener("click", nextPage);
  prevBtn.addEventListener("click", prevPage);
  zoomIn.addEventListener("click", () => zoom(0.1));
  zoomOut.addEventListener("click", () => zoom(-0.1));

  // Keyboard arrows
  window.addEventListener("keydown", (e) => {
    if (e.key === "ArrowRight") nextPage();
    if (e.key === "ArrowLeft") prevPage();
  });

  // Mobile swipe
  let touchStartX = null;
  pageFrame.addEventListener("touchstart", (e) => {
    touchStartX = e.changedTouches[0].screenX;
  }, { passive: true });

  pageFrame.addEventListener("touchend", (e) => {
    if (touchStartX == null) return;
    const dx = e.changedTouches[0].screenX - touchStartX;
    touchStartX = null;
    if (Math.abs(dx) < 45) return;
    if (dx < 0) nextPage(); else prevPage();
  }, { passive: true });

  // Double click to toggle zoom (desktop)
  pageFrame.addEventListener("dblclick", () => {
    scale = (scale < 1.4) ? 1.6 : 1.0;
    renderPage(pageNum);
  });

  // Re-fit on resize
  let resizeTimer = null;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => renderPage(pageNum), 120);
  });

  // Go
  loadPdf().catch(err => {
    console.error("Comic Reader error:", err);
    alert("Could not load this comic. (PDF failed to render)");
  });
})();
