// web/js/nk_image_to_prompt_video.js
import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "NK.AIGC.ImageToPromptVideo",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "NK_ImageToPromptVideo") {
            // 预留前端扩展位：可在此添加按钮、样式或动态显隐逻辑
            // 当前版本所有交互均由 Python 端完成，无需额外 UI 操作
        }
    },
});