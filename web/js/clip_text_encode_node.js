// NK-AIGC-Comfyui/web/js/clip_text_encode_node.js
import { app } from "../../scripts/app.js";

const NODE_TYPE = "NKCLIPTextEncode";

// 深灰色默认配色（与 ComfyUI 原生节点一致）
const NODE_COLOR = "#3a3a3a";      // 标题栏深灰
const NODE_BGCOLOR = "#2b2b2b";    // 节点主体深灰

const PLACEHOLDERS = {
    "正向提示词": "在此输入正向提示词，例如：masterpiece, best quality, 1girl, ...",
    "负向提示词": "在此输入负向提示词，例如：lowres, bad anatomy, worst quality, ...",
};

function applyPlaceholder(widget) {
    const text = PLACEHOLDERS[widget.name];
    if (!text) return;

    // 不同 ComfyUI 版本里多行输入框的 DOM 引用字段不同，统一兜底处理
    const el = widget.inputEl || widget.element || widget.textarea;
    if (!el) return;

    try {
        el.setAttribute("placeholder", text);
    } catch (_) {}
    try {
        el.placeholder = text;
    } catch (_) {}
}

function setupNode(node) {
    for (const widget of node.widgets || []) {
        applyPlaceholder(widget);
    }

    // 深灰色默认配色（覆盖 LiteGraph 默认值，保证视觉统一）
    node.color = NODE_COLOR;
    node.bgcolor = NODE_BGCOLOR;

    // 默认尺寸更大，方便编辑长提示词
    const width = Math.max(node.size?.[0] || 0, 380);
    const height = Math.max(node.size?.[1] || 0, 320);
    node.setSize?.([width, height]);
}

app.registerExtension({
    name: "NK-AIGC.CLIPTextEncode",
    async nodeCreated(node) {
        if (node.comfyClass !== NODE_TYPE) return;
        setupNode(node);
    },
});