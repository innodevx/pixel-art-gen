from typing import Optional, Tuple
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import streamlit as st

from config import CANVAS_W, CANVAS_H, CANVAS_BG_HEX
from image_utils import np_from_pil, pil_from_np, move_rect_nonblack

def draw_mode(current_img: Image.Image) -> Image.Image:
    stroke = st.color_picker("Cor do traço", "#FFFFFF")
    width  = st.slider("Espessura", 1, 32, 8)
    canvas = st_canvas(
        fill_color="rgba(0,0,0,0)",
        stroke_color=stroke,
        stroke_width=width,
        background_color=CANVAS_BG_HEX,
        background_image=current_img.copy(),
        width=CANVAS_W, height=CANVAS_H,
        drawing_mode="freedraw", key="draw",
        update_streamlit=True,
    )
    if canvas.image_data is not None:
        img = Image.fromarray(canvas.image_data).convert("RGBA")
        return pil_from_np(np_from_pil(img))
    return current_img

def _rect_from_obj(obj) -> Tuple[int, int, int, int]:
    left   = int(round(obj.get("left", 0)))
    top    = int(round(obj.get("top", 0)))
    width  = int(round(obj.get("width", 0)  * float(obj.get("scaleX", 1) or 1)))
    height = int(round(obj.get("height", 0) * float(obj.get("scaleY", 1) or 1)))
    return (left, top, width, height)

def select_mode(current_img: Image.Image, prev_rect: Optional[Tuple[int,int,int,int]]) -> Tuple[Image.Image, Optional[Tuple[int,int,int,int]]]:
    st.caption("Arraste o retângulo – a área dentro dele se moverá em tempo real.")
    csel = st_canvas(
        fill_color="rgba(0,0,0,0)",
        stroke_width=2,
        stroke_color="#00FFAA",
        background_color=CANVAS_BG_HEX,
        background_image=current_img.copy(),
        width=CANVAS_W, height=CANVAS_H,
        drawing_mode="transform",
        key="select",
        update_streamlit=True,
    )
    rect = None
    if csel.json_data and "objects" in csel.json_data:
        for obj in csel.json_data["objects"]:
            if obj.get("type") == "rect":
                rect = _rect_from_obj(obj)
                break

    if rect:
        if prev_rect and rect != prev_rect:
            dx, dy = rect[0] - prev_rect[0], rect[1] - prev_rect[1]
            current_img = move_rect_nonblack(current_img, prev_rect, dx, dy)
        prev_rect = rect

    return current_img, prev_rect
