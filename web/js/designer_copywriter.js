// NK-AIGC-Comfyui/web/js/designer_copywriter.js

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const NODE_TYPE = "NKDesignerCopywriter";

app.registerExtension({
    name: "NK.AIGC.DesignerCopywriter",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== NODE_TYPE) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            onNodeCreated?.apply(this, arguments);

            // ── 中文化控件标签 ────────────────────────────────
            const labelMap = {
                conversation: "会话内容",
                api_key: "API 密钥",
                model: "模型选择",
                temperature: "创意温度",
                api_base_override: "API Base URL（进阶）",
            };

            this.widgets?.forEach((w) => {
                if (labelMap[w.name]) {
                    w.label = labelMap[w.name];
                }
            });

            // 隐藏进阶字段
            const baseWidget = this.widgets?.find((w) => w.name === "api_base_override");
            if (baseWidget) {
                baseWidget.type = "hidden";
                baseWidget.computeSize = () => [0, -4];
            }

            // ── 添加「测试连接」按钮 ──────────────────────────
            const testBtn = this.addWidget(
                "button",
                "🔗 测试 API 连接",
                null,
                async () => {
                    const modelWidget = this.widgets?.find((w) => w.name === "model");
                    const keyWidget = this.widgets?.find((w) => w.name === "api_key");
                    const model = modelWidget?.value ?? "";
                    const apiKey = keyWidget?.value ?? "";

                    if (!model || !apiKey) {
                        alert("请先填写模型和 API 密钥。");
                        return;
                    }

                    testBtn.name = "⏳ 正在测试...";
                    try {
                        const resp = await api.fetchApi("/nk_aigc/designer_copywriter/test_api", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ model, api_key: apiKey }),
                        });
                        
                        // 读取文本防止解析非 JSON 崩溃
                        const rawText = await resp.text();
                        let data;
                        try {
                            data = JSON.parse(rawText);
                        } catch (parseError) {
                            alert(`接口返回了非 JSON 内容（HTTP ${resp.status}）：\n\n${rawText.slice(0, 300)}`);
                            return;
                        }

                        alert(data.message || (data.ok ? "连接成功" : "连接失败"));
                    } catch (e) {
                        alert("测试请求失败：" + e);
                    } finally {
                        testBtn.name = "🔗 测试 API 连接";
                    }
                }
            );

            // 调整节点尺寸
            const sz = this.computeSize();
            this.setSize([Math.max(sz[0], 360), sz[1]]);
        };
    },
});