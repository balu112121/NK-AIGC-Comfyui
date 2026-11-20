import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

app.registerExtension({
  name: "NK-AIGC.PositiveNegativePrompt",

  async beforeRegisterNodeDef(nodeType, nodeData, app) {
    if (nodeData.name !== "NKAIGC_PositiveNegativePrompt") return;

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

      const node = this;

      // ── 添加“自动反推负面提示词”按钮 ──────────────
      const btn = node.addWidget("button", "自动反推负面提示词", null, async () => {
        const posWidget = node.widgets.find((w) => w.name === "positive_prompt");
        const negWidget = node.widgets.find((w) => w.name === "negative_prompt");

        if (!posWidget || !negWidget) return;

        const positive = (posWidget.value || "").trim();
        if (!positive) {
          alert("请先填写正向提示词");
          return;
        }

        try {
          const resp = await api.fetchApi("/nk_aigc/auto_negative", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ positive_prompt: positive }),
          });

          if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
          const data = await resp.json();
          negWidget.value = data.negative_prompt || "";
          node.setDirtyCanvas(true, true);
        } catch (e) {
          console.error("[NK-AIGC] 反推失败:", e);
          alert("自动反推失败，请查看控制台日志");
        }
      });

      // 让按钮更显眼一些
      btn.serialize = false;

      return r;
    };
  },
});