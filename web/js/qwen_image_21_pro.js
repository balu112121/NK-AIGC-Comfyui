// NK-AIGC-Comfyui/web/js/qwen_image_21_pro.js

// 修复路径：因为 WEB_DIRECTORY 是 ./web/js，向上两级是 extensions，再到 scripts
import { app } from "../../scripts/app.js";

const NODE_TYPE = "NK_AIGC_QwenImage21Pro";
const DEFAULT_PROMPT = "南光AIGC丨AI绘画提示词、模型、图像、音频、视频、工作流定制，节点软件开发服务。";

// 核心函数：动态物理增删输入槽
function updateDynamicInputs(node) {
    if (!node.inputs) return;

    // 1. 计算已经连线的最大连续槽位
    let maxConnected = 0;
    let img0 = node.inputs.find(inp => inp.name === "图像");
    if (img0 && img0.link != null) {
        maxConnected = 1; // 代表 "图像" 有连接，需要显示到 "图像1"
        for (let i = 1; i <= 9; i++) {
            let inp = node.inputs.find(x => x.name === `图像${i}`);
            if (inp && inp.link != null) {
                maxConnected = i + 1; // 比如图像1有连接，需要显示到图像2
            } else {
                break;
            }
        }
    }
    
    const showCount = Math.min(maxConnected, 9);

    // 2. 从后往前，移除多余的槽位
    for (let i = 9; i >= 1; i--) {
        const slotName = `图像${i}`;
        const idx = node.inputs.findIndex(inp => inp.name === slotName);
        if (idx !== -1 && i > showCount) {
            const inp = node.inputs[idx];
            if (inp.link != null) {
                node.disconnectInput(idx);
            }
            node.removeInput(idx);
        }
    }

    // 3. 从左到右，补齐缺少的槽位
    for (let i = 1; i <= showCount; i++) {
        const slotName = `图像${i}`;
        const idx = node.inputs.findIndex(inp => inp.name === slotName);
        if (idx === -1) {
            node.addInput(slotName, "IMAGE");
        }
    }
    
    node.setSize(node.computeSize());
    app.graph.setDirtyCanvas(true, true);
}

// 提示词灰度颜色逻辑
function setupPromptColor(node) {
    const promptWidget = node.widgets?.find(w => w.name === "提示词");
    if (promptWidget && promptWidget.inputEl) {
        const textarea = promptWidget.inputEl;
        const checkColor = () => {
            textarea.style.color = (textarea.value === DEFAULT_PROMPT) ? "#888888" : "";
        };
        checkColor();
        textarea.addEventListener("input", checkColor);
        node._checkPromptColor = checkColor;
    }
}

app.registerExtension({
    name: "NK.AIGC.QwenImage21Pro",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== NODE_TYPE) return;

        // ── 节点创建时：暴力剔除多余的槽位 ──
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            if (onNodeCreated) onNodeCreated.apply(this, arguments);
            
            // 初始状态下，直接把 图像1~9 全部删掉，让界面极度清爽
            for (let i = 9; i >= 1; i--) {
                const idx = this.inputs.findIndex(inp => inp.name === `图像${i}`);
                if (idx !== -1) {
                    this.removeInput(idx);
                }
            }
            this.setSize(this.computeSize());

            setupPromptColor(this);
        };

        // ── 加载工作流时：恢复连线后，再执行清理 ──
        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (info) {
            if (onConfigure) onConfigure.apply(this, arguments);
            
            // 等待 ComfyUI 恢复连线后，根据实际情况重新整理端口
            setTimeout(() => {
                if (this._checkPromptColor) this._checkPromptColor();
                updateDynamicInputs(this);
            }, 50);
            setTimeout(() => updateDynamicInputs(this), 200);
        };

        // ── 连线状态改变时：动态增删 ──
        const onConnectionsChange = nodeType.prototype.onConnectionsChange;
        nodeType.prototype.onConnectionsChange = function (type, index, connected, link_info) {
            if (onConnectionsChange) onConnectionsChange.apply(this, arguments);
            setTimeout(() => updateDynamicInputs(this), 10);
            setTimeout(() => updateDynamicInputs(this), 50);
        };
    }
});