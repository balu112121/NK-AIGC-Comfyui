import { app } from "../../../scripts/app.js";

app.registerExtension({
  name: "NK.AIGC.XHSWriter",
  async beforeRegisterNodeDef(nodeType, nodeData, app) {
    if (nodeData.name === "NKXHSWriter") {
      const onNodeCreated = nodeType.prototype.onNodeCreated;
      nodeType.prototype.onNodeCreated = function () {
        if (onNodeCreated) {
          onNodeCreated.apply(this, arguments);
        }

        // 1. 节点标题（保持原生灰色）
        this.title = "南光AIGC-小红书文案";

        // 2. 汉化输入插槽
        const inputLabels = { image: "图像", text: "文本" };
        this.inputs?.forEach((i) => {
          if (inputLabels[i.name]) i.label = inputLabels[i.name];
        });

        // 3. 强力汉化控件 (针对多行文本框做特殊 DOM 处理)
        const widgetLabels = {
          api_key: "API密钥",
          topic: "主题",
          audience: "目标人群",
          temperature: "温度",
          model: "模型",
          base_url: "接口地址"
        };
        
        this.widgets?.forEach((w) => {
          if (widgetLabels[w.name]) {
            w.label = widgetLabels[w.name];
            // 如果是 textarea (多行文本)，原生框架有时不刷新 label，需要手动改 placeholder 和 DOM
            if (w.inputEl) {
              if (w.name === "topic") {
                w.inputEl.placeholder = "请输入主题或关键词（选填）";
                // 尝试修改 textarea 上的 label 节点
                if (w.inputEl.previousElementSibling) {
                  w.inputEl.previousElementSibling.textContent = "主题";
                }
              }
              if (w.name === "base_url") {
                w.inputEl.placeholder = "https://dashscope.aliyuncs.com/compatible-mode/v1";
                if (w.inputEl.previousElementSibling) {
                  w.inputEl.previousElementSibling.textContent = "接口地址";
                }
              }
            }
          }
        });

        // 4. 生成结果框
        const output = this.addWidget("text", "生成结果", "", () => {});
        if (output.inputEl) {
          output.inputEl.readOnly = true;
          output.inputEl.style.height = "160px";
        }
        this._nkOutput = output;

        // 5. 接收结果
        this.onExecuted = function (message) {
          const text = (message && message.text && message.text[0]) || "";
          if (this._nkOutput) this._nkOutput.value = text;
        };

        // 6. 设置节点大小，防止 base_url 撑爆
        this.setSize([420, 620]);
      };
    }
  }
});