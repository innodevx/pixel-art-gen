#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use anyhow::Result;
use base64::{engine::general_purpose::STANDARD as BASE64, Engine};
use image::{codecs::png::PngEncoder, ColorType, Rgba, RgbaImage};
use rand::{rngs::StdRng, Rng, SeedableRng};
use serde::Serialize;
use std::{collections::hash_map::DefaultHasher, hash::Hash, hash::Hasher, io::Cursor};

type CanvasImage = RgbaImage;

#[derive(Serialize)]
struct GeneratedImage {
    preview: String,
    note: String,
}

#[tauri::command]
fn generate_image(prompt: String, canvas_data: String) -> Result<GeneratedImage, String> {
    let seed = prompt_seed(&prompt);
    let mut rng = StdRng::seed_from_u64(seed);

    let bytes = decode_data_url(&canvas_data).map_err(|e| e.to_string())?;
    let mut canvas = load_rgba(&bytes).map_err(|e| e.to_string())?;

    apply_prompt_overlay(&mut canvas, &prompt, &mut rng);

    let encoded = encode_png_data_url(&canvas).map_err(|e| e.to_string())?;
    Ok(GeneratedImage {
        preview: encoded,
        note: format!("Preview ready — using prompt seed {}", seed),
    })
}

fn decode_data_url(data_url: &str) -> Result<Vec<u8>> {
    let b64 = data_url
        .split(',')
        .nth(1)
        .unwrap_or(data_url);
    BASE64.decode(b64).map_err(anyhow::Error::from)
}

fn load_rgba(bytes: &[u8]) -> Result<CanvasImage> {
    let img = image::load_from_memory(bytes)?;
    Ok(img.to_rgba8())
}

fn apply_prompt_overlay(image: &mut CanvasImage, prompt: &str, rng: &mut StdRng) {
    let (w, h) = image.dimensions();
    let tint = prompt_palette(prompt, rng);

    for (x, y, pixel) in image.enumerate_pixels_mut() {
        let progress = (x as f32 / w as f32 + y as f32 / h as f32) / 2.0;
        let mix = 0.12 + progress * 0.25;
        let blend = |c, t| (c as f32 * (1.0 - mix) + t as f32 * mix) as u8;

        *pixel = Rgba([
            blend(pixel[0], tint[0]),
            blend(pixel[1], tint[1]),
            blend(pixel[2], tint[2]),
            255,
        ]);

        // add a subtle spark of noise to avoid flat regions
        if rng.gen_bool(0.003) {
            let scatter = rng.gen_range(0..4) as i16;
            let bump = |c: u8| c.saturating_add(scatter as u8);
            pixel.0[0] = bump(pixel[0]);
            pixel.0[1] = bump(pixel[1]);
            pixel.0[2] = bump(pixel[2]);
        }
    }
}

fn prompt_palette(prompt: &str, rng: &mut StdRng) -> [u8; 3] {
    let mut hasher = DefaultHasher::new();
    prompt.hash(&mut hasher);
    let seed = hasher.finish();
    let mut seeded_rng = StdRng::seed_from_u64(seed ^ rng.gen::<u64>());

    [
        seeded_rng.gen_range(60..220),
        seeded_rng.gen_range(60..220),
        seeded_rng.gen_range(60..220),
    ]
}

fn encode_png_data_url(img: &CanvasImage) -> Result<String> {
    let mut buf = Cursor::new(Vec::new());
    let encoder = PngEncoder::new(&mut buf);
    encoder.write_image(img.as_raw(), img.width(), img.height(), ColorType::Rgba8)?;
    let encoded = BASE64.encode(buf.into_inner());
    Ok(format!("data:image/png;base64,{}", encoded))
}

fn prompt_seed(prompt: &str) -> u64 {
    let mut hasher = DefaultHasher::new();
    prompt.hash(&mut hasher);
    hasher.finish()
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![generate_image])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
