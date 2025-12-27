from dotenv import load_dotenv
import os

load_dotenv()

# ComfyUI
COMFY_URL      = os.getenv("COMFY_URL", "http://127.0.0.1:8188")
WORKFLOW_PATH  = os.getenv("WORKFLOW_PATH", "workflow.json")
UPLOAD_NAME    = os.getenv("UPLOAD_FILENAME", "live_canvas.png")

# Prefixos de saída
# Preview (512x512):
PREVIEW_PREFIX = os.getenv("PREVIEW_PREFIX", "pixelbuildings128-v1-upscale-x8-")
# Sprite para download (64x64):
ITEM_PREFIX    = os.getenv("ITEM_PREFIX",    "pixelbuildings128-v1-downscale-x8-")

# Canvas
CANVAS_W, CANVAS_H = 512, 512
CANVAS_BG_HEX      = "#000000"  # fundo preto opaco

# Prompt base (não exibido ao usuário)
BASE_POS_PROMPT = (
    "game icon institute, game icon, no humans, still life, simple background, "
    "black background, wuxia, dao, xinxia"
)

# Defaults UI
DEFAULT_SEED     = int(os.getenv("DEFAULT_SEED", "16340233486341"))
DEFAULT_DENOISE  = float(os.getenv("DEFAULT_DENOISE", "0.75"))

# Rede
REQ_TIMEOUT = 60
