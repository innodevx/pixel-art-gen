import re
import time
import requests
from typing import Any, Dict, Optional, Tuple, List
from config import COMFY_URL, REQ_TIMEOUT

def upload_image(png_bytes: bytes, filename: str) -> Dict[str, Any]:
    files = {"image": (filename, png_bytes, "image/png")}
    r = requests.post(f"{COMFY_URL}/upload/image", files=files, timeout=REQ_TIMEOUT)
    r.raise_for_status()
    return r.json()

def post_prompt(prompt_json: Dict[str, Any]) -> Dict[str, Any]:
    import uuid, json
    payload = {"prompt": prompt_json, "client_id": str(uuid.uuid4())}
    r = requests.post(f"{COMFY_URL}/prompt", json=payload, timeout=REQ_TIMEOUT)
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        try:
            msg = r.json()
        except Exception:
            msg = r.text
        raise RuntimeError(f"HTTP {r.status_code} ao enviar prompt.\n{msg}") from e
    return r.json()

def get_history(prompt_id: str) -> Dict[str, Any]:
    r = requests.get(f"{COMFY_URL}/history/{prompt_id}", timeout=REQ_TIMEOUT)
    r.raise_for_status()
    return r.json()

def wait_for_images(prompt_id: str, timeout_sec: float = 10.0, poll_interval: float = 0.5) -> Dict[str, Any]:
    """
    Espera até aparecer ao menos 1 imagem no history (ou até expirar timeout).
    Retorna sempre o último history consultado.
    """
    t0 = time.time()
    last = {}
    while time.time() - t0 < timeout_sec:
        h = get_history(prompt_id)
        last = h
        if _collect_images(h):
            return h
        time.sleep(poll_interval)
    return last

def _view_url(filename: str, subfolder: str = "", img_type: str = "output") -> str:
    return f"{COMFY_URL}/view?filename={filename}&subfolder={subfolder}&type={img_type}"

def _collect_images(history_json: Dict[str, Any]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for _pid, pdata in history_json.items():
        for node_out in pdata.get("outputs", {}).values():
            for img in node_out.get("images") or []:
                fname = img.get("filename")
                if not fname:
                    continue
                out.append({
                    "filename": fname,
                    "type": img.get("type", "output"),
                    "subfolder": img.get("subfolder", ""),
                })
    return out

# ---- Helpers de debug/consulta pública ----

def debug_list_images(history_json: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Retorna [{filename, type, subfolder, url}] de todas as imagens no history.
    Útil para exibir em tabela no Streamlit.
    """
    rows = []
    for rec in _collect_images(history_json):
        rows.append({
            "filename": rec["filename"],
            "type": rec["type"],
            "subfolder": rec["subfolder"],
            "url": _view_url(rec["filename"], rec["subfolder"], rec["type"]),
        })
    # Ordena por filename para ficar previsível
    rows.sort(key=lambda r: r["filename"])
    return rows

_num_pat = re.compile(r"_(\d{3,})_/?$")

def _extract_suffix_number(filename: str) -> int:
    """
    Extrai o número do padrão ..._00360_ -> 360; senão, -1.
    """
    m = _num_pat.search(filename)
    if not m:
        return -1
    try:
        return int(m.group(1))
    except Exception:
        return -1

def find_latest_image_by_prefix(history_json: Dict[str, Any], prefix: str, prefer_type: str = "output") -> Optional[Tuple[str, str]]:
    """
    Retorna (url, filename) MAIS RECENTE cujo nome começa com `prefix`.
    Criterio: maior sufixo numérico `_000NNN_`. Empata? prioriza `prefer_type`.
    """
    imgs = _collect_images(history_json)
    imgs = [i for i in imgs if i["filename"].startswith(prefix)]
    if not imgs:
        return None
    imgs.sort(key=lambda i: ((i["type"] != prefer_type), -_extract_suffix_number(i["filename"])))
    best = imgs[0]
    return _view_url(best["filename"], best["subfolder"], best["type"]), best["filename"]

def find_image_url_by_prefix(history_json: Dict[str, Any], prefix: str) -> Optional[Tuple[str, str]]:
    """
    Compat: primeira ocorrência do prefixo.
    Prefira find_latest_image_by_prefix para múltiplas saídas.
    """
    imgs = _collect_images(history_json)
    for img in imgs:
        if img["filename"].startswith(prefix):
            return _view_url(img["filename"], img["subfolder"], img["type"]), img["filename"]
    return None
