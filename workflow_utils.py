import json
from typing import Any, Dict, List
from config import BASE_POS_PROMPT, WORKFLOW_PATH

def load_workflow(path: str = WORKFLOW_PATH) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def is_editor(doc: Dict[str, Any]) -> bool:
    return isinstance(doc.get("nodes"), list) and isinstance(doc.get("links"), list)

def build_positive_prompt(user_extra: str) -> str:
    extra = (user_extra or "").strip()
    return BASE_POS_PROMPT if not extra else f"{BASE_POS_PROMPT}, {extra}"

def patch_workflow_for_filename_and_prompt_editor(
    wf: Dict[str, Any], filename: str, user_extra_prompt: str
) -> Dict[str, Any]:
    wf = json.loads(json.dumps(wf))
    pos_prompt = build_positive_prompt(user_extra_prompt)

    for n in wf.get("nodes", []):
        ntype = n.get("type")
        title = (n.get("title") or "").strip().lower()

        if ntype == "LoadImage":
            if "widgets_values" in n and n["widgets_values"]:
                n["widgets_values"][0] = filename
            if "widgets_values" in n and len(n["widgets_values"]) >= 2:
                n["widgets_values"][1] = "image"
            # remove IMAGEUPLOAD se houver
            n["inputs"] = [i for i in n.get("inputs", []) if i.get("type") != "IMAGEUPLOAD"]

        if ntype == "CLIPTextEncode" and title == "prompt positive":
            if "widgets_values" in n and n["widgets_values"]:
                n["widgets_values"][0] = pos_prompt
            else:
                n["widgets_values"] = [pos_prompt]
    return wf

# Conversão robusta Editor → API
IGNORED_NODE_TYPES = {
    "Reroute", "Note", "Group", "Primitive", "Text", "Accumulator", "XYPlot",
    "Viewer", "StickyNote", "Comment", "Markdown"
}

def editor_to_api_prompt(editor_json: Dict[str, Any], ui_seed: int, ui_denoise: float) -> Dict[str, Any]:
    nodes = editor_json.get("nodes", [])
    links = editor_json.get("links", [])
    link_by_id = {lk[0]: lk for lk in links if isinstance(lk, list) and len(lk) >= 6}
    node_by_id = {str(n["id"]): n for n in nodes if "id" in n}
    prompt: Dict[str, Any] = {}

    for n in nodes:
        nid = str(n.get("id"))
        ntype = n.get("type")
        if not ntype or ntype in IGNORED_NODE_TYPES:
            continue

        inputs_obj: Dict[str, Any] = {}
        inputs = n.get("inputs", [])
        widgets_vals: List[Any] = list(n.get("widgets_values", []))
        widget_idx = 0

        if ntype == "KSampler":
            for inp in inputs:
                name = inp.get("name")
                link_id = inp.get("link")
                itype = inp.get("type")
                if itype == "IMAGEUPLOAD":
                    continue
                if link_id is not None:
                    lk = link_by_id.get(link_id)
                    if lk:
                        from_node_id = str(lk[1])
                        from_slot_idx = lk[2]
                        src = node_by_id.get(from_node_id)
                        if src and src.get("type") not in IGNORED_NODE_TYPES:
                            inputs_obj[name] = [from_node_id, from_slot_idx]
            # tipagem explícita
            inputs_obj["seed"]         = int(ui_seed)
            inputs_obj["steps"]        = 20
            inputs_obj["cfg"]          = 5.0
            inputs_obj["sampler_name"] = "euler"
            inputs_obj["scheduler"]    = "normal"
            inputs_obj["denoise"]      = float(ui_denoise)

            prompt[nid] = {"class_type": ntype, "inputs": inputs_obj}
            continue

        for inp in inputs:
            name = inp.get("name")
            link_id = inp.get("link")
            itype = inp.get("type")
            has_widget = isinstance(inp.get("widget"), dict)

            if itype == "IMAGEUPLOAD":
                continue

            if link_id is not None:
                lk = link_by_id.get(link_id)
                if lk:
                    from_node_id = str(lk[1])
                    from_slot_idx = lk[2]
                    src = node_by_id.get(from_node_id)
                    if src and src.get("type") not in IGNORED_NODE_TYPES:
                        inputs_obj[name] = [from_node_id, from_slot_idx]
                continue

            if has_widget:
                if widget_idx < len(widgets_vals):
                    inputs_obj[name] = widgets_vals[widget_idx]
                widget_idx += 1

        prompt[nid] = {"class_type": ntype, "inputs": inputs_obj}

    return prompt
