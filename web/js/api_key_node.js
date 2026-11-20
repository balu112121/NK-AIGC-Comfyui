// NK-AIGC-Comfyui/web/js/api_key_node.js
import { app } from "../../../scripts/app.js";

const NODE_CLASS = "NK_AIGC_APIKey";
const NODE_TITLE = "南光AIGC-API密钥";

app.registerExtension({
    name: "NK.AIGC.APIKey",

    async beforeRegisterNodeDef(nodeType, nodeData, appInstance) {
        if (nodeData.name !== NODE_CLASS) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;

        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);

            // 1. 强制设置节点原生标题
            this.title = NODE_TITLE;

            // 2. 隐藏后端定义的普通 api_key widget
            const oldWidget = this.widgets?.find(w => w.name === "api_key");
            if (oldWidget) {
                oldWidget.type = "hidden";
                oldWidget.computeSize = () => [0, -4];
                oldWidget.draw = () => {};
                oldWidget.serialize = false;
            }

            // 3. 读取工作流之前保存的旧值
            let initialValue = "";
            if (oldWidget && typeof oldWidget.value === "string") {
                initialValue = oldWidget.value;
            }

            // 4. 构建紧凑的横向 UI（已放大尺寸）
            const container = document.createElement("div");
            container.style.display = "flex";
            container.style.flexDirection = "row";
            container.style.alignItems = "center";
            container.style.gap = "12px"; // 加大输入框和按钮的间距
            container.style.width = "100%";
            container.style.boxSizing = "border-box";
            container.style.padding = "14px 16px"; // 加大上下左右内边距

            const input = document.createElement("input");
            input.type = "password";
            input.placeholder = "在此输入 API 密钥...";
            input.value = initialValue || "";
            input.style.flex = "1";
            input.style.padding = "10px 14px"; // 加大输入框内边距，让框变高
            input.style.borderRadius = "6px";
            input.style.border = "1px solid #555";
            input.style.background = "#1e1e1e";
            input.style.color = "#fff";
            input.style.fontSize = "16px"; // 加大字体
            input.style.outline = "none";
            input.style.minWidth = "0"; // 防止撑破

            // 防止 ComfyUI 画布拦截键盘快捷键
            input.addEventListener("focus", () => {
                if (app.canvas) app.canvas.node_widget = null;
            });

            const toggle = document.createElement("button");
            toggle.type = "button";
            toggle.textContent = "👁";
            toggle.title = "显示/隐藏密码";
            toggle.style.padding = "10px 14px"; // 加大按钮内边距
            toggle.style.cursor = "pointer";
            toggle.style.background = "#333";
            toggle.style.color = "#ddd";
            toggle.style.border = "1px solid #555";
            toggle.style.borderRadius = "6px";
            toggle.style.fontSize = "16px"; // 加大按钮图标
            toggle.style.flexShrink = "0";

            toggle.addEventListener("click", () => {
                if (input.type === "password") {
                    input.type = "text";
                    toggle.textContent = "🙈";
                } else {
                    input.type = "password";
                    toggle.textContent = "👁";
                }
            });

            container.appendChild(input);
            container.appendChild(toggle);

            // 同步到隐藏 widget 以保证工作流保存
            const syncToHidden = () => {
                if (oldWidget) oldWidget.value = input.value;
            };

            // 5. 添加 DOM Widget
            this.addDOMWidget(
                "api_key_dom",
                "NK_AIGC_PASSWORD",
                container,
                {
                    getValue: () => input.value,
                    setValue: (v) => {
                        input.value = v || "";
                        syncToHidden();
                    },
                    getMinHeight: () => 68, // 高度加大以适应大输入框
                }
            );

            input.addEventListener("input", syncToHidden);
            input.addEventListener("change", syncToHidden);

            // 6. 自动调整节点大小（把宽度加大到 380）
            requestAnimationFrame(() => {
                const size = this.computeSize();
                const width = Math.max(this.size[0], 380); // 最小宽度设为 380
                this.setSize([width, size[1]]);
            });

            // 清理事件
            const onRemoved = this.onRemoved;
            this.onRemoved = function () {
                input.removeEventListener("input", syncToHidden);
                input.removeEventListener("change", syncToHidden);
                return onRemoved?.apply(this, arguments);
            };

            // 工作流加载时恢复值
            const originalConfigure = this.configure;
            this.configure = function (info) {
                const r = originalConfigure?.apply(this, arguments);
                if (info?.widgets_values) {
                    const stored = info.widgets_values[0];
                    if (stored && !input.value) {
                        input.value = stored;
                        syncToHidden();
                    }
                }
                return r;
            };

            return result;
        };
    },
});