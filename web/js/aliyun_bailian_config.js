// web/js/aliyun_bailian_config.js
import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "NK.AIGC.AliyunBailianConfig",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "NK_AliyunBailianConfig") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

            // 在节点上添加一个「获取 API Key」按钮，点击后打开百炼控制台
            this.addWidget("button", "获取 API Key", null, () => {
                window.open(
                    "https://bailian.console.aliyun.com/?tab=model#/api-key",
                    "_blank"
                );
            });

            // 可选：添加一行说明文本
            this.addWidget("text", "提示", "地址默认已填好，只需填入密钥即可。");

            return r;
        };
    },
});