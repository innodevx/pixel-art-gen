const { invoke } = window.__TAURI__.tauri;

const canvas = document.querySelector("#paint");
const ctx = canvas.getContext("2d");
const colorPicker = document.querySelector("#colorPicker");
const brushSize = document.querySelector("#brushSize");
const brushLabel = document.querySelector("#brushLabel");
const prompt = document.querySelector("#prompt");
const statusEl = document.querySelector("#status");
const generateBtn = document.querySelector("#generate");
const applyBtn = document.querySelector("#applyPreview");
const previewFrame = document.querySelector("#previewFrame");

let isDrawing = false;
let lastX = 0;
let lastY = 0;
let erasing = false;
let previewDataUrl = null;

function setStatus(text) {
  statusEl.textContent = text;
}

function setBrushLabel() {
  brushLabel.textContent = `${brushSize.value} px`;
}

function setStrokeStyle() {
  ctx.lineWidth = Number(brushSize.value);
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.strokeStyle = erasing ? "rgba(15,23,42,1)" : colorPicker.value;
}

function startDraw(event) {
  isDrawing = true;
  const { offsetX, offsetY } = event;
  lastX = offsetX;
  lastY = offsetY;
  setStrokeStyle();
  ctx.beginPath();
  ctx.moveTo(lastX, lastY);
}

function draw(event) {
  if (!isDrawing) return;
  const { offsetX, offsetY } = event;
  ctx.lineTo(offsetX, offsetY);
  ctx.stroke();
  lastX = offsetX;
  lastY = offsetY;
}

function stopDraw() {
  if (!isDrawing) return;
  isDrawing = false;
  ctx.closePath();
}

function fillCanvas(color) {
  ctx.fillStyle = color;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
}

function usePreviewOnCanvas() {
  if (!previewDataUrl) return;
  const img = new Image();
  img.onload = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    setStatus("Preview applied to canvas. Keep iterating!");
  };
  img.src = previewDataUrl;
}

function attachEvents() {
  canvas.addEventListener("pointerdown", startDraw);
  canvas.addEventListener("pointermove", draw);
  canvas.addEventListener("pointerup", stopDraw);
  canvas.addEventListener("pointerleave", stopDraw);

  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    const delta = Math.sign(e.deltaY) * -1;
    const next = Math.min(60, Math.max(1, Number(brushSize.value) + delta));
    brushSize.value = next;
    setBrushLabel();
    setStrokeStyle();
  });

  colorPicker.addEventListener("input", () => {
    erasing = false;
    setStrokeStyle();
  });

  brushSize.addEventListener("input", () => {
    setBrushLabel();
    setStrokeStyle();
  });

  document.querySelector("#eraserToggle").addEventListener("click", () => {
    erasing = !erasing;
    setStrokeStyle();
    setStatus(erasing ? "Eraser active." : "Brush active.");
  });

  document.querySelector("#clearCanvas").addEventListener("click", () => {
    fillCanvas("rgba(15,23,42,1)");
    setStatus("Canvas cleared. Ready for a new idea.");
  });

  document.querySelector("#fillCanvas").addEventListener("click", () => {
    fillCanvas(colorPicker.value);
    setStatus("Filled the canvas with your current color.");
  });

  document.querySelectorAll(".swatch").forEach((btn) => {
    btn.addEventListener("click", () => {
      colorPicker.value = btn.dataset.color;
      erasing = false;
      setStrokeStyle();
    });
  });

  applyBtn.addEventListener("click", usePreviewOnCanvas);

  generateBtn.addEventListener("click", async () => {
    const promptText = prompt.value.trim();
    const dataUrl = canvas.toDataURL("image/png");

    setStatus("Crafting AI preview…");
    generateBtn.disabled = true;
    applyBtn.disabled = true;

    try {
      const result = await invoke("generate_image", {
        prompt: promptText || "visual polish",
        canvasData: dataUrl,
      });

      previewDataUrl = result.preview;
      const img = new Image();
      img.src = previewDataUrl;
      img.alt = "AI preview";
      img.onload = () => {
        previewFrame.innerHTML = "";
        previewFrame.appendChild(img);
        applyBtn.disabled = false;
        setStatus(result.note || "Preview ready.");
      };
    } catch (error) {
      console.error(error);
      setStatus(`Preview failed: ${error}`);
    } finally {
      generateBtn.disabled = false;
    }
  });
}

function init() {
  setStrokeStyle();
  setBrushLabel();
  fillCanvas("rgba(15,23,42,1)");
  attachEvents();
}

init();
