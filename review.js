
(function(){
"use strict";
const KEY = __KEY__;
const UIKEY = KEY + ":ui";
const META = __META__;
const STATUS = {ok:"通过",minor:"小修",revise:"需修改",question:"存疑",logic:"逻辑/证据",trans:"译文有误"};
const FIELD = {en:META.languages.source,table:"表格",sum:META.languages.target+" 大意",strict:META.languages.target+" 严格翻译"};
const FORDER = {en:0,table:0,sum:1,strict:2};
const $ = (s, r) => (r || document).querySelector(s);
const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const trunc = (s, n) => { s = String(s || "").replace(/\s+/g, " ").trim(); return s.length > n ? s.slice(0, n - 1) + "…" : s; };
const now = () => new Date().toISOString();

function readJSON(k){ try { return JSON.parse(localStorage.getItem(k) || "null"); } catch (e) { return null; } }
function writeJSON(k, v){ try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch (e) { return false; } }

let state = readJSON(KEY);
if (!state || typeof state !== "object" || !state.blocks) state = {version: 1, blocks: {}};
const ui = readJSON(UIKEY) || {};
const saveUi = () => writeJSON(UIKEY, ui);

const rows = $$(".row");
const rowById = new Map(rows.map(r => [r.id, r]));
const rowText = r => {
  const t = r.querySelector('[data-field="table"]');
  if (t) return $$("tr", t).map(tr => $$("th,td", tr).map(c => c.textContent.trim()).join(" | ")).join(" / ");
  const c = r.querySelector('[data-field="en"]');
  return c ? c.textContent.replace(/\s+/g, " ").trim() : "";
};
const getSt = id => state.blocks[id];
const isEmpty = st => !st || (!st.status && !(st.note || "").trim() && !(st.hls || []).length);
function ensureSt(id){
  let st = state.blocks[id];
  if (!st) { const r = rowById.get(id); st = state.blocks[id] = {status: "", note: "", hls: [], doc: r.dataset.doc, label: r.dataset.label, snip: rowText(r).slice(0, 80)}; }
  if (!st.hls) st.hls = [];
  return st;
}
function prune(id){ if (isEmpty(state.blocks[id])) delete state.blocks[id]; }

// Marks are keyed by block id; if a rebuilt page shifted the ids, re-attach them by the stored opening text.
function remap(){
  const kept = {}, lost = [];
  Object.entries(state.blocks).forEach(([id, st]) => {
    const r = rowById.get(id);
    if (r && (!st.snip || rowText(r).startsWith(st.snip))) { kept[id] = st; return; }
    const hits = st.snip ? rows.filter(x => x.dataset.doc === st.doc && rowText(x).startsWith(st.snip)) : [];
    const hit = hits.length === 1 ? hits[0] : null;
    if (hit && !kept[hit.id]) kept[hit.id] = st; else lost.push(Object.assign({id: id}, st));
  });
  state.blocks = kept;
  if (lost.length) state.orphans = (state.orphans || []).concat(lost);
}

let saveTimer = null;
function save(immediate){
  clearTimeout(saveTimer);
  const run = () => { state.savedAt = now(); setSaved(writeJSON(KEY, state)); };
  if (immediate) run(); else saveTimer = setTimeout(run, 350);
}
function setSaved(ok){
  const el = $("#saved");
  if (ok) { el.textContent = "已自动保存 " + new Date().toLocaleTimeString("zh-CN", {hour: "2-digit", minute: "2-digit"}); el.className = "saved"; }
  else { el.textContent = "⚠ 浏览器未能保存，请及时导出"; el.className = "saved warn"; }
}
let toastTimer = null;
function toast(msg){ const t = $("#toast"); t.textContent = msg; t.hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, 2600); }
function autosize(t){ t.style.height = "auto"; t.style.height = Math.min(t.scrollHeight + 2, 460) + "px"; }

// ---------- highlights
function clearMarks(row){
  $$("mark.hl", row).forEach(m => { const p = m.parentNode; while (m.firstChild) p.insertBefore(m.firstChild, m); p.removeChild(m); p.normalize(); });
}
function wrapRange(container, start, end, hid){
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  let pos = 0; const targets = [];
  while (walker.nextNode()) {
    const n = walker.currentNode, len = n.data.length;
    const s = Math.max(start, pos), e = Math.min(end, pos + len);
    if (s < e) targets.push([n, s - pos, e - pos]);
    pos += len;
  }
  targets.forEach(([n, s, e]) => {
    let node = n;
    if (s > 0) node = node.splitText(s);
    if (e - s < node.data.length) node.splitText(e - s);
    const m = document.createElement("mark"); m.className = "hl"; m.dataset.hl = hid;
    node.parentNode.insertBefore(m, node); m.appendChild(node);
  });
}
function locate(container, h){
  const t = container.textContent;
  if (t.slice(h.start, h.end) === h.text) return [h.start, h.end];
  const i = t.indexOf(h.text);
  return i >= 0 ? [i, i + h.text.length] : null;
}
function renderHls(row, st){
  clearMarks(row);
  const list = $(".hl-list", row);
  if (!list) return;
  list.innerHTML = "";
  const hls = ((st && st.hls) || []).slice().sort((a, b) => (FORDER[a.field] - FORDER[b.field]) || (a.start - b.start));
  hls.forEach(h => {
    const c = row.querySelector('[data-field="' + h.field + '"]');
    const pos = c ? locate(c, h) : null;
    if (pos) { h.start = pos[0]; h.end = pos[1]; wrapRange(c, pos[0], pos[1], h.id); }
    const li = document.createElement("li");
    li.className = "hl-item" + (pos ? "" : " lost"); li.dataset.hl = h.id;
    li.innerHTML = '<button type="button" class="hl-del" title="删除这处标记">×</button><div class="hl-q"><span class="f">' + esc(FIELD[h.field] || "") + '</span><b>' + esc(trunc(h.text, 90)) + '</b>' +
      (pos ? "" : ' <em>（原文已变，未能定位）</em>') + '</div><textarea class="hl-note" rows="1" placeholder="对这处的批注…"></textarea>';
    const ta = li.querySelector(".hl-note"); ta.value = h.note || "";
    list.appendChild(li); autosize(ta);
  });
}
function flash(row, hid){
  const ms = $$('mark.hl[data-hl="' + hid + '"]', row);
  if (!ms.length) return;
  ms[0].scrollIntoView({block: "center", behavior: "smooth"});
  ms.forEach(m => m.classList.add("flash"));
  setTimeout(() => ms.forEach(m => m.classList.remove("flash")), 1400);
}

// ---------- rows
function flags(row){
  const st = getSt(row.id);
  row.dataset.status = (st && st.status) || "";
  row.classList.toggle("marked", !isEmpty(st));
}
function renderRow(row){
  const st = getSt(row.id);
  flags(row);
  $$(".chip", row).forEach(c => c.setAttribute("aria-pressed", String(!!st && c.dataset.s === st.status)));
  const ta = $(".note", row);
  if (ta) { const v = (st && st.note) || ""; if (ta.value !== v) ta.value = v; autosize(ta); }
  const cm = $(".c-mark.compact", row);
  if (cm) cm.classList.toggle("open", !isEmpty(st) || cm.classList.contains("keep-open"));
  renderHls(row, st);
}
function renderAll(){ rows.forEach(renderRow); updateProgress(); updateToc(); applyFilters(); showOrphans(); }

function updateProgress(){
  const parts = Object.keys(META.docs).map(doc => {
    const rs = rows.filter(r => r.dataset.doc === doc && r.dataset.reviewable === "1");
    const done = rs.filter(r => { const st = getSt(r.id); return st && st.status; }).length;
    return META.docs[doc].name + " " + done + "/" + rs.length;
  });
  $("#progress").textContent = "已定状态 " + parts.join(" · ");
}
function updateToc(){
  const counts = {};
  rows.forEach(r => { if (!isEmpty(getSt(r.id))) counts[r.dataset.sec] = (counts[r.dataset.sec] || 0) + 1; });
  $$(".toc a").forEach(a => { $(".cnt", a).textContent = counts[a.dataset.target] || ""; });
}
let tocTimer = null;
const updateTocSoon = () => { clearTimeout(tocTimer); tocTimer = setTimeout(updateToc, 500); };
function applyFilters(){
  const fm = $("#fMarked").checked, ft = $("#fTodo").checked, fc = $("#fChg").checked;
  rows.forEach(r => {
    const st = getSt(r.id);
    const struct = r.dataset.kind === "heading" || r.dataset.kind === "title";
    let hide = false;
    if (!struct && fm && isEmpty(st)) hide = true;
    if (!struct && ft && (r.dataset.reviewable !== "1" || (st && st.status))) hide = true;
    if (!struct && fc && r.dataset.chg === "same") hide = true;
    if (!struct && $("#fStatus").value && (!st || st.status !== $("#fStatus").value)) hide = true;
    r.classList.toggle("hide", hide);
  });
}
function showOrphans(){
  const n = (state.orphans || []).length, el = $("#orphans");
  el.hidden = !n;
  if (n) el.textContent = "有 " + n + " 段旧标记对应不到当前稿件（稿件可能已改动），它们仍保存在浏览器里，并会随导出文件一起写出。";
}

// ---------- events
document.addEventListener("click", e => {
  const chip = e.target.closest(".chip");
  if (chip) {
    const row = chip.closest(".row"), st = ensureSt(row.id);
    st.status = st.status === chip.dataset.s ? "" : chip.dataset.s; st.t = now();
    prune(row.id); renderRow(row); save(true); updateProgress(); updateToc(); applyFilters();
    return;
  }
  const add = e.target.closest(".add-note");
  if (add) { const cm = add.closest(".c-mark"); cm.classList.add("open", "keep-open"); const ta = $(".note", cm); if (ta) ta.focus(); return; }
  const del = e.target.closest(".hl-del");
  if (del) {
    const row = del.closest(".row"), hid = del.closest(".hl-item").dataset.hl, st = getSt(row.id);
    if (st) { st.hls = (st.hls || []).filter(h => h.id !== hid); prune(row.id); }
    renderRow(row); save(true); updateToc(); applyFilters();
    return;
  }
  const q = e.target.closest(".hl-q");
  if (q) { flash(q.closest(".row"), q.closest(".hl-item").dataset.hl); return; }
  const mk = e.target.closest("mark.hl");
  if (mk && window.getSelection().isCollapsed) {
    const row = mk.closest(".row"), ta = row.querySelector('.hl-item[data-hl="' + mk.dataset.hl + '"] .hl-note');
    flash(row, mk.dataset.hl); if (ta) ta.focus({preventScroll: true});
    return;
  }
  const img = e.target.closest(".fig img");
  if (img) { $("#lbImg").src = img.src; $("#lightbox").hidden = false; return; }
  const tocA = e.target.closest(".toc a");
  if (tocA && document.body.classList.contains("toc-open")) document.body.classList.remove("toc-open");
});
document.addEventListener("input", e => {
  const t = e.target;
  if (t.classList.contains("note")) {
    const row = t.closest(".row"), st = ensureSt(row.id);
    st.note = t.value; st.t = now(); autosize(t); prune(row.id); flags(row); save(false); updateTocSoon();
  } else if (t.classList.contains("hl-note")) {
    const row = t.closest(".row"), st = ensureSt(row.id), hid = t.closest(".hl-item").dataset.hl;
    const h = st.hls.find(x => x.id === hid); if (h) { h.note = t.value; h.t = now(); }
    autosize(t); save(false);
  }
});

// selection -> highlight
const pop = $("#selPop");
let pending = null;
function selectionInfo(){
  const sel = window.getSelection();
  if (!sel || sel.isCollapsed || !sel.rangeCount) return null;
  const range = sel.getRangeAt(0);
  const el = n => n && (n.nodeType === 1 ? n : n.parentElement);
  const a = el(range.startContainer) && el(range.startContainer).closest("[data-field]");
  const b = el(range.endContainer) && el(range.endContainer).closest("[data-field]");
  if (!a || a !== b) return null;
  const text = range.toString();
  if (!text.trim()) return null;
  const pre = document.createRange(); pre.setStart(a, 0); pre.setEnd(range.startContainer, range.startOffset);
  const start = pre.toString().length;
  const lead = text.length - text.replace(/^\s+/, "").length, trail = text.length - text.replace(/\s+$/, "").length;
  return {row: a.closest(".row"), field: a.dataset.field, start: start + lead, end: start + text.length - trail, text: text.trim(), rect: range.getBoundingClientRect()};
}
function showPop(){
  pending = selectionInfo();
  if (!pending) { pop.hidden = true; return; }
  pop.hidden = false;
  const r = pending.rect, sx = window.scrollX, sy = window.scrollY;
  let top = sy + r.top - pop.offsetHeight - 8;
  const minTop = sy + $("#topbar").offsetHeight + 6;
  if (top < minTop) top = sy + r.bottom + 8;
  const left = sx + r.left + r.width / 2 - pop.offsetWidth / 2;
  pop.style.top = top + "px";
  pop.style.left = Math.max(sx + 8, Math.min(left, sx + document.documentElement.clientWidth - pop.offsetWidth - 8)) + "px";
}
const inField = t => t && t.closest && t.closest("textarea,input");
document.addEventListener("mouseup", e => { if (!pop.contains(e.target) && !inField(e.target)) setTimeout(showPop, 0); });
document.addEventListener("keyup", e => { if (!inField(e.target) && (e.shiftKey || /^Arrow/.test(e.key))) showPop(); });
pop.addEventListener("mousedown", e => e.preventDefault());
$("#popMark").addEventListener("click", () => {
  if (!pending) return;
  const p = pending, st = ensureSt(p.row.id);
  const h = {id: "h" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6), field: p.field, start: p.start, end: p.end, text: p.text, note: "", t: now()};
  st.hls.push(h);
  window.getSelection().removeAllRanges(); pop.hidden = true; pending = null;
  renderRow(p.row); save(true); updateToc(); applyFilters();
  const ta = p.row.querySelector('.hl-item[data-hl="' + h.id + '"] .hl-note');
  if (ta) ta.focus({preventScroll: true});
});
document.addEventListener("keydown", e => { if (e.key === "Escape") { pop.hidden = true; $("#lightbox").hidden = true; document.body.classList.remove("toc-open"); } });
$("#lightbox").addEventListener("click", () => { $("#lightbox").hidden = true; });

// ---------- documents, view and filters
const scrollPos = ui.scroll || {};
function showDoc(doc, restore){
  const cur = ui.doc;
  if (cur && cur !== doc) scrollPos[cur] = window.scrollY;
  $$(".doc").forEach(d => { d.hidden = d.dataset.doc !== doc; });
  $$(".toc-doc").forEach(d => { d.hidden = d.dataset.doc !== doc; });
  $$("#docTabs button").forEach(b => b.classList.toggle("on", b.dataset.doc === doc));
  ui.doc = doc; ui.scroll = scrollPos; saveUi();
  if (restore !== false) window.scrollTo(0, scrollPos[doc] || 0);
}
function setView(v){
  document.body.dataset.view = v;
  $$("#viewSeg button").forEach(b => b.classList.toggle("on", b.dataset.view === v));
  ui.view = v; saveUi();
}
$$("#docTabs button").forEach(b => b.addEventListener("click", () => showDoc(b.dataset.doc)));
$$("#viewSeg button").forEach(b => b.addEventListener("click", () => setView(b.dataset.view)));
$("#fStatus").addEventListener("change", applyFilters);
$("#fMarked").addEventListener("change", applyFilters);
$("#fTodo").addEventListener("change", applyFilters);
$("#fChg").addEventListener("change", applyFilters);
$("#fOpen").addEventListener("change", () => { $$("details.chg").forEach(d => { d.open = $("#fOpen").checked; }); });
$("#tocToggle").addEventListener("click", () => document.body.classList.toggle("toc-open"));
$("#helpClose").addEventListener("click", () => { $("#help").hidden = true; ui.helpHidden = true; saveUi(); });
$("#helpShow").addEventListener("click", () => { $("#help").hidden = false; ui.helpHidden = false; saveUi(); window.scrollTo(0, 0); });
let scrollTimer = null;
window.addEventListener("scroll", () => { clearTimeout(scrollTimer); scrollTimer = setTimeout(() => { scrollPos[ui.doc] = window.scrollY; ui.scroll = scrollPos; saveUi(); }, 400); }, {passive: true});

// scroll spy for the contents list
const tocLinks = new Map($$(".toc a").map(a => [a.dataset.target, a]));
const spy = new IntersectionObserver(entries => {
  entries.forEach(en => {
    if (!en.isIntersecting) return;
    const a = tocLinks.get(en.target.dataset.sec);
    if (!a) return;
    $$(".toc a.active").forEach(x => x.classList.remove("active"));
    a.classList.add("active");
  });
}, {rootMargin: "-120px 0px -65% 0px"});
rows.forEach(r => spy.observe(r));

// ---------- export and import
function collect(){
  const marks = [];
  rows.forEach(r => {
    const st = getSt(r.id);
    if (isEmpty(st)) return;
    const sum = r.querySelector('[data-field="sum"]');
    marks.push({
      id: r.id, doc: r.dataset.doc, docName: META.docs[r.dataset.doc].name, label: r.dataset.label,
      page: r.dataset.page ? Number(r.dataset.page) : null, kind: r.dataset.kind,
      status: st.status || "", statusLabel: STATUS[st.status] || "", note: st.note || "",
      highlights: (st.hls || []).map(h => ({field: h.field, fieldLabel: FIELD[h.field] || h.field, text: h.text, note: h.note || ""})),
      source: rowText(r), summary: sum ? sum.textContent.trim() : ""
    });
  });
  return marks;
}
function stamp(){ const d = new Date(), p = n => String(n).padStart(2, "0"); return "" + d.getFullYear() + p(d.getMonth() + 1) + p(d.getDate()) + "-" + p(d.getHours()) + p(d.getMinutes()); }
function download(name, text, mime){
  const blob = new Blob([text], {type: mime + ";charset=utf-8"});
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name;
  document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  toast("已下载 " + name + "（在浏览器的下载文件夹）");
}
async function saveFile(name, text, mime){
  if (window.showSaveFilePicker) {
    let h = null;
    try {
      const ext = name.slice(name.lastIndexOf("."));
      h = await window.showSaveFilePicker({suggestedName: name, types: [{description: ext === ".json" ? "JSON" : "Markdown", accept: {[mime]: [ext]}}]});
    } catch (err) {
      if (err && err.name === "AbortError") return;  // the reader closed the dialog
      h = null;
    }
    if (h) {
      try {
        const w = await h.createWritable(); await w.write(text); await w.close();
        toast("已保存 " + h.name); return;
      } catch (err) {
        // writing to the chosen place failed: say so and fall back to an ordinary download
        alert("没能写入所选位置（" + ((err && err.name) || "未知错误") + "），改为下载到浏览器的下载文件夹，请从那里移到 review_marks。");
      }
    }
  }
  download(name, text, mime);
}
function exportPayload(){
  const marks = collect(), counts = {};
  marks.forEach(m => { if (m.status) counts[m.status] = (counts[m.status] || 0) + 1; });
  return {format: "bilingual-review-marks", version: 1, storageKey: KEY, page: META.title, exportedAt: now(), sources: META.sources,
    suggestedFolder: META.suggestedFolder, counts: counts, marks: marks, orphans: state.orphans || [], state: state};
}
function toMarkdown(p){
  const L = [], s = META.sources;
  L.push("# " + META.title + " 人工审阅批注", "");
  L.push("- 导出时间：" + new Date().toLocaleString("zh-CN"));
  Object.entries(s).forEach(([key, value]) => L.push("- " + META.docs[key].name + ": " + value.docxName));
  const cs = Object.keys(STATUS).filter(k => p.counts[k]).map(k => STATUS[k] + " " + p.counts[k]).join("，");
  L.push("- 共标记 " + p.marks.length + " 处" + (cs ? "；" + cs : ""), "");
  Object.keys(META.docs).forEach(doc => {
    const ms = p.marks.filter(m => m.doc === doc);
    if (!ms.length) return;
    L.push("## " + META.docs[doc].name, "");
    ms.forEach(m => {
      L.push("### " + m.label + (m.page ? " · p." + m.page : "") + (m.statusLabel ? " ·【" + m.statusLabel + "】" : "") + " · " + m.id, "");
      if (m.source) L.push("> " + trunc(m.source, 260), "");
      if (m.note.trim()) L.push("批注：" + m.note.trim().replace(/\n+/g, "\n  "), "");
      m.highlights.forEach(h => L.push("- " + h.fieldLabel + "「" + trunc(h.text, 140) + "」" + (h.note.trim() ? "：" + h.note.trim().replace(/\n+/g, " ") : "")));
      if (m.highlights.length) L.push("");
    });
  });
  if (p.orphans.length) {
    L.push("## 对应不到当前稿件的旧标记", "");
    p.orphans.forEach(o => L.push("- " + (o.label || o.id) + "：" + (STATUS[o.status] || "") + " " + trunc(o.note || "", 200)));
  }
  const encoded = btoa(Array.from(new TextEncoder().encode(JSON.stringify(p)), b => String.fromCharCode(b)).join(""));
  L.push("", "<!-- bilingual-review-state:" + encoded + " -->");
  return L.join("\n") + "\n";
}
$("#expMd").addEventListener("click", () => saveFile("review_marks_" + stamp() + ".md", toMarkdown(exportPayload()), "text/markdown"));
$("#expJson").addEventListener("click", () => saveFile("review_marks_" + stamp() + ".json", JSON.stringify(exportPayload(), null, 2), "application/json"));
$("#impFile").addEventListener("change", e => {
  const f = e.target.files[0];
  if (!f) return;
  const rd = new FileReader();
  rd.onload = () => {
    try {
      const marker = String(rd.result).match(/<!-- bilingual-review-state:([A-Za-z0-9+/=]+) -->/);
      const data = JSON.parse(marker ? new TextDecoder().decode(Uint8Array.from(atob(marker[1]), c => c.charCodeAt(0))) : rd.result);
      if (data.format !== "bilingual-review-marks" || data.version !== 1) throw new Error("不支持的批注格式或版本");
      if (data.storageKey !== KEY) throw new Error("批注属于另一份审阅配置，存储键不匹配");
      const inc = data && data.state && data.state.blocks ? data.state.blocks : (data && data.blocks);
      if (!inc || typeof inc !== "object") throw new Error("文件里没有找到标记数据");
      if (Array.isArray(inc)) throw new Error("标记数据必须是对象");
      for (const [id, st] of Object.entries(inc)) {
        if (!/^[MS]-[0-9]+$/.test(id) || !st || typeof st !== "object" ||
            typeof st.note !== "string" || typeof st.snip !== "string" ||
            (st.status !== "" && !Object.hasOwn(STATUS, st.status)) || !Array.isArray(st.hls)) throw new Error("无效段落标记");
        for (const h of st.hls) if (!h || !/^[A-Za-z0-9_-]+$/.test(h.id) ||
            !Object.hasOwn(FIELD, h.field) || typeof h.text !== "string" || typeof h.note !== "string" ||
            !Number.isInteger(h.start) || !Number.isInteger(h.end) || h.start < 0 || h.end < h.start) throw new Error("无效高亮标记");
      }
      if (data.state.orphans && (!Array.isArray(data.state.orphans) || data.state.orphans.some(o => !o || typeof o !== "object" || typeof o.note !== "string"))) throw new Error("无效旧标记");
      const n = Object.keys(inc).length;
      if (!confirm("导入 " + n + " 段标记，并与当前标记合并（同一段以导入文件为准）？")) return;
      Object.assign(state.blocks, inc);
      if (data.state && data.state.orphans) state.orphans = (state.orphans || []).concat(data.state.orphans);
      remap(); save(true); renderAll(); toast("已导入 " + n + " 段标记");
    } catch (err) { alert("导入失败：" + err.message); }
  };
  rd.readAsText(f, "utf-8"); e.target.value = "";
});
$("#clearAll").addEventListener("click", () => {
  const n = Object.keys(state.blocks).length + (state.orphans || []).length;
  if (!n) { toast("当前没有标记"); return; }
  if (!confirm("清空本浏览器里的全部 " + n + " 段标记？清空前会先下载一份 JSON 备份。")) return;
  download("review_marks_backup_" + stamp() + ".json", JSON.stringify(exportPayload(), null, 2), "application/json");
  state = {version: 1, blocks: {}}; save(true); renderAll();
});

window.addEventListener("pagehide", () => save(true));

// ---------- start
function setTopbarHeight(){ document.documentElement.style.setProperty("--topbar-h", $("#topbar").offsetHeight + "px"); }
window.addEventListener("resize", setTopbarHeight);
setTopbarHeight();
if (ui.helpHidden) $("#help").hidden = true;
const rev = $("#rev");
if (rev) { if (ui.revClosed) rev.open = false; rev.addEventListener("toggle", () => { ui.revClosed = !rev.open; saveUi(); }); }
remap(); renderAll(); setView(ui.view || "both"); showDoc(ui.doc || "main", true);
setSaved(writeJSON(KEY, state));
})();
