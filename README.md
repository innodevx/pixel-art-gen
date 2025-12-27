# Pixel Art Gen — Tauri Desktop Painter

A desktop-first painter inspired by Photoshop/Aseprite that keeps your canvas local while letting an AI-inspired overlay remix your strokes into a preview. Built with [Tauri](https://tauri.app/) so everything runs as a lightweight native app.

## Features

- 🎨 Full-screen canvas with brush size, quick palette swatches, eraser, and fill tools.
- 🧠 Prompt box to describe the style you want; the Rust backend creates an AI-flavored preview using your strokes as guidance.
- 🔁 Apply the preview back to the canvas and iterate without losing your layers.
- 🖥️ Ships as a desktop app; no browser tab or remote uploads needed for the preview effect.

## Project layout

- `src/` — Plain HTML/CSS/JS front-end served by Tauri. Uses the canvas API for drawing and `window.__TAURI__.invoke` to call backend commands.
- `src-tauri/` — Rust backend. The `generate_image` command decodes the canvas PNG, mixes in a prompt-driven palette, and returns a base64 preview.
- `package.json` — Provides the Tauri CLI scripts. No bundler is required for the front-end assets.

## Prerequisites

- **Rust** (stable) with Cargo installed.
- **Node.js** 18+ and npm.
- On Linux you may need additional system packages for webview/GTK; see the [Tauri prerequisites](https://tauri.app/v1/guides/getting-started/prerequisites/).

## Install dependencies

```bash
npm install
```

This installs only the Tauri CLI locally; the front-end uses vanilla JS without extra packages.

## Run in development

```bash
npm run tauri dev
```

This launches the Tauri window pointed at `src/index.html` so you can draw, enter a prompt, generate a preview, and apply it back to the canvas.

## Build a desktop bundle

```bash
npm run tauri build
```

The compiled binaries/installer will appear under `src-tauri/target/release/` for your platform.

## How the AI-inspired preview works

The Tauri command `generate_image` (see `src-tauri/src/main.rs`) takes your canvas as a base64 PNG and:

1. Decodes it into RGBA pixels.
2. Derives a deterministic color palette seeded from your prompt text.
3. Applies a smooth tint gradient plus subtle noise, so the preview reflects your prompt while respecting the original strokes.
4. Encodes the result back to a PNG data URL and returns it to the front-end.

You can replace this logic with calls to your preferred model server later; the front-end only expects a `data:image/png;base64,...` string in response.

## Tips

- Scroll over the canvas to resize the brush while drawing.
- Use the palette chips to quickly set a scheme before sketching.
- If you integrate a real model, reuse the command signature (`prompt`, `canvasData`) so the UI keeps working.
