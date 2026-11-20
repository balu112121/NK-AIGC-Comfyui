import { app } from "../../scripts/app.js";

const ASPECT_RATIO_MAP = {
    "1:1(Square)": { width: 512, height: 512 },
    "2:3 (Portrait Photo)": { width: 512, height: 768 },
    "3:2 (Photo)": { width: 768, height: 512 },
    "3:4 (Portrait Standard)": { width: 576, height: 768 },
    "4:3 (Standard)": { width: 768, height: 576 },
    "9:16 (Portrait Widescreen)": { width: 432, height: 768 },
    "16:9 (Widescreen)": { width: 768, height: 432 },
    "21:9 (Ultrawide)": { width: 1008, height: 432 },
    "自定义": null,
};

const CUSTOM_RATIO = "自定义";

app.registerExtension({
    name: "NK.AIGC.EmptyLatentPreset",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "NK_AIGC_EmptyLatentPreset") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

            const node = this;
            const ratioWidget = node.widgets.find((w) => w.name === "宽高比");
            const widthWidget = node.widgets.find((w) => w.name === "宽度");
            const heightWidget = node.widgets.find((w) => w.name === "高度");
            if (!ratioWidget || !widthWidget || !heightWidget) return r;

            // 核心修复：清理历史脏数据，防止 NaN 卡死
            const fixNaN = (widget, fallback) => {
                if (isNaN(widget.value) || widget.value === undefined || widget.value === null || String(widget.value) === "NaN") {
                    widget.value = fallback;
                }
            };
            fixNaN(widthWidget, 512);
            fixNaN(heightWidget, 768);

            const updateState = () => {
                const isCustom = ratioWidget.value === CUSTOM_RATIO;
                
                // 如果是预设，自动应用数值
                if (!isCustom) {
                    const size = ASPECT_RATIO_MAP[ratioWidget.value];
                    if (size) {
                        widthWidget.value = size.width;
                        heightWidget.value = size.height;
                    }
                }

                // 原生的禁用/启用（禁用后无法点击，也不会产生任何输入）
                widthWidget.disabled = !isCustom;
                heightWidget.disabled = !isCustom;
                
                // 视觉提示：改变标签名称
                widthWidget.label = isCustom ? "宽度" : "宽度 (自动)";
                heightWidget.label = isCustom ? "高度" : "高度 (自动)";
                
                node.setDirtyCanvas(true, true);
            };

            // 监听下拉框变化
            const origRatioCallback = ratioWidget.callback;
            ratioWidget.callback = function(value, ...args) {
                if (origRatioCallback) origRatioCallback.apply(this, args);
                updateState();
            };

            // 初始化状态
            setTimeout(updateState, 50);

            return r;
        };

        // 确保工作流从保存文件加载时也能正确恢复状态
        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (info) {
            const r = onConfigure ? onConfigure.apply(this, arguments) : undefined;
            const node = this;
            const ratioWidget = node.widgets.find((w) => w.name === "宽高比");
            const widthWidget = node.widgets.find((w) => w.name === "宽度");
            const heightWidget = node.widgets.find((w) => w.name === "高度");
            
            if (ratioWidget && widthWidget && heightWidget) {
                if (isNaN(widthWidget.value) || widthWidget.value === undefined || String(widthWidget.value) === "NaN") widthWidget.value = 512;
                if (isNaN(heightWidget.value) || heightWidget.value === undefined || String(heightWidget.value) === "NaN") heightWidget.value = 768;
                
                const isCustom = ratioWidget.value === CUSTOM_RATIO;
                if (!isCustom) {
                    const size = ASPECT_RATIO_MAP[ratioWidget.value];
                    if (size) {
                        widthWidget.value = size.width;
                        heightWidget.value = size.height;
                    }
                }
                widthWidget.disabled = !isCustom;
                heightWidget.disabled = !isCustom;
                widthWidget.label = isCustom ? "宽度" : "宽度 (自动)";
                heightWidget.label = isCustom ? "高度" : "高度 (自动)";
            }
            return r;
        };
    },
});