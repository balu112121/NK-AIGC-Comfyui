import { app } from "../../scripts/app.js";

const NODE_CLASS = "NKNodeEncryptNode";
const ADMIN_PASSWORD = "TUIN666";
// 密码规则：7位，纯字母、纯数字或字母+数字均可
const USER_PASSWORD_REGEX = /^[A-Za-z0-9]{7}$/;

// ── 暗黑风密码输入弹窗 ────────────────
function showPasswordModal() {
    return new Promise((resolve) => {
        const overlay = document.createElement("div");
        Object.assign(overlay.style, {
            position: "fixed", top: 0, left: 0, width: "100vw", height: "100vh",
            background: "rgba(0,0,0,0.6)", zIndex: 10000,
            display: "flex", justifyContent: "center", alignItems: "center"
        });

        const modal = document.createElement("div");
        Object.assign(modal.style, {
            background: "#222", color: "#eee", padding: "20px",
            borderRadius: "10px", width: "380px", fontFamily: "sans-serif",
            boxShadow: "0 4px 15px rgba(0,0,0,0.8)", border: "1px solid #333"
        });

        const header = document.createElement("div");
        header.style.display = "flex";
        header.style.justifyContent = "space-between";
        header.style.marginBottom = "20px";
        header.innerHTML = `<span style="font-weight:bold; font-size:16px;">南光AI文本加密 - 输入密码</span>`;
        const closeBtn = document.createElement("span");
        closeBtn.innerHTML = "&times;";
        closeBtn.style.cursor = "pointer";
        closeBtn.style.fontSize = "20px";
        closeBtn.onclick = () => { document.body.removeChild(overlay); resolve(null); };
        header.appendChild(closeBtn);
        modal.appendChild(header);

        const msg = document.createElement("div");
        msg.innerText = "请输入解锁密码以查看加密内容：";
        msg.style.marginBottom = "15px";
        msg.style.fontSize = "13px";
        msg.style.color = "#aaa";
        modal.appendChild(msg);

        const inputEl = document.createElement("input");
        Object.assign(inputEl.style, {
            width: "100%", padding: "12px", marginBottom: "20px",
            background: "#1a1a1a", border: "1px solid #444",
            borderRadius: "20px", color: "#fff", boxSizing: "border-box",
            outline: "none", fontSize: "16px", textAlign: "center"
        });
        inputEl.type = "password";
        modal.appendChild(inputEl);

        const btn = document.createElement("button");
        btn.innerText = "确认";
        Object.assign(btn.style, {
            width: "100%", padding: "12px", background: "#333",
            border: "1px solid #444", borderRadius: "20px", color: "#fff",
            cursor: "pointer", fontWeight: "bold", fontSize: "16px"
        });
        btn.onmouseover = () => btn.style.background = "#444";
        btn.onmouseout = () => btn.style.background = "#333";
        
        btn.onclick = () => {
            document.body.removeChild(overlay);
            resolve(inputEl.value);
        };
        modal.appendChild(btn);

        overlay.appendChild(modal);
        document.body.appendChild(overlay);
        
        inputEl.focus();
        inputEl.onkeydown = (e) => { if (e.key === "Enter") btn.click(); };
    });
}

// ── 安全控制显隐（完美还原高度和 DOM） ──────────────────────
function setWidgetVisible(w, visible) {
    if (!w) return;
    // 仅首次记录原始状态，绝对不碰 type 属性
    if (!w._backedUp) {
        w._origComputeSize = w.computeSize;
        w._origDraw = w.draw;
        w._backedUp = true;
    }

    if (visible) {
        w.computeSize = w._origComputeSize;
        w.draw = w._origDraw;
        if (w.inputEl) w.inputEl.style.display = "block";
    } else {
        w.computeSize = () => [0, -4]; // 占据负空间，不留空白
        w.draw = () => {}; // 不绘制
        if (w.inputEl) w.inputEl.style.display = "none";
    }
}

// ── 切换节点 UI 状态 ────────────────────────────────
function applyUI(node) {
    const isEncW = node.widgets.find(w => w.name === "is_encrypted");
    const textW = node.widgets.find(w => w.name === "text");
    const pwdW = node.widgets.find(w => w.name === "password_setting");
    const switchW = node.widgets.find(w => w.name === "password_switch");
    const encW = node.widgets.find(w => w.name === "encrypted_text");

    if (!isEncW) return;

    setWidgetVisible(encW, false);
    setWidgetVisible(isEncW, false);

    if (isEncW.value) {
        // 加密状态：隐藏输入组件，变为 120 高度
        setWidgetVisible(textW, false);
        setWidgetVisible(pwdW, false);
        setWidgetVisible(switchW, false);
        node.setSize([node.size[0], 120]);
    } else {
        // 未加密状态：恢复所有组件，高度恢复至 290（完美容纳图2的所有组件）
        setWidgetVisible(textW, true);
        setWidgetVisible(pwdW, true);
        setWidgetVisible(switchW, true);
        node.setSize([node.size[0], 290]);
    }
    node.setDirtyCanvas(true, true);
}

// ── Canvas 绘制加密后锁定画面 ────────────────
function drawCustomUI(ctx, node) {
    if (node.flags.collapsed) return;
    const isEncW = node.widgets.find(w => w.name === "is_encrypted");
    if (!isEncW || !isEncW.value) return;

    const w = node.size[0];
    const h = node.size[1];

    ctx.fillStyle = "#12121c";
    ctx.beginPath();
    if (ctx.roundRect) {
        ctx.roundRect(10, 30, w - 20, h - 45, 6);
    } else {
        ctx.rect(10, 30, w - 20, h - 45);
    }
    ctx.fill();

    // 锁图标
    ctx.fillStyle = "#ffb800";
    ctx.beginPath();
    ctx.rect(w / 2 - 10, 50, 20, 15);
    ctx.fill();
    
    ctx.beginPath();
    ctx.strokeStyle = "#ffb800";
    ctx.lineWidth = 4;
    ctx.arc(w / 2, 50, 8, Math.PI, 0, false);
    ctx.stroke();

    // 文本
    ctx.fillStyle = "#ffb800";
    ctx.font = "bold 14px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("文本已加密", w / 2, h - 30);

    ctx.fillStyle = "#888";
    ctx.font = "12px sans-serif";
    ctx.fillText("右键解锁", w / 2, h - 10);
}

// ── 注册 ComfyUI 扩展 ──────────────────────────────
app.registerExtension({
    name: "NK.AIGC.NodeEncrypt",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_CLASS) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = onNodeCreated?.apply(this, arguments);

            const textW = this.widgets.find(w => w.name === "text");
            const pwdW = this.widgets.find(w => w.name === "password_setting");
            const switchW = this.widgets.find(w => w.name === "password_switch");

            // 设置 UI 标签
            if (textW) {
                textW.label = "文本";
                // 核心修复：直接接管多行文本框高度计算为 100，绝不出现空白
                const origCompute = textW.computeSize;
                textW.computeSize = function(width) {
                    let res = origCompute ? origCompute.apply(this, arguments) : [width, 100];
                    return [res[0], 100];
                };
            }
            if (pwdW) pwdW.label = "设置密码";
            if (switchW) switchW.label = "密码开关";

            // 密码开关回调
            if (switchW) {
                switchW.callback = (value) => {
                    if (value === true) {
                        const pwd = (pwdW.value || "").trim();
                        if (pwd === ADMIN_PASSWORD || USER_PASSWORD_REGEX.test(pwd)) {
                            this.widgets.find(w => w.name === "encrypted_text").value = textW.value;
                            this.widgets.find(w => w.name === "is_encrypted").value = true;
                            applyUI(this);
                        } else {
                            alert("联系创作者：南光AIGC");
                            switchW.value = false;
                            this.setDirtyCanvas(true, true);
                        }
                    }
                };
            }

            // 延迟应用 UI 和强制打码
            setTimeout(() => {
                applyUI(this);
                if (pwdW && pwdW.inputEl) {
                    pwdW.inputEl.type = "password";
                    pwdW.inputEl.placeholder = "*******";
                }
            }, 50);

            return r;
        };

        const onDrawForeground = nodeType.prototype.onDrawForeground;
        nodeType.prototype.onDrawForeground = function (ctx) {
            onDrawForeground?.apply(this, arguments);
            try {
                const pwdW = this.widgets.find(w => w.name === "password_setting");
                if (pwdW && pwdW.inputEl && pwdW.inputEl.type !== "password") {
                    pwdW.inputEl.type = "password";
                    pwdW.inputEl.placeholder = "*******";
                }
                drawCustomUI(ctx, this);
            } catch (e) {}
        };

        // ── 注入右键菜单 (兼容新版 & 旧版) ──
        const triggerUnlock = async (node) => {
            const pwd = await showPasswordModal();
            if (pwd === null) return; 
            const trimmed = pwd.trim();
            
            if (trimmed === ADMIN_PASSWORD || USER_PASSWORD_REGEX.test(trimmed)) {
                alert("解锁成功\n文本已解密，您可以查看和编辑内容。");
                const textW = node.widgets.find(w => w.name === "text");
                const encW = node.widgets.find(w => w.name === "encrypted_text");
                const pwdW = node.widgets.find(w => w.name === "password_setting");
                const switchW = node.widgets.find(w => w.name === "password_switch");
                const isEncW = node.widgets.find(w => w.name === "is_encrypted");
                
                textW.value = encW.value;
                isEncW.value = false;
                pwdW.value = ""; 
                switchW.value = false;
                applyUI(node);
            } else {
                alert("联系创作者：南光AIGC");
            }
        };

        const originalGetExtraMenuOptions = nodeType.prototype.getExtraMenuOptions;
        nodeType.prototype.getExtraMenuOptions = function (canvas, options) {
            let result = originalGetExtraMenuOptions ? originalGetExtraMenuOptions.apply(this, arguments) : undefined;
            let menuOptions = options || result || [];
            if (!Array.isArray(menuOptions)) menuOptions = [];

            const isEncW = this.widgets?.find(w => w.name === "is_encrypted");
            if (isEncW && isEncW.value) {
                menuOptions.push({
                    content: "🦆 南光AI文本加密 (解锁)",
                    callback: () => { triggerUnlock(this); }
                });
            }
            return menuOptions;
        };

        const originalGetNodeMenuItems = nodeType.prototype.getNodeMenuItems;
        if (originalGetNodeMenuItems) {
            nodeType.prototype.getNodeMenuItems = function (node) {
                const items = originalGetNodeMenuItems.apply(this, arguments) || [];
                const isEncW = this.widgets?.find(w => w.name === "is_encrypted");
                if (isEncW && isEncW.value) {
                    items.push({
                        content: "🦆 南光AI文本加密 (解锁)",
                        callback: () => { triggerUnlock(this); }
                    });
                }
                return items;
            };
        }
    },
});