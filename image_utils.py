import io
import hashlib
import numpy as np
from typing import Tuple
from PIL import Image
from config import CANVAS_W, CANVAS_H

def pil_to_png_bytes(img: Image.Image) -> bytes:
    b = io.BytesIO()
    img.save(b, format="PNG")
    return b.getvalue()

def sha1_bytes(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()

def np_from_pil(img: Image.Image) -> np.ndarray:
    arr = np.array(img.convert("RGBA"))
    arr[..., 3] = 255  # opaco
    return arr

def pil_from_np(arr: np.ndarray) -> Image.Image:
    arr[..., 3] = 255
    return Image.fromarray(arr, mode="RGBA")

def move_rect_nonblack(img: Image.Image, rect: Tuple[int, int, int, int], dx: int, dy: int) -> Image.Image:
    """
    Move pixels não pretos dentro de 'rect', mantendo preto no background.
    """
    x, y, w, h = rect
    x2, y2 = x + w, y + h
    x, y = max(0, x), max(0, y)
    x2, y2 = min(CANVAS_W, x2), min(CANVAS_H, y2)
    w, h = max(0, x2 - x), max(0, y2 - y)
    if w == 0 or h == 0:
        return img

    a = np_from_pil(img)
    crop = a[y:y+h, x:x+w, :].copy()
    mask = (crop[..., :3] != 0).any(-1)

    # limpa origem (preto)
    a[y:y+h, x:x+w, 0][mask] = 0
    a[y:y+h, x:x+w, 1][mask] = 0
    a[y:y+h, x:x+w, 2][mask] = 0
    a[y:y+h, x:x+w, 3][mask] = 255

    nx, ny = x + int(dx), y + int(dy)
    dst_x1, dst_y1 = max(0, nx), max(0, ny)
    dst_x2, dst_y2 = min(CANVAS_W, nx + w), min(CANVAS_H, ny + h)
    if dst_x1 >= dst_x2 or dst_y1 >= dst_y2:
        return pil_from_np(a)

    sx1 = dst_x1 - nx
    sy1 = dst_y1 - ny
    sx2 = sx1 + (dst_x2 - dst_x1)
    sy2 = sy1 + (dst_y2 - dst_y1)

    sub_crop = crop[sy1:sy2, sx1:sx2, :]
    sub_mask = mask[sy1:sy2, sx1:sx2]

    a[dst_y1:dst_y2, dst_x1:dst_x2, 0][sub_mask] = sub_crop[..., 0][sub_mask]
    a[dst_y1:dst_y2, dst_x1:dst_x2, 1][sub_mask] = sub_crop[..., 1][sub_mask]
    a[dst_y1:dst_y2, dst_x1:dst_x2, 2][sub_mask] = sub_crop[..., 2][sub_mask]
    a[dst_y1:dst_y2, dst_x1:dst_x2, 3][sub_mask] = 255

    return pil_from_np(a)
