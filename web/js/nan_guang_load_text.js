import { app } from "../../../scripts/app.js";

app.registerExtension({
    name: "NK.AIGC.NanGuang.LoadText",

    async nodeCreated(node) {
        // 兼容性判断，确保只对当前节点生效
        if (node.comfyClass !== "NanGuangLoadText" && node.type !== "NanGuangLoadText") return;

        // 查找 text widget
        let textWidget = null;
        for (let i = 0; i < node.widgets.length; i++) {
            if (node.widgets[i].name === "text") {
                textWidget = node.widgets[i];
                break;
            }
        }
        if (!textWidget) return;

        // 直接添加原生按钮
        const loadBtn = node.addWidget("button", "加载文本文件", null, function () {
            // 点击按钮时动态创建 input，避免多开隐藏元素
            const fileInput = document.createElement("input");
            fileInput.type = "file";
            fileInput.accept = ".txt,.md,.json,.csv,.py,.yaml,.yml,.xml,.html,.ini,.cfg,.log,.text";
            
            fileInput.onchange = (event) => {
                const file = event.target.files[0];
                if (!file) return;

                const reader = new FileReader();
                reader.onload = (e) => {
                    const content = e.target.result;
                    if (typeof content === "string") {
                        // 填充内容
                        textWidget.value = content;
                        
                        // 触发值改变回调
                        if (typeof textWidget.callback === "function") {
                            textWidget.callback(content);
                        }
                        
                        // 强制画布重绘
                        node.setDirtyCanvas(true, true);
                        app.graph.setDirtyCanvas(true, true);
                    }
                };
                reader.onerror = () => alert("读取文件失败，请确认编码为 UTF-8。");
                reader.readAsText(file, "UTF-8");
            };
            fileInput.click();
        });

        // 防止按钮状态被保存到 JSON 中
        if (loadBtn) {
            loadBtn.serialize = false;
        }

        // 自动调整节点高度，确保新加的按钮能显示出来
        const currentSize = node.size;
        const minSize = node.computeSize();
        if (minSize[1] > currentSize[1]) {
            node.setSize([currentSize[0], minSize[1]]);
        }
    },
});