import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const SKILL_NODE = "NKSkillNode";

app.registerExtension({
    name: "NK-AIGC.SkillNode",

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== SKILL_NODE) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = onNodeCreated?.apply(this, arguments);

            // 上传按钮
            const zipWidget = this.widgets?.find((w) => w.name === "SKILL加载");
            if (zipWidget) {
                const uploadBtn = this.addWidget("button", "📤 上传SKILL包", null, async () => {
                    const input = document.createElement("input");
                    input.type = "file";
                    input.accept = ".zip";
                    input.onchange = async () => {
                        const file = input.files?.[0];
                        if (!file) return;
                        const form = new FormData();
                        form.append("image", file);
                        form.append("type", "input");
                        form.append("subfolder", "nk_skills");
                        try {
                            const resp = await api.fetchApi("/upload/image", { method: "POST", body: form });
                            if (!resp.ok) throw new Error("上传失败");
                            const data = await resp.json();
                            if (data.name) {
                                zipWidget.value = data.name;
                                if (!zipWidget.options.values.includes(data.name)) {
                                    zipWidget.options.values.push(data.name);
                                }
                                this.setDirtyCanvas(true, true);
                            }
                        } catch (e) {
                            alert("上传技能包失败：" + e.message);
                        }
                    };
                    input.click();
                });
                uploadBtn.serialize = false;
            }

            // API_KEY 密码框
            setTimeout(() => {
                const apiKeyWidget = this.widgets?.find((w) => w.name === "API_KEY");
                if (apiKeyWidget) {
                    const inputEl = apiKeyWidget.inputEl || apiKeyWidget.element;
                    if (inputEl && inputEl.tagName === "INPUT") {
                        inputEl.type = "password";
                        inputEl.placeholder = "在此粘贴 API Key";
                    }
                }
            }, 100);

            return r;
        };
    },
});