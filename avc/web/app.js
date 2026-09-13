const app = document.getElementById("app");

const state = {
  view: "home",
  projects: [],
  project: null,
  records: [],
  sessions: [],
  status: null,
  session: null,
  record: null,
  diff: null,
  tab: "now",
  compareFrom: "",
  compareTo: "working",
  error: "",
  modal: null,
  theme: {
    editing: false,
    selected: "bg",
    draft: { bg: "#f3ead8", btn: "#b23a2f", dialog: "#fff8ec", text: "#2a2118" },
    saved: { bg: "#f3ead8", btn: "#b23a2f", dialog: "#fff8ec", text: "#2a2118" },
  },
  platform: { os: "mac", path_example: "/Users/你/Desktop/我的小說", agents: [
    { id: "cursor", label: "Cursor" },
    { id: "claude", label: "Claude" },
    { id: "codex", label: "Codex" },
  ] },
};

const AGENT_HINT = {
  cursor: "Cursor 聊天",
  claude: "Claude Code",
  codex: "Codex",
};

const DEFAULT_THEME = { bg: "#f3ead8", btn: "#b23a2f", dialog: "#fff8ec", text: "#2a2118" };
const THEME_LABELS = { bg: "背景", btn: "按鈕", dialog: "對話框", text: "文字" };

function normalizeHex(value) {
  const raw = String(value || "").trim();
  const m = raw.match(/^#?([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/);
  if (!m) return "";
  let hex = m[1];
  if (hex.length === 3) hex = hex.split("").map((ch) => ch + ch).join("");
  return "#" + hex.toLowerCase();
}

function mixHex(a, b, t) {
  const pa = normalizeHex(a).slice(1);
  const pb = normalizeHex(b).slice(1);
  if (!pa || !pb) return a;
  const n = (hex, i) => parseInt(hex.slice(i, i + 2), 16);
  const ch = (i) => Math.round(n(pa, i) * (1 - t) + n(pb, i) * t);
  const to = (n) => n.toString(16).padStart(2, "0");
  return "#" + to(ch(0)) + to(ch(2)) + to(ch(4));
}

function applyTheme(colors) {
  const t = { ...DEFAULT_THEME, ...(colors || {}) };
  const root = document.documentElement;
  root.style.setProperty("--paper", t.bg);
  root.style.setProperty("--paper-2", mixHex(t.bg, t.text, 0.08));
  root.style.setProperty("--card", t.dialog);
  root.style.setProperty("--ink", t.text);
  root.style.setProperty("--muted", mixHex(t.text, t.bg, 0.38));
  root.style.setProperty("--line", mixHex(t.text, t.dialog, 0.78));
  root.style.setProperty("--accent", t.btn);
  root.style.setProperty("--danger", t.btn);
}

function themePartFromTarget(el) {
  if (!el || !el.closest) return "bg";
  if (el.closest(".theme-dock")) return null;
  if (el.closest(".btn, button.tab, .agent-pick")) return "btn";
  if (el.closest(".modal, .card, .t-item, .banner, .msg, .change, .seal")) return "dialog";
  if (el.closest("h1, h2, h3, h4, p, .meta, .label, .empty, .brand")) return "text";
  return "bg";
}

function startThemeEdit() {
  state.theme.editing = true;
  state.theme.draft = { ...state.theme.saved };
  state.theme.selected = "bg";
  document.body.classList.add("theme-picking");
  applyTheme(state.theme.draft);
  render();
}

function endThemeEdit(restoreSaved) {
  state.theme.editing = false;
  document.body.classList.remove("theme-picking");
  if (restoreSaved) {
    state.theme.draft = { ...state.theme.saved };
    applyTheme(state.theme.saved);
  }
  render();
}

function setDraftColor(hex) {
  const n = normalizeHex(hex);
  if (!n) return false;
  state.theme.draft[state.theme.selected] = n;
  applyTheme(state.theme.draft);
  const hexField = document.querySelector(".theme-dock .theme-hex");
  const swatch = document.querySelector(".theme-dock .theme-swatch");
  if (hexField && document.activeElement !== hexField) hexField.value = n;
  if (swatch) swatch.value = n;
  return true;
}

function themeDock() {
  const key = state.theme.selected;
  const value = state.theme.draft[key] || DEFAULT_THEME[key];
  const swatch = h("input", { class: "theme-swatch", type: "color", value });
  const hex = h("input", { class: "theme-hex", type: "text", value, placeholder: "#b23a2f", spellcheck: "false" });
  swatch.addEventListener("input", () => setDraftColor(swatch.value));
  hex.addEventListener("input", () => {
    const n = normalizeHex(hex.value);
    if (n) setDraftColor(n);
  });
  hex.addEventListener("change", () => {
    if (!setDraftColor(hex.value)) hex.value = state.theme.draft[key];
  });
  return h("div", { class: "theme-dock" },
    h("h3", {}, "修改配色"),
    pSafe("點畫面中的背景、按鈕、對話框或文字。可用本機調色盤，也可以直接填色碼。"),
    h("div", { class: "theme-parts" },
      ...Object.keys(THEME_LABELS).map((id) => h("button", {
        type: "button",
        class: "theme-part" + (key === id ? " on" : ""),
        onClick: () => { state.theme.selected = id; render(); },
      }, THEME_LABELS[id])),
    ),
    h("div", { class: "theme-color-row" },
      h("span", { class: "meta" }, "正在改：" + THEME_LABELS[key]),
      swatch,
      hex,
    ),
    h("div", { class: "row" },
      h("button", { class: "btn primary", onClick: async () => {
        const data = await api("/api/theme", {
          method: "POST",
          body: JSON.stringify({ colors: state.theme.draft }),
        });
        state.theme.saved = { ...DEFAULT_THEME, ...data.colors };
        state.theme.draft = { ...state.theme.saved };
        applyTheme(state.theme.saved);
        alert("配色已記住，下次開啟會用這組顏色。");
      } }, "儲存"),
      h("button", { class: "btn", onClick: async () => {
        const data = await api("/api/theme", {
          method: "POST",
          body: JSON.stringify({ reset: true }),
        });
        state.theme.saved = { ...DEFAULT_THEME, ...data.colors };
        state.theme.draft = { ...state.theme.saved };
        applyTheme(state.theme.saved);
        render();
      } }, "回到預設"),
      h("button", { class: "btn ghost", onClick: () => endThemeEdit(true) }, "結束"),
    ),
  );
}

document.addEventListener("click", (e) => {
  if (!state.theme.editing) return;
  if (e.target.closest && e.target.closest(".theme-dock")) return;
  const part = themePartFromTarget(e.target);
  if (!part) return;
  e.preventDefault();
  e.stopPropagation();
  if (state.theme.selected === part) return;
  state.theme.selected = part;
  render();
}, true);

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "操作失敗");
  return data;
}

function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "class") el.className = v;
    else if (k === "html") el.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (v === false || v == null) continue;
    else el.setAttribute(k, v);
  }
  for (const child of children.flat()) {
    if (child == null || child === false) continue;
    el.append(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return el;
}

function fmtTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("zh-Hant", { hour12: false });
}

function changeTag(kind) {
  if (kind === "added") return h("span", { class: "chip tag-add" }, "新增");
  if (kind === "removed") return h("span", { class: "chip tag-del" }, "刪除");
  return h("span", { class: "chip tag-mod" }, "修改");
}

function renderDiff(text) {
  const pre = h("div", { class: "diff" });
  for (const line of (text || "").split("\n")) {
    const div = h("div", {}, line || " ");
    if (line.startsWith("+") && !line.startsWith("+++")) div.className = "add";
    if (line.startsWith("-") && !line.startsWith("---")) div.className = "del";
    pre.append(div);
  }
  return pre;
}

function modalSave() {
  const label = h("input", { type: "text", placeholder: "例如：藍色封面、完成第一章" });
  const note = h("textarea", { placeholder: "這次改了什麼、為什麼要記住" });
  return h("div", { class: "modal-bg", onClick: (e) => e.target.classList.contains("modal-bg") && closeModal() },
    h("div", { class: "modal" },
      h("h2", {}, "幫這次改動做一個標籤"),
      h("p", { class: "meta" }, "像在相簿寫說明一樣。之後就能回來對照，或整份切換回去。"),
      h("label", { class: "field" }, h("span", {}, "標籤"), label),
      h("label", { class: "field" }, h("span", {}, "說明"), note),
      h("div", { class: "row" },
        h("button", { class: "btn primary", onClick: async () => {
          if (!label.value.trim()) return alert("請寫一個標籤名稱");
          await api(`/api/projects/${state.project.id}/records`, {
            method: "POST",
            body: JSON.stringify({ label: label.value.trim(), note: note.value }),
          });
          closeModal();
          await loadProject(state.project.id);
        } }, "記住這次"),
        h("button", { class: "btn ghost", onClick: closeModal }, "取消"),
      ),
    ),
  );
}

function modalRename(rec) {
  const label = h("input", { type: "text", value: rec.label || "" });
  const note = h("textarea", { placeholder: "這次改了什麼、為什麼要記住" });
  note.value = rec.note || "";
  return h("div", { class: "modal-bg", onClick: (e) => e.target.classList.contains("modal-bg") && closeModal() },
    h("div", { class: "modal" },
      h("h2", {}, "改成自己看得懂的標籤"),
      pSafe("只改名稱和說明，資料夾內容不會變。"),
      h("label", { class: "field" }, h("span", {}, "標籤"), label),
      h("label", { class: "field" }, h("span", {}, "說明"), note),
      h("div", { class: "row" },
        h("button", { class: "btn primary", onClick: async () => {
          if (!label.value.trim()) return alert("請寫一個標籤名稱");
          await api(`/api/projects/${state.project.id}/records/${rec.id}/meta`, {
            method: "POST",
            body: JSON.stringify({ label: label.value.trim(), note: note.value }),
          });
          closeModal();
          await loadProject(state.project.id);
        } }, "儲存"),
        h("button", { class: "btn ghost", onClick: closeModal }, "取消"),
      ),
    ),
  );
}

function modalRestore(rec) {
  return h("div", { class: "modal-bg", onClick: (e) => e.target.classList.contains("modal-bg") && closeModal() },
    h("div", { class: "modal" },
      h("h2", {}, "回到「" + rec.label + "」？"),
      h("p", { class: "meta" }, "資料夾會變成那一次記住的樣子。現在還沒記住的改動會消失。"),
      h("div", { class: "row" },
        h("button", { class: "btn primary", onClick: async () => {
          try {
            await api(`/api/projects/${state.project.id}/records/${rec.id}/restore`, {
              method: "POST",
              body: JSON.stringify({ force: false }),
            });
          } catch (err) {
            if (!confirm(err.message + "\n\n要放棄未紀錄的改動，強制切換嗎？")) return;
            await api(`/api/projects/${state.project.id}/records/${rec.id}/restore`, {
              method: "POST",
              body: JSON.stringify({ force: true }),
            });
          }
          closeModal();
          await loadProject(state.project.id);
        } }, "切換過去"),
        h("button", { class: "btn ghost", onClick: closeModal }, "取消"),
      ),
    ),
  );
}

function modalClear() {
  return h("div", { class: "modal-bg", onClick: (e) => e.target.classList.contains("modal-bg") && closeModal() },
    h("div", { class: "modal" },
      h("h2", {}, "清空這個資料夾的所有紀錄？"),
      pSafe("會刪掉全部標籤、對話與歷史快照。資料夾裡的檔案不會動。這一步沒辦法復原。"),
      h("div", { class: "row" },
        h("button", { class: "btn primary", onClick: async () => {
          await api(`/api/projects/${state.project.id}/clear`, {
            method: "POST",
            body: JSON.stringify({ confirm: true }),
          });
          state.session = null;
          state.record = null;
          state.diff = null;
          closeModal();
          await loadProject(state.project.id);
        } }, "確定清空"),
        h("button", { class: "btn ghost", onClick: closeModal }, "取消"),
      ),
    ),
  );
}

function agentPicker(selected, onChange) {
  return h("div", { class: "agent-picks" },
    ...(state.platform.agents || []).map((a) => h("button", {
      type: "button",
      class: "agent-pick" + (selected.value === a.id ? " on" : ""),
      onClick: () => { selected.value = a.id; onChange(); },
    },
      h("strong", {}, a.label),
      h("span", {}, a.id === "cursor" ? "Cursor 編輯器" : a.id === "claude" ? "Claude Code" : "OpenAI Codex"),
    )),
  );
}

function projectAgentControls() {
  const current = state.project.agent || "cursor";
  return h("div", { class: "agent-picks" },
    ...(state.platform.agents || []).map((a) => h("button", {
      type: "button",
      class: "agent-pick" + (current === a.id ? " on" : ""),
      onClick: async () => {
        if (a.id === current) return;
        await api(`/api/projects/${state.project.id}/agent`, {
          method: "POST",
          body: JSON.stringify({ agent: a.id }),
        });
        await loadProject(state.project.id);
      },
    },
      h("strong", {}, a.label),
      h("span", {}, a.id === "cursor" ? "Cursor 編輯器" : a.id === "claude" ? "Claude Code" : "OpenAI Codex"),
    )),
  );
}

function modalNewProject() {
  const chosen = { value: "cursor" };
  const path = h("input", { type: "text", placeholder: "例如 " + (state.platform.path_example || "") });
  const name = h("input", { type: "text", placeholder: "顯示名稱，可留空" });
  const browse = h("button", { type: "button", class: "btn", onClick: async (e) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      const result = await api("/api/browse-folder", { method: "POST", body: "{}" });
      if (result.cancelled || !result.path) return;
      path.value = result.path;
      if (!name.value.trim()) {
        const bits = result.path.replace(/[\\/]+$/, "").split(/[\\/]/);
        name.value = bits[bits.length - 1] || "";
      }
    } catch (err) {
      alert(err.message);
    }
  } }, "瀏覽…");
  const box = h("div", { class: "modal" });
  function paintAgents() {
    const old = box.querySelector(".agent-picks");
    const next = agentPicker(chosen, paintAgents);
    if (old) old.replaceWith(next);
  }
  box.append(
    h("h2", {}, "開始記錄一個資料夾"),
    h("p", { class: "meta" }, "只會在本機運作。用瀏覽選資料夾，不必手打路徑。Mac 與 Windows 都可以。"),
    h("label", { class: "field" },
      h("span", {}, "資料夾完整路徑"),
      h("div", { class: "field-row" }, path, browse),
    ),
    h("label", { class: "field" }, h("span", {}, "名稱"), name),
    h("div", { class: "field" },
      h("span", {}, "這個資料夾主要跟哪一種 AI Agent 協作"),
      agentPicker(chosen, paintAgents),
    ),
    h("div", { class: "row" },
      h("button", { class: "btn primary", onClick: async () => {
        if (!path.value.trim()) return alert("請先用瀏覽選資料夾，或貼上路徑");
        const created = await api("/api/projects", {
          method: "POST",
          body: JSON.stringify({
            root: path.value.trim(),
            name: name.value.trim(),
            agent: chosen.value,
          }),
        });
        closeModal();
        await loadHome();
        await loadProject(created.project.id);
      } }, "開始記錄"),
      h("button", { class: "btn ghost", onClick: closeModal }, "取消"),
    ),
  );
  return h("div", { class: "modal-bg", onClick: (e) => e.target.classList.contains("modal-bg") && closeModal() }, box);
}

function pSafe(text) {
  return h("p", { class: "meta" }, text);
}

function closeModal() {
  state.modal = null;
  render();
}

function changesBlock(summary) {
  if (!summary || !summary.change_count) {
    return h("div", { class: "empty" }, "沒有改動。資料夾跟對照的那一次一樣。");
  }
  const rows = [];
  for (const item of summary.added) rows.push(["added", item.path]);
  for (const item of summary.removed) rows.push(["removed", item.path]);
  for (const item of summary.modified) rows.push(["modified", item.path]);
  return h("div", { class: "change-list" },
    ...rows.map(([kind, path]) => h("div", { class: "change" }, changeTag(kind), h("div", {}, path))),
  );
}

function homeView() {
  return h("div", { class: "wrap" },
    header(false),
    h("p", { class: "banner" }, "這是給不懂程式的人用的版本控制。跟 AI 一起改檔案時，可以記住某一刻、回頭看、互相比對，或整份切回之前。資料存在本機資料庫，不是記事本。"),
    h("div", { class: "grid" },
      ...state.projects.map((p) => h("article", { class: "card" },
        h("h3", {}, p.name),
        h("div", { class: "meta" }, p.root),
        h("div", { class: "row", style: "margin:10px 0" },
          p.info && p.info.active_session_id ? h("span", { class: "chip hot" }, "對話進行中") : h("span", { class: "chip" }, (p.info && p.info.agent_label) || "本機專案"),
        ),
        h("div", { class: "row" },
          h("button", { class: "btn primary", onClick: () => loadProject(p.id) }, "打開"),
          h("button", { class: "btn ghost", onClick: async () => {
            if (!confirm("只是從列表拿掉，不會刪資料夾裡的紀錄。")) return;
            await api(`/api/projects/${p.id}`, { method: "DELETE" });
            await loadHome();
          } }, "從列表移除"),
        ),
      )),
      h("article", { class: "card" },
        h("h3", {}, "新增資料夾"),
        pSafe("用瀏覽選取你正在跟 AI 一起改的資料夾。"),
        h("button", { class: "btn", onClick: () => { state.modal = modalNewProject(); render(); } }, "開始記錄"),
      ),
    ),
  );
}

function header(inProject) {
  return h("header", { class: "masthead" },
    h("div", { class: "brand" },
      h("div", { class: "seal" }, "時"),
      h("div", {},
        h("h1", {}, inProject ? state.project.name : "時光本"),
        h("p", {}, inProject ? state.project.root : "給人與 AI 一起改檔案時用的本地版本控制"),
      ),
    ),
    h("div", { class: "nav-actions" },
      inProject ? h("span", { class: "chip hot" }, "即時更新中") : null,
      inProject ? h("span", { class: "chip" }, state.project.agent_label || "Cursor") : null,
      h("button", { class: "btn", onClick: startThemeEdit }, "修改配色"),
      inProject ? h("button", { class: "btn ghost", onClick: loadHome }, "全部專案") : null,
      inProject ? h("button", { class: "btn primary", onClick: () => { state.modal = modalSave(); render(); } }, "記住這次改動") : null,
    ),
  );
}

function projectView() {
  const tabs = [
    ["now", "現在的改動"],
    ["timeline", "紀錄時間軸"],
    ["talk", "對話"],
    ["compare", "互相比對"],
  ];
  return h("div", { class: "wrap" },
    header(true),
    state.project.active_session_id
      ? h("div", { class: "banner" }, `正在記錄對話 #${state.project.active_session_id}。對話開始前的資料夾已另外拍下，可在「對話」裡看出改了什麼。`)
      : null,
    h("div", { class: "tabs" },
      ...tabs.map(([id, label]) => h("button", {
        class: "tab" + (state.tab === id ? " on" : ""),
        onClick: () => { state.tab = id; render(); },
      }, label)),
    ),
    state.tab === "now" ? nowTab() : null,
    state.tab === "timeline" ? timelineTab() : null,
    state.tab === "talk" ? talkTab() : null,
    state.tab === "compare" ? compareTab() : null,
  );
}

function nowTab() {
  const st = state.status || { added: [], removed: [], modified: [], change_count: 0 };
  const aside = h("aside", { class: "card" },
    h("h3", {}, "對照基準"),
    pSafe(`目前站在「${st.current_label || "起始"}」之後。`),
    h("div", { class: "field" },
      h("span", {}, "這個資料夾使用的 AI Agent（會寫入對應的 SKILL）"),
      projectAgentControls(),
    ),
    state.project.active_session_id ? null : h("div", { class: "row" },
      h("button", { class: "btn primary", onClick: () => { state.modal = modalSave(); render(); } }, "記住這次"),
    ),
    h("div", { class: "row", style: "margin-top:16px" },
      h("button", { class: "btn danger", onClick: () => { state.modal = modalClear(); render(); } }, "清空所有紀錄"),
    ),
  );
  // While an AI 對話 is running, its edits belong to that conversation — they show
  // in「對話」and「紀錄時間軸」, not here. "現在的改動" is only for your own manual edits.
  if (state.project.active_session_id) {
    return h("div", { class: "layout" },
      aside,
      h("section", { class: "card" },
        h("h3", {}, "目前有 AI 對話進行中"),
        pSafe("這些改動屬於目前的 AI 對話，會記在「對話」與「紀錄時間軸」裡。「現在的改動」只顯示你自己手動改的東西。"),
        h("div", { class: "row" },
          h("button", { class: "btn primary", onClick: async () => {
            state.tab = "talk";
            try {
              state.session = await api(`/api/projects/${state.project.id}/sessions/${state.project.active_session_id}`);
            } catch (_) {}
            render();
          } }, "到「對話」看 AI 的改動"),
        ),
      ),
    );
  }
  return h("div", { class: "layout" },
    aside,
    h("section", { class: "card" },
      h("h3", {}, st.change_count ? `有 ${st.change_count} 處尚未記住` : "沒有未紀錄的改動"),
      changesBlock(st),
    ),
  );
}

function timelineTab() {
  const visible = (state.records || []).filter((r) => r.kind !== "session-start");
  return h("div", { class: "layout" },
    h("aside", { class: "timeline" },
      ...visible.map((r) => h("button", {
        class: "t-item"
          + (state.record && state.record.id === r.id ? " selected" : "")
          + (state.project.current_record_id === r.id ? " current" : ""),
        onClick: async () => {
          state.record = await api(`/api/projects/${state.project.id}/records/${r.id}`);
          render();
        },
      },
        h("div", { class: "label" }, r.label),
        h("div", { class: "meta" }, `#${r.id} · ${fmtTime(r.created_at)} · ${r.file_count} 個檔案`),
      )),
    ),
    h("section", { class: "card" }, recordDetail()),
  );
}

function recordDetail() {
  const rec = state.record;
  if (!rec) return h("div", { class: "empty" }, "點左邊一筆紀錄，查看當時有哪些檔案。");
  return h("div", {},
    h("h3", {}, rec.label),
    pSafe(rec.note || "沒有額外說明"),
    h("div", { class: "meta" }, `${fmtTime(rec.created_at)} · 紀錄 #${rec.id}`),
    h("div", { class: "row", style: "margin:14px 0" },
      h("button", { class: "btn green", onClick: () => { state.modal = modalRestore(rec); render(); } }, "切換到這一次"),
      h("button", { class: "btn", onClick: () => { state.modal = modalRename(rec); render(); } }, "改標籤名稱"),
      h("button", { class: "btn", onClick: async () => {
        state.tab = "compare";
        state.compareFrom = String(rec.id);
        state.compareTo = "working";
        state.diff = await api(`/api/projects/${state.project.id}/diff?from=${rec.id}&to=working`);
        render();
      } }, "跟現在比對"),
    ),
    h("h4", {}, "當時的檔案"),
    h("div", { class: "change-list" },
      ...(rec.files || []).map((f) => h("button", {
        class: "change",
        onClick: async () => {
          const file = await api(`/api/projects/${state.project.id}/records/${rec.id}/file?path=${encodeURIComponent(f.path)}`);
          state.modal = h("div", { class: "modal-bg", onClick: (e) => e.target.classList.contains("modal-bg") && closeModal() },
            h("div", { class: "modal", style: "width:min(760px,100%)" },
              h("h2", {}, f.path),
              file.binary ? pSafe("這是非文字檔，已保存在資料庫，可切換回去，但不適合直接顯示。")
                : h("div", { class: "diff" }, file.text || ""),
              h("button", { class: "btn ghost", onClick: closeModal }, "關閉"),
            ),
          );
          render();
        },
      }, h("span", { class: "chip" }, prettySize(f.size)), h("div", {}, f.path))),
    ),
  );
}

function prettySize(n) {
  if (n < 1024) return n + " B";
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
  return (n / 1024 / 1024).toFixed(1) + " MB";
}

function talkTab() {
  const sessions = state.sessions || [];
  return h("div", { class: "layout" },
    h("aside", { class: "card" },
      h("h3", {}, "對話 session"),
      pSafe("跟 AI 一起改檔時會自動開始。這裡只查看紀錄。"),
      state.project.active_session_id ? h("div", { class: "row", style: "margin-bottom:12px" },
        h("button", { class: "btn", onClick: async () => {
          await api(`/api/projects/${state.project.id}/sessions/${state.project.active_session_id}/end`, { method: "POST" });
          await loadProject(state.project.id);
        } }, "結束目前對話"),
      ) : null,
      ...sessions.map((s) => h("button", {
        class: "t-item" + (state.session && state.session.id === s.id ? " current" : ""),
        onClick: async () => {
          state.session = await api(`/api/projects/${state.project.id}/sessions/${s.id}`);
          render();
        },
      },
        h("div", { class: "label" }, s.title),
        h("div", { class: "meta" }, `#${s.id} · ${AGENT_HINT[s.agent] || ""} · ${s.message_count} 則 · ${s.ended_at ? "已結束" : "進行中"}`),
      )),
    ),
    h("section", { class: "card" }, sessionDetail()),
  );
}

function sessionDetail() {
  const s = state.session;
  if (!s) return h("div", { class: "empty" }, "選擇一次對話，查看內容以及對話前後的檔案差異。");
  const roleName = { user: "你", assistant: "AI", system: "系統" };
  const box = h("div", {});
  box.append(
    h("h3", {}, s.title),
    pSafe(s.source ? `來源：${s.source}` : "沒有填來源"),
    pSafe(s.agent ? `AI Agent：${AGENT_HINT[s.agent] || s.agent}` : ""),
    h("div", { class: "row", style: "margin:12px 0" },
      h("button", { class: "btn", onClick: async () => {
        const diff = await api(`/api/projects/${state.project.id}/sessions/${s.id}/changes`);
        state.diff = diff;
        state.tab = "compare";
        state.compareFrom = String(s.baseline_record_id);
        state.compareTo = "working";
        render();
      } }, "看對話前 → 現在的改動"),
    ),
    !s.ended_at && s.change_summary ? h("div", {},
      h("h4", {}, s.change_summary.change_count
        ? `這次對話目前改了 ${s.change_summary.change_count} 個檔`
        : "這次對話目前還沒有檔案改動"),
      changesBlock(s.change_summary),
    ) : null,
    h("h4", {}, "對話內容"),
    ...(s.messages || []).length ? s.messages.map((m) => h("div", { class: "msg " + m.role },
      h("strong", {}, roleName[m.role] || m.role),
      h("div", { class: "meta" }, fmtTime(m.created_at)),
      h("div", {}, m.content),
    )) : [h("div", { class: "empty" }, "還沒有對話內容。跟 AI 一起改檔時，會由 AI 自動寫入。")],
    h("h4", {}, "這次對話留下的標籤"),
    pSafe("可改成自己看得懂的名稱，不會影響當時記住的檔案。"),
    ...(s.records || []).filter((r) => r.kind === "user").length
      ? (s.records || []).filter((r) => r.kind === "user").map((r) => h("div", { class: "change label-item" },
        h("span", { class: "chip" }, `#${r.id}`),
        h("div", {}, r.label),
        h("button", { class: "btn ghost", onClick: () => { state.modal = modalRename(r); render(); } }, "改名稱"),
      ))
      : [h("div", { class: "empty" }, "這次對話還沒留下標籤。")],
  );
  return box;
}

function compareTab() {
  const options = (state.records || []).map((r) => h("option", { value: String(r.id) }, `#${r.id} ${r.label}`));
  const fromSel = h("select", { onChange: (e) => { state.compareFrom = e.target.value; } },
    ...options.map((o) => o.cloneNode(true)),
  );
  const toSel = h("select", { onChange: (e) => { state.compareTo = e.target.value; } },
    h("option", { value: "working" }, "現在資料夾"),
    ...options.map((o) => o.cloneNode(true)),
  );
  fromSel.value = state.compareFrom || (state.records[0] ? String(state.records[0].id) : "");
  toSel.value = state.compareTo || "working";
  state.compareFrom = fromSel.value;
  return h("div", {},
    h("section", { class: "card" },
      h("h3", {}, "選兩次紀錄來對照"),
      h("div", { class: "row" },
        h("label", { class: "field", style: "flex:1" }, h("span", {}, "較早 / 左邊"), fromSel),
        h("label", { class: "field", style: "flex:1" }, h("span", {}, "較新 / 右邊"), toSel),
      ),
      h("button", { class: "btn primary", onClick: async () => {
        state.diff = await api(`/api/projects/${state.project.id}/diff?from=${encodeURIComponent(fromSel.value)}&to=${encodeURIComponent(toSel.value)}`);
        render();
      } }, "開始比對"),
    ),
    state.diff ? h("section", { class: "card", style: "margin-top:16px" },
      h("h3", {}, `${state.diff.from_label} → ${state.diff.to_label}`),
      changesBlock(state.diff.summary),
      ...(state.diff.files || []).map((f) => h("div", { style: "margin-top:16px" },
        h("h4", {}, f.path),
        f.binary ? pSafe("二進位檔有改動，內容不適合用文字顯示。") : renderDiff(f.diff),
      )),
    ) : null,
  );
}

function render() {
  app.innerHTML = "";
  try {
    const view = state.view === "project" && state.project ? projectView() : homeView();
    app.append(view);
    if (state.error) app.prepend(h("div", { class: "wrap error" }, state.error));
    if (state.modal) app.append(state.modal);
    if (state.theme.editing) app.append(themeDock());
  } catch (e) {
    app.textContent = e.message;
  }
}

async function loadHome() {
  state.view = "home";
  state.platform = await api("/api/platform");
  state.projects = await api("/api/projects");
  watch.lastStamp = "";
  watch.lastDbStamp = "";
  watch.lastActive = null;
  watch.homeStamp = homeStamp(state.projects);
  render();
}

async function loadProject(id, opts = {}) {
  const keepTab = state.view === "project" && state.project && state.project.id === id;
  const tab = state.tab;
  const sessionId = state.session && state.session.id;
  const recordId = state.record && state.record.id;
  const y = window.scrollY;
  state.project = await api(`/api/projects/${id}`);
  state.status = await api(`/api/projects/${id}/status`);
  state.records = await api(`/api/projects/${id}/records?all=1`);
  state.sessions = await api(`/api/projects/${id}/sessions`);
  state.view = "project";
  if (keepTab) state.tab = tab;
  if (opts.followSession && state.project.active_session_id) {
    state.tab = "talk";
    try {
      state.session = await api(`/api/projects/${id}/sessions/${state.project.active_session_id}`);
    } catch (_) {
      state.session = null;
    }
  } else if (sessionId) {
    try {
      state.session = await api(`/api/projects/${id}/sessions/${sessionId}`);
    } catch (_) {
      state.session = state.project.active_session_id
        ? await api(`/api/projects/${id}/sessions/${state.project.active_session_id}`).catch(() => null)
        : null;
    }
  } else if (state.project.active_session_id) {
    try {
      state.session = await api(`/api/projects/${id}/sessions/${state.project.active_session_id}`);
    } catch (_) {
      state.session = null;
    }
  }
  const wantRecord = recordId || state.project.current_record_id;
  const current = state.records.find((r) => r.id === wantRecord) || state.records.find((r) => r.id === state.project.current_record_id);
  if (current) {
    state.record = await api(`/api/projects/${id}/records/${current.id}`);
  }
  try {
    const pulse = await api(`/api/projects/${id}/pulse`);
    watch.lastStamp = pulse.stamp;
    watch.lastDbStamp = pulse.db_stamp;
    watch.lastActive = state.project.active_session_id;
  } catch (_) {}
  render();
  if (opts.keepScroll) window.scrollTo(0, y);
}

function homeStamp(projects) {
  return JSON.stringify((projects || []).map((p) => [
    p.id,
    p.info && p.info.active_session_id,
    p.info && p.info.session_count,
    p.info && p.info.record_count,
  ]));
}

function isEditing() {
  if (state.theme.editing) return true;
  if (state.modal) return true;
  const ae = document.activeElement;
  if (!ae) return false;
  const tag = ae.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || ae.isContentEditable;
}

const watch = {
  lastStamp: "",
  lastDbStamp: "",
  lastActive: null,
  homeStamp: "",
  busy: false,
};

async function tickWatch() {
  if (watch.busy || isEditing()) return;
  watch.busy = true;
  try {
    if (state.view === "project" && state.project) {
      const pulse = await api(`/api/projects/${state.project.id}/pulse`);
      if (!watch.lastStamp) {
        watch.lastStamp = pulse.stamp;
        watch.lastDbStamp = pulse.db_stamp;
        watch.lastActive = pulse.active_session_id;
        return;
      }
      if (pulse.stamp === watch.lastStamp) return;
      const dbChanged = pulse.db_stamp !== watch.lastDbStamp;
      const follow = Boolean(pulse.active_session_id && pulse.active_session_id !== watch.lastActive);
      watch.lastStamp = pulse.stamp;
      watch.lastDbStamp = pulse.db_stamp;
      watch.lastActive = pulse.active_session_id;
      if (!dbChanged) {
        const y = window.scrollY;
        state.status = await api(`/api/projects/${state.project.id}/status`);
        // Keep the in-progress 對話's change list fresh as the AI edits files.
        if (state.session && state.session.id === pulse.active_session_id && !state.session.ended_at) {
          try {
            state.session = await api(`/api/projects/${state.project.id}/sessions/${state.session.id}`);
          } catch (_) {}
        }
        render();
        window.scrollTo(0, y);
        return;
      }
      await loadProject(state.project.id, { followSession: follow, keepScroll: true });
      return;
    }
    if (state.view === "home") {
      const projects = await api("/api/projects");
      const next = homeStamp(projects);
      if (watch.homeStamp && next !== watch.homeStamp) {
        state.projects = projects;
        watch.homeStamp = next;
        render();
      } else {
        watch.homeStamp = next;
      }
    }
  } catch (_) {
    // keep the last painted page if the server is briefly busy
  } finally {
    watch.busy = false;
  }
}

setInterval(() => { tickWatch(); }, 1200);
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") tickWatch();
});

async function loadTheme() {
  try {
    const data = await api("/api/theme");
    state.theme.saved = { ...DEFAULT_THEME, ...(data.colors || {}) };
    state.theme.draft = { ...state.theme.saved };
    applyTheme(state.theme.saved);
  } catch (_) {
    applyTheme(DEFAULT_THEME);
  }
}

loadTheme().then(loadHome).catch((e) => {
  state.error = e.message;
  render();
});
