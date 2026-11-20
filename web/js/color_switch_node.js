// NK-AIGC-Comfyui/web/js/color_switch_node.js
// 为「南光AIGC-颜色切换」的 4 个颜色输入增加可视化取色按钮（不参与序列化）
import { app } from "../../scripts/app.js";

const COLOR_WIDGET_NAMES = ["颜色1", "颜色2", "颜色3", "颜色4"];
const HEX_RE = /^#?([0-9a-fA-F]{6})$/;

const NAMED_COLORS = {
    "红": "#FF0000", "红色": "#FF0000",
    "绿": "#00FF00", "绿色": "#00FF00",
    "蓝": "#0000FF", "蓝色": "#0000FF",
    "白": "#FFFFFF", "白色": "#FFFFFF",
    "黑": "#000000", "黑色": "#000000",
    "黄": "#FFFF00", "黄色": "#FFFF00",
    "紫": "#800080", "紫色": "#800080",
    "橙": "#FFA500", "橙色": "#FFA500",
};

function toHexColor(value) {
    const text = String(value ?? "").trim();
    const matched = text.match(HEX_RE);
    if (matched) return "#" + matched[1].toUpperCase();
    return NAMED_COLORS[text] || "#FF0000";
}

function openColorPicker(currentValue, onPick) {
    const picker = document.createElement("input");
    picker.type = "color";
    picker.value = toHexColor(currentValue);
    picker.style.position = "fixed";
    picker.style.left = "-9999px";
    picker.style.top = "-9999px";
    document.body.appendChild(picker);

    picker.addEventListener("input", () => onPick(picker.value.toUpperCase()));
    picker.addEventListener("change", () => {
        onPick(picker.value.toUpperCase());
        picker.remove();
    });
    picker.click();
}

app.registerExtension({
    name: "NK-AIGC.ColorSwitch",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "NKColorSwitch") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);

            for (const name of COLOR_WIDGET_NAMES) {
                const widget = this.widgets?.find((w) => w.name === name);
                if (!widget) continue;
                if (widget.__nkColorButton) continue;

                const button = this.addWidget(
                    "button",
                    `${name} 选色`,
                    null,
                    () => {
                        openColorPicker(widget.value, (hex) => {
                            widget.value = hex;
                            app.graph.setDirtyCanvas(true, true);
                        });
                    },
                    { serialize: false }
                );
                if (button) {
                    button.serialize = false;
                    button.options = { ...(button.options || {}), serialize: false };
                    widget.__nkColorButton = button;
                }
            }

            return result;
        };
    },
});