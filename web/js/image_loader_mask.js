import { app } from "../../../scripts/app.js";

app.registerExtension({
    name: "NK.AIGC.LoadImageMask",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "NK_LoadImageMask") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            onNodeCreated?.apply(this, arguments);
            const node = this;

            const imgWidget = node.widgets.find(w => w.name === "image");
            if (imgWidget) imgWidget.label = "图像文件"; 

            const ratioWidget = node.widgets.find(w => w.name === "宽高比");
            const cropWWidget = node.widgets.find(w => w.name === "裁剪宽度");
            const cropHWidget = node.widgets.find(w => w.name === "裁剪高度");

            let currentOrigW = 0;
            let currentOrigH = 0;

            const updateDimensions = () => {
                if (currentOrigW === 0 || currentOrigH === 0) return;
                
                const ratioText = ratioWidget ? ratioWidget.value : "原始比例";
                let targetW = currentOrigW;
                let targetH = currentOrigH;

                if (ratioText !== "原始比例") {
                    const ratios = {
                        "1:1 (Square)": 1/1,
                        "2:3 (Portrait Photo)": 2/3,
                        "3:2 (Photo)": 3/2,
                        "3:4 (Portrait Standard)": 3/4,
                        "4:3 (Standard)": 4/3,
                        "9:16 (Portrait Widescreen)": 9/16,
                        "16:9 (Widescreen)": 16/9,
                        "21:9 (Ultrawide)": 21/9
                    };
                    
                    const r = ratios[ratioText];
                    targetW = currentOrigW;
                    targetH = Math.round(targetW / r);
                    
                    if (targetH > currentOrigH) {
                        targetH = currentOrigH;
                        targetW = Math.round(targetH * r);
                    }
                }
                
                if (cropWWidget) cropWWidget.value = targetW;
                if (cropHWidget) cropHWidget.value = targetH;
                node.setDirtyCanvas(true, true);
            };

            const loadImageSize = (filename) => {
                if (!filename || filename === "None") return;
                const cleanName = filename.split(" ")[0];
                const img = new Image();
                img.src = `/view?filename=${encodeURIComponent(cleanName)}&type=input&rand=${Math.random()}`;
                img.onload = () => {
                    currentOrigW = img.naturalWidth;
                    currentOrigH = img.naturalHeight;
                    updateDimensions();
                };
            };

            if (imgWidget) {
                const origCallback = imgWidget.callback;
                imgWidget.callback = function () {
                    if (origCallback) origCallback.apply(this, arguments);
                    loadImageSize(this.value);
                };
            }

            if (ratioWidget) {
                const origRatioCallback = ratioWidget.callback;
                ratioWidget.callback = function () {
                    if (origRatioCallback) origRatioCallback.apply(this, arguments);
                    updateDimensions();
                };
            }

            node.addWidget("button", "🎨 切换 RGB", null, () => {
                const modeWidget = node.widgets.find(w => w.name === "处理模式");
                if (modeWidget) modeWidget.value = "RGB"; 
                node.setDirtyCanvas(true, true);
            });

            node.addWidget("button", "⬛ 切换 Alpha", null, () => {
                const modeWidget = node.widgets.find(w => w.name === "处理模式");
                if (modeWidget) modeWidget.value = "Alpha"; 
                node.setDirtyCanvas(true, true);
            });

            setTimeout(() => {
                if (imgWidget && imgWidget.value) {
                    loadImageSize(imgWidget.value);
                }
            }, 300);
        };
    },
});