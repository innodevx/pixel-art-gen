# app.py
import os
import time
import json
import random
import requests
import streamlit as st
from PIL import Image

from config import (
    COMFY_URL, WORKFLOW_PATH, UPLOAD_NAME,
    PREVIEW_PREFIX, ITEM_PREFIX,
    CANVAS_W, CANVAS_H, DEFAULT_SEED, DEFAULT_DENOISE
)
from comfy_api import (
    upload_image, post_prompt, get_history,
    find_latest_image_by_prefix, debug_list_images
)
from workflow_utils import (
    load_workflow, is_editor,
    patch_workflow_for_filename_and_prompt_editor, editor_to_api_prompt
)
from image_utils import pil_to_png_bytes, sha1_bytes
from ui_selection import draw_mode, select_mode


# ---------------- Página / Estado básico ----------------
st.set_page_config(page_title="Comfy Live Painter — realtime", layout="wide")
st.title("🖌️ Comfy Live Painter — realtime")

# Estado principal
if "mode" not in st.session_state:                 st.session_state.mode = "draw"
if "seed" not in st.session_state:                 st.session_state.seed = DEFAULT_SEED
if "denoise" not in st.session_state:              st.session_state.denoise = DEFAULT_DENOISE
if "user_prompt_extra" not in st.session_state:    st.session_state.user_prompt_extra = ""

# Imagem atual / hashes
if "current_img" not in st.session_state:
    st.session_state.current_img = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 255))
if "last_canvas_hash" not in st.session_state:     st.session_state.last_canvas_hash = ""
if "last_generated_hash" not in st.session_state:  st.session_state.last_generated_hash = ""

# Fila de prompts (para polling) e últimos resultados
if "pending_pids" not in st.session_state:         st.session_state.pending_pids = []  # list[str]
if "last_preview" not in st.session_state:         st.session_state.last_preview = None  # (url, filename)
if "last_item" not in st.session_state:            st.session_state.last_item = None     # (url, filename)

# Debug: última lista de imagens e último history bruto (parcial)
if "last_debug_rows" not in st.session_state:      st.session_state.last_debug_rows = []
if "last_debug_hist" not in st.session_state:      st.session_state.last_debug_hist = {}


# ---------------- Funções internas ----------------
def _generate_now(server_filename: str):
    """Monta prompt (Editor->API) e dispara geração no Comfy. Guarda prompt_id para polling."""
    raw = load_workflow()
    if not is_editor(raw):
        st.error("O workflow precisa estar no formato do Editor (nodes/links).")
        return

    wf_editor = patch_workflow_for_filename_and_prompt_editor(
        raw, server_filename, st.session_state.user_prompt_extra
    )
    api_prompt = editor_to_api_prompt(
        wf_editor, ui_seed=st.session_state.seed, ui_denoise=float(st.session_state.denoise)
    )

    resp = post_prompt(api_prompt)
    pid = resp.get("prompt_id")
    if pid:
        st.session_state.pending_pids.append(pid)


def _maybe_generate_on_canvas_change():
    """
    Gera imediatamente se a imagem mudou (hash diferente do último gerado).
    Chamado após desenhar/soltar ou arrastar seleção.
    """
    png = pil_to_png_bytes(st.session_state.current_img)
    cur_hash = sha1_bytes(png)
    st.session_state.last_canvas_hash = cur_hash

    if cur_hash != st.session_state.last_generated_hash:
        server_filename = f"{os.path.splitext(UPLOAD_NAME)[0]}-{cur_hash[:10]}.png"
        upload_image(png, server_filename)
        _generate_now(server_filename)
        st.session_state.last_generated_hash = cur_hash


def _poll_pending_histories():
    """
    A cada execução (a cada 0,5s), consulta os prompt_ids pendentes.
    Atualiza preview (512) e item 64 se aparecerem imagens.
    Mantém o que ainda não retornou na fila.
    """
    if not st.session_state.pending_pids:
        return

    still = []
    # Processa no máx. 5 pids mais recentes, do mais novo ao mais velho
    for pid in list(st.session_state.pending_pids)[-5:][::-1]:
        try:
            hist = get_history(pid)
        except Exception:
            still.append(pid)  # tenta de novo no próximo tick
            continue

        rows = debug_list_images(hist)
        if rows:
            st.session_state.last_debug_rows = rows
            # evita armazenar JSON gigante
            try:
                st.session_state.last_debug_hist = {k: hist[k] for k in list(hist.keys())[:3]}
            except Exception:
                st.session_state.last_debug_hist = {}

            prev = find_latest_image_by_prefix(hist, PREVIEW_PREFIX, prefer_type="output")
            if prev:
                st.session_state.last_preview = prev

            item = find_latest_image_by_prefix(hist, ITEM_PREFIX, prefer_type="output")
            if item:
                st.session_state.last_item = item

            # Se pelo menos um dos dois apareceu, consideramos pronto e tiramos da fila
            if prev or item:
                continue

        # Continua pendente
        still.append(pid)

    st.session_state.pending_pids = still


# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown("### Config")
    st.write("**COMFY_URL:**", COMFY_URL)
    st.write("**WORKFLOW_PATH:**", WORKFLOW_PATH)
    st.write("**UPLOAD_NAME:**", UPLOAD_NAME)
    st.write("**PREVIEW_PREFIX (512):**", PREVIEW_PREFIX)
    st.write("**ITEM_PREFIX (64):**", ITEM_PREFIX)
    st.caption("Edite no `.env` e recarregue.")


# ---------------- Layout principal ----------------
col1, col2 = st.columns([1.3, 1], vertical_alignment="top")

with col1:
    st.subheader("Canvas (512×512)")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("✏️ Desenhar", use_container_width=True):
            st.session_state.mode = "draw"
            st.session_state.selection_rect_prev = None
            st.rerun()
    with c2:
        if st.button("📐 Selecionar/Arrastar", use_container_width=True):
            st.session_state.mode = "select"
            st.session_state.selection_rect_prev = None
            st.rerun()
    with c3:
        if st.button("🧹 Limpar Canvas", use_container_width=True):
            st.session_state.current_img = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 255))
            st.session_state.selection_rect_prev = None
            st.session_state.last_canvas_hash = ""
            st.session_state.last_generated_hash = ""
            st.rerun()

    # Modo atual
    if st.session_state.mode == "draw":
        st.session_state.current_img = draw_mode(st.session_state.current_img)
        # Gera imediatamente quando o traço foi consolidado pelo componente
        _maybe_generate_on_canvas_change()
    else:
        # Selecionar/arrastar
        if "selection_rect_prev" not in st.session_state:
            st.session_state.selection_rect_prev = None
        st.session_state.current_img, st.session_state.selection_rect_prev = select_mode(
            st.session_state.current_img, st.session_state.selection_rect_prev
        )
        # Gera após arrastar (imagem mudou)
        _maybe_generate_on_canvas_change()

    st.markdown("---")
    st.subheader("Prompt extra, Seed & Precisão (denoise)")

    st.session_state.user_prompt_extra = st.text_area(
        "Prompt (extra opcional)",
        value=st.session_state.user_prompt_extra,
        placeholder="Digite aqui para complementar o prompt base…",
        height=100,
        help="O prompt base é fixo e invisível; o texto aqui é concatenado a ele.",
        key="prompt_extra",
    )

    cA, cB, cC = st.columns(3)
    with cA:
        st.session_state.seed = int(st.number_input("Seed", value=int(st.session_state.seed), min_value=0, step=1))
    with cB:
        if st.button("🎲 Randomizar seed", use_container_width=True):
            # Ao randomizar seed, geramos imediatamente com a mesma imagem atual
            st.session_state.seed = random.getrandbits(63)
            png = pil_to_png_bytes(st.session_state.current_img)
            cur_hash = sha1_bytes(png)
            server_filename = f"{os.path.splitext(UPLOAD_NAME)[0]}-{cur_hash[:10]}.png"
            upload_image(png, server_filename)
            _generate_now(server_filename)
    with cC:
        if st.button("▶️ Gerar novamente (mesma imagem)", use_container_width=True):
            # Gera com a imagem atual (mesmo hash/arquivo)
            png = pil_to_png_bytes(st.session_state.current_img)
            cur_hash = sha1_bytes(png)
            server_filename = f"{os.path.splitext(UPLOAD_NAME)[0]}-{cur_hash[:10]}.png"
            upload_image(png, server_filename)
            _generate_now(server_filename)

    st.session_state.denoise = st.slider(
        "Precisão (denoise)", 0.0, 1.0, float(st.session_state.denoise), 0.01,
        help="0 preserva mais a entrada; 1 altera mais. Padrão 0.75.",
    )


with col2:
    st.subheader("Saída do Comfy (atualiza continuamente)")

    # Polling dos histories pendentes (não bloqueia; roda a cada 0,5s por causa do loop final)
    _poll_pending_histories()

    # Preview (512×512) se já houver
    st.markdown("#### Preview (512×512)")
    if st.session_state.last_preview:
        prev_url, prev_name = st.session_state.last_preview
        try:
            st.image(prev_url, caption=prev_name, use_container_width=True)
        except TypeError:
            st.image(prev_url, caption=prev_name, use_column_width=True)
    else:
        st.info("Aguardando preview...")

    # Download 64×64 se já houver
    st.markdown("---")
    st.subheader("Baixar Item/Block 64×64 (OUTPUT)")
    st.caption(f"Prefixo: `{ITEM_PREFIX}` (SaveImage 64×64)")
    if st.session_state.last_item:
        item_url, fname = st.session_state.last_item
        try:
            r = requests.get(item_url, timeout=60)
            r.raise_for_status()
            st.download_button(
                "⬇️ Baixar PNG (64×64)",
                data=r.content,
                file_name=fname if fname.endswith(".png") else f"{fname}.png",
                mime="image/png",
            )
        except Exception as e:
            st.warning(f"Download falhou: {e}")
    else:
        st.info("Aguardando sprite 64×64...")

    # Painel de Debug
    with st.expander("🔎 Debug — Últimas imagens do history"):
        rows = st.session_state.last_debug_rows or []
        if rows:
            st.table(rows)
        else:
            st.caption("Sem imagens listadas ainda.")
        if st.checkbox("Mostrar JSON bruto (parcial)"):
            try:
                st.code(json.dumps(st.session_state.last_debug_hist, indent=2)[:15000], language="json")
            except Exception:
                st.write(st.session_state.last_debug_hist)


# ---------------- Loop contínuo (0,5s) ----------------
# Sem funções experimentais: reexecuta o app suavemente a cada meio segundo
time.sleep(0.5)
st.rerun()
