// NK-AIGC-Comfyui/web/js/volcengine_ark_config.js
import { app } from "../../../scripts/app.js";

app.registerExtension({
    name: "NK.AIGC.VolcengineArkConfig",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "NK_AIGC_VolcengineArkConfig") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

            // 获取原生生成的输入组件
            const apiKeyWidget = this.widgets.find((w) => w.name === "api_key");
            const baseUrlWidget = this.widgets.find((w) => w.name === "base_url");

            // 延迟 100ms 确保 ComfyUI 的原生 DOM 渲染完毕后再进行覆盖
            setTimeout(() => {
                // 修改 API 密钥输入框：隐藏左侧原生标签，添加 placeholder
                if (apiKeyWidget) {
                    apiKeyWidget.label = "";
                    if (apiKeyWidget.inputEl) {
                        apiKeyWidget.inputEl.placeholder = "API密钥";
                    }
                }

                // 修改 地址输入框：隐藏左侧原生标签
                if (baseUrlWidget) {
                    baseUrlWidget.label = "";
                }
            }, 100);

            // 添加“获取 API Key” 按钮
            const btnWidget = this.addWidget("button", "获取 API Key", null, () => {
                window.open("https://console.volcengine.com/ark/region:ark+cn-beijing/apikey", "_blank");
            });
            btnWidget.serialize = false; // 不保存到工作流

            // 添加底部提示框
            // name 设为空，把整个提示文本放进 value 里，这样就和图2一样显示在同一行
            const tipWidget = this.addWidget(
                "text", 
                "", 
                "提示   地址默认已填好，只需填入密钥即可。", 
                null, 
                { serialize: false }
            );
            
            setTimeout(() => {
                if (tipWidget && tipWidget.inputEl) {
                    // 使用 readOnly 而不是 disabled，保证文字清晰可见
                    tipWidget.inputEl.readOnly = true; 
                    // 将鼠标光标改为默认箭头，提示用户无法编辑
                    tipWidget.inputEl.style.cursor = "default"; 
                }
            }, 100);

            // 稍微增加一点节点高度以容纳按钮和提示
            this.setSize([this.size[0], this.size[1] + 15]);

            return r;
        };
    },
});