import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "NK.AIGC.VAENodes",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // 强制注册显示名称
        if (nodeData.name === "NKVAEDecode") {
            nodeData.display_name = "南光AIGC-VAE解码(NK)";
        }
        if (nodeData.name === "NKVAEEncode") {
            nodeData.display_name = "南光AIGC-VAE编码(NK)";
        }
    },
    async nodeCreated(node) {
        // 精准映射输入输出端名称，完全复刻图片要求
        if (node.comfyClass === "NKVAEDecode") {
            if (node.inputs) {
                if (node.inputs[0]) node.inputs[0].label = "Latent";
                if (node.inputs[1]) node.inputs[1].label = "VAE";
            }
            if (node.outputs && node.outputs[0]) {
                node.outputs[0].label = "图像";
            }
        }
        if (node.comfyClass === "NKVAEEncode") {
            if (node.inputs) {
                if (node.inputs[0]) node.inputs[0].label = "图像";
                if (node.inputs[1]) node.inputs[1].label = "VAE";
            }
            if (node.outputs && node.outputs[0]) {
                node.outputs[0].label = "Latent";
            }
        }
    }
});