import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "NK-AIGC-Comfyui.SaveText",
    async nodeCreated(node) {
        if (node.comfyClass !== "NKSaveText") return;

        const tip = document.createElement("div");
        tip.style.cssText = `
            padding: 4px 8px;
            margin-top: 4px;
            font-size: 11px;
            color: #aaa;
            background: rgba(255,255,255,0.06);
            border-radius: 4px;
            text-align: center;
            pointer-events: none;
        `;
        tip.textContent = "保存至 input/南光AIGC.txt";

        const container = document.createElement("div");
        container.style.cssText = "width: 100%;";
        container.appendChild(tip);

        node.addDOMWidget(
            "nk_save_tip",
            "div",
            container,
            { serialize: false }
        );

        node.setSize([280, node.size[1]]);
    },
});