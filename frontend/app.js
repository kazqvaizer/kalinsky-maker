const API = "/api/v1";
let sources = [];
let allAssemblies = [];
let selectedAsmId = null;
let activeTab = "tries";
let allTags = [];

const TAG_COLORS = ["#b58900", "#cb4b16", "#dc322f", "#d33682", "#6c71c4", "#268bd2", "#2aa198", "#859900"];

function randomTagColor() {
    return TAG_COLORS[Math.floor(Math.random() * TAG_COLORS.length)];
}

async function api(method, path, body) {
    const opts = { method, headers: { "Content-Type": "application/json" } };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(API + path, opts);
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || JSON.stringify(err));
    }
    if (res.status === 204) return null;
    return res.json();
}

function fmt(sec) {
    if (sec == null) return "";
    const m = Math.floor(sec / 60);
    const s = (sec % 60).toFixed(1);
    return m > 0 ? `${m}m${s}s` : `${s}s`;
}

function fmtBytes(b) {
    if (b > 1e9) return (b / 1e9).toFixed(1) + "GB";
    if (b > 1e6) return (b / 1e6).toFixed(1) + "MB";
    return (b / 1e3).toFixed(0) + "KB";
}

// Burger menu
function toggleMenu() {
    document.getElementById("burger-menu").classList.toggle("open");
}

document.addEventListener("click", (e) => {
    const menu = document.getElementById("burger-menu");
    if (menu.classList.contains("open") && !menu.contains(e.target) && !e.target.closest(".burger-btn")) {
        menu.classList.remove("open");
    }
    // Close tag assign dropdowns on outside click
    if (!e.target.closest(".tag-assign-dropdown") && !e.target.closest(".tag-assign-btn")) {
        document.querySelectorAll(".tag-assign-dropdown.open").forEach(d => d.classList.remove("open"));
    }
});

// Tags
async function loadTags() {
    try {
        allTags = await api("GET", "/tags");
        renderTags();
    } catch { allTags = []; }
}

function renderTags() {
    const el = document.getElementById("tags-list");
    if (!allTags.length) { el.innerHTML = '<div class="empty" style="padding:4px">No tags</div>'; return; }
    el.innerHTML = allTags.map(t =>
        `<div class="tag-row" data-id="${t.id}">
            <span class="tag-name" style="color:${t.color}" onclick="renameTag(${t.id}, '${t.name.replace(/'/g, "\\'")}')">${t.name}</span>
            <button class="tag-del" onclick="deleteTag(${t.id})">x</button>
        </div>`
    ).join("");
}

async function createTag() {
    const input = document.getElementById("new-tag-input");
    const name = input.value.trim();
    if (!name) return;
    try {
        await api("POST", "/tags", { name, color: randomTagColor() });
        input.value = "";
        await loadTags();
        renderSources();
    } catch (e) { alert(e.message); }
}

async function deleteTag(id) {
    try {
        await api("DELETE", `/tags/${id}`);
        await loadTags();
        await loadSources();
    } catch (e) { alert(e.message); }
}

async function renameTag(id, currentName) {
    const name = prompt("Rename tag:", currentName);
    if (!name || name === currentName) return;
    try {
        await api("PUT", `/tags/${id}`, { name });
        await loadTags();
        await loadSources();
    } catch (e) { alert(e.message); }
}

// Sources
async function reindex() {
    const btn = document.getElementById("reindex-btn");
    btn.textContent = "...";
    try {
        await api("POST", "/sources/reindex");
        await loadSources();
    } catch (e) { alert(e.message); }
    btn.textContent = "Reindex";
}

async function loadSources() {
    try {
        sources = await api("GET", "/sources");
        renderSources();
    } catch (e) {
        document.getElementById("sources-list").innerHTML = `<div class="empty" style="padding:8px">${e.message}</div>`;
    }
}

function renderSources() {
    const el = document.getElementById("sources-list");
    if (!sources.length) { el.innerHTML = '<div class="empty" style="padding:8px">No sources</div>'; return; }
    el.innerHTML = sources.map(s => {
        const stem = s.filename.replace(/\.[^.]+$/, "");
        const thumbUrl = `/media/previews/${encodeURIComponent(stem)}.jpg`;
        const tagChips = (s.tags || []).map(t => `<span class="tag-chip" style="background:${t.color};color:#fff">${t.name}</span>`).join("");
        return `<div class="source-item" data-index="${s.index}" data-filename="${s.filename}" data-duration="${s.duration}">
            <div class="source-info">
                <div class="source-name">${s.index}. ${s.filename}</div>
                <div class="source-meta">${s.resolution} ${fmt(s.duration)} ${fmtBytes(s.file_size)}</div>
                ${tagChips ? `<div class="source-tags">${tagChips}</div>` : ""}
            </div>
            <button class="tag-assign-btn" onclick="event.stopPropagation(); toggleTagAssign(this, ${s.index})" title="Tags">T</button>
            <button class="preview-btn" onclick="event.stopPropagation(); previewSource('${s.filename}')">Play</button>
            <div class="source-thumb"><img src="${thumbUrl}" alt=""></div>
        </div>`;
    }).join("");
    el.querySelectorAll(".source-item").forEach(item => {
        item.addEventListener("click", () => addClipFromSource(item));
        const thumb = item.querySelector(".source-thumb");
        item.addEventListener("mouseenter", (e) => {
            const rect = item.getBoundingClientRect();
            thumb.style.left = rect.right + 4 + "px";
            thumb.style.top = rect.top + "px";
        });
    });
    highlightUsedSources();
}

function toggleTagAssign(btn, index) {
    // Close all existing dropdowns
    document.querySelectorAll(".tag-assign-dropdown").forEach(d => d.remove());

    // Check if we're toggling off
    if (btn._tagDropdownOpen) { btn._tagDropdownOpen = false; return; }

    const src = sources.find(s => s.index === index);
    const srcTagNames = src ? (src.tags || []).map(t => t.name) : [];

    const dd = document.createElement("div");
    dd.className = "tag-assign-dropdown open";
    dd.onclick = (e) => e.stopPropagation();

    dd.innerHTML = allTags.length ? allTags.map(t => {
        const checked = srcTagNames.includes(t.name) ? "checked" : "";
        return `<label class="tag-assign-row"><input type="checkbox" ${checked} onchange="updateSourceTags(${index})" value="${t.id}"> <span style="color:${t.color}">${t.name}</span></label>`;
    }).join("") : '<div class="empty" style="padding:4px;font-size:0.6rem">No tags</div>';

    // Position near the T button
    const rect = btn.getBoundingClientRect();
    dd.style.position = "fixed";
    dd.style.left = rect.left + "px";
    dd.style.top = rect.bottom + 2 + "px";
    document.body.appendChild(dd);

    btn._tagDropdownOpen = true;

    // Auto-hide on mouse leave (with grace period)
    let hideTimer = null;
    const startHide = () => { hideTimer = setTimeout(() => { dd.remove(); btn._tagDropdownOpen = false; }, 150); };
    const cancelHide = () => { clearTimeout(hideTimer); };
    dd.addEventListener("mouseenter", cancelHide);
    dd.addEventListener("mouseleave", startHide);
    btn.addEventListener("mouseenter", cancelHide);
    btn.addEventListener("mouseleave", startHide);

    // Reset flag when dropdown is removed
    const observer = new MutationObserver(() => {
        if (!document.body.contains(dd)) {
            btn._tagDropdownOpen = false;
            clearTimeout(hideTimer);
            observer.disconnect();
        }
    });
    observer.observe(document.body, { childList: true });
}

async function updateSourceTags(index) {
    const dd = document.querySelector(".tag-assign-dropdown.open");
    if (!dd) return;
    const tag_ids = Array.from(dd.querySelectorAll("input:checked")).map(cb => parseInt(cb.value));
    try {
        await api("PUT", `/sources/${index}/tags`, { tag_ids });
        // Reload sources but keep dropdown
        sources = await api("GET", "/sources");
        // Update just the tag chips without full re-render
        const src = sources.find(s => s.index === index);
        if (src) {
            const item = document.querySelector(`.source-item[data-index="${index}"]`);
            if (item) {
                const tagsContainer = item.querySelector(".source-tags");
                const chips = (src.tags || []).map(t => `<span class="tag-chip" style="background:${t.color};color:#fff">${t.name}</span>`).join("");
                if (tagsContainer) {
                    tagsContainer.innerHTML = chips;
                } else if (chips) {
                    const info = item.querySelector(".source-info");
                    info.insertAdjacentHTML("beforeend", `<div class="source-tags">${chips}</div>`);
                }
            }
        }
    } catch (e) { alert(e.message); }
}

function previewSource(filename) {
    window.open("/sources/" + encodeURIComponent(filename), "_blank");
}

// Clips
function addClip(sourceIndex, filename, duration, start, end) {
    const container = document.getElementById("clips-list");
    const pos = container.children.length + 1;
    const div = document.createElement("div");
    div.className = "clip-row";
    div.dataset.source = sourceIndex;
    div.dataset.filename = filename;
    div.dataset.duration = duration;
    const startVal = start != null ? `value="${start}"` : "";
    const endVal = end != null ? `value="${end}"` : "";
    const placeholder = parseFloat(duration).toFixed(1);
    div.innerHTML = `
        <span class="clip-pos">${pos}.</span>
        <span class="clip-filename" title="${filename}"><strong>${sourceIndex}</strong> ${filename}</span>
        <input type="number" class="clip-start" placeholder="0" step="0.1" min="0" max="${duration}" ${startVal}>
        <input type="number" class="clip-end" placeholder="${placeholder}" step="0.1" min="0" max="${duration}" ${endVal}>
        <button type="button" class="move-btn" onclick="moveClip(this, -1)" title="Up">&#9650;</button>
        <button type="button" class="move-btn" onclick="moveClip(this, 1)" title="Down">&#9660;</button>
        <button type="button" class="remove-btn" onclick="removeClip(this)">X</button>
    `;
    container.appendChild(div);
    updateClipsUI();
}

function addClipFromSource(item) {
    addClip(item.dataset.index, item.dataset.filename, item.dataset.duration, 0, item.dataset.duration);
}

function moveClip(btn, direction) {
    const row = btn.closest(".clip-row");
    const container = document.getElementById("clips-list");
    const rows = Array.from(container.children);
    const idx = rows.indexOf(row);
    const target = idx + direction;
    if (target < 0 || target >= rows.length) return;
    if (direction === -1) container.insertBefore(row, rows[target]);
    else container.insertBefore(row, rows[target].nextSibling);
    renumberClips();
}

function removeClip(btn) {
    btn.closest(".clip-row").remove();
    updateClipsUI();
}

function renumberClips() {
    document.querySelectorAll("#clips-list .clip-row").forEach((row, i) => {
        row.querySelector(".clip-pos").textContent = (i + 1) + ".";
    });
}

function updateClipsUI() {
    renumberClips();
    document.getElementById("clips-empty").style.display =
        document.querySelectorAll("#clips-list .clip-row").length > 0 ? "none" : "block";
    highlightUsedSources();
}

function highlightUsedSources() {
    const used = new Set();
    document.querySelectorAll("#clips-list .clip-row").forEach(row => used.add(row.dataset.source));
    document.querySelectorAll("#sources-list .source-item").forEach(item => {
        item.classList.toggle("source-used", used.has(item.dataset.index));
    });
}

function fillFormFromAssembly(asm) {
    document.getElementById("asm-name").value = asm.name || "";
    document.getElementById("asm-preview").checked = asm.preview;
    document.getElementById("clips-list").innerHTML = "";
    for (const c of asm.clips) {
        const src = sources.find(s => s.filename === c.filename);
        const duration = src ? src.duration : c.end;
        const start = c.start > 0 ? c.start : null;
        const end = (c.end < duration) ? c.end : null;
        addClip(src ? src.index : 0, c.filename, duration, start, end);
    }
    updateClipsUI();
}

// Tabs
function switchTab(tab) {
    activeTab = tab;
    document.querySelectorAll(".tab-btn").forEach(b => {
        b.classList.toggle("tab-active", b.dataset.tab === tab);
    });
    renderAssemblies();
}

// Assemblies
async function createAssembly(e) {
    e.preventDefault();
    const rows = document.querySelectorAll("#clips-list .clip-row");
    if (!rows.length) { alert("Add at least one clip"); return; }
    const clips = Array.from(rows).map(row => {
        const clip = { source: parseInt(row.dataset.source) };
        const start = row.querySelector(".clip-start").value;
        const end = row.querySelector(".clip-end").value;
        if (start) clip.start = parseFloat(start);
        if (end) clip.end = parseFloat(end);
        return clip;
    });
    const body = { clips, preview: document.getElementById("asm-preview").checked };
    const name = document.getElementById("asm-name").value.trim();
    if (name) body.name = name;
    try {
        const asm = await api("POST", "/assemblies", body);
        await loadAssemblies();
        selectAssembly(asm.id);
        startPolling();
    } catch (e) { alert(e.message); }
}

async function loadAssemblies() {
    try {
        allAssemblies = await api("GET", "/assemblies");
        renderAssemblies();
        return allAssemblies;
    } catch (e) {
        document.getElementById("assemblies-list").innerHTML = `<div class="empty" style="padding:8px">${e.message}</div>`;
        return [];
    }
}

function renderAssemblies() {
    const el = document.getElementById("assemblies-list");
    const filtered = allAssemblies.filter(a => activeTab === "tries" ? a.preview : !a.preview);
    const show = filtered.slice(0, 50);
    if (!show.length) { el.innerHTML = '<div class="empty" style="padding:8px">No assemblies yet</div>'; return; }
    el.innerHTML = show.map(a => {
        const sel = a.id === selectedAsmId ? " asm-selected" : "";
        const clips = a.clips.map(c => `${c.filename} [${c.start.toFixed(1)}–${c.end.toFixed(1)}s]`).join(", ");
        const noteVal = a.note ? a.note.replace(/"/g, "&quot;") : "";
        let error = "";
        if (a.status === "failed" && a.error) {
            error = `<div class="asm-error">${a.error}</div>`;
        }
        const release = a.preview ? "" : " asm-release";
        return `<div class="asm-item${sel}${release}" data-id="${a.id}">
            <div class="asm-header">
                <strong>${a.id}</strong>
                ${a.name ? " — " + a.name : ""}
                <span class="status status-${a.status}">${a.status}</span>
                ${fmt(a.duration)}
            </div>
            <div class="asm-clips">${clips}</div>
            <div class="asm-note">
                <input type="text" value="${noteVal}" placeholder="note..." data-id="${a.id}" onchange="saveNote(this)">
            </div>
            <div class="asm-actions">
                <a class="asm-link" onclick="event.stopPropagation(); fillFormById('${a.id}')">fill form</a>
                <a class="delete-btn" onclick="event.stopPropagation(); deleteAssembly('${a.id}')">delete</a>
            </div>
            ${error}
        </div>`;
    }).join("");
    el.querySelectorAll(".asm-item").forEach(item => {
        item.addEventListener("click", (e) => {
            if (e.target.tagName === "INPUT" || e.target.tagName === "BUTTON") return;
            selectAssembly(item.dataset.id);
        });
    });
}

function selectAssembly(id) {
    selectedAsmId = id;
    document.querySelectorAll(".asm-item").forEach(el => {
        el.classList.toggle("asm-selected", el.dataset.id === id);
    });
    const asm = allAssemblies.find(a => a.id === id);
    renderPlayer(asm);
}

function renderPlayer(asm) {
    const title = document.getElementById("player-title");
    const content = document.getElementById("player-content");
    if (!asm) {
        title.textContent = "Player";
        content.innerHTML = '<div class="empty">Select an assembly from the feed</div>';
        return;
    }
    title.textContent = asm.id + (asm.name ? " — " + asm.name : "");
    if (asm.status === "processing") {
        content.innerHTML = '<div class="empty">Processing...</div>';
    } else if (asm.status === "failed") {
        content.innerHTML = `<div class="empty">Failed: ${asm.error || "unknown error"}</div>`;
    } else if (asm.output_url) {
        const dlName = (asm.name || asm.id) + ".mp4";
        content.innerHTML = `
            <video controls autoplay src="${asm.output_url}"></video>
            <div class="player-info">
                ${fmt(asm.duration)} &middot; <a href="${asm.output_url}" download="${dlName}" target="_blank">Download</a>
            </div>`;
    } else {
        content.innerHTML = '<div class="empty">No output</div>';
    }
}

function fillFormById(id) {
    const asm = allAssemblies.find(a => a.id === id);
    if (asm) fillFormFromAssembly(asm);
}

async function deleteAssembly(id) {
    const asm = allAssemblies.find(a => a.id === id);
    if (asm && !asm.preview && !confirm(`Delete release ${id}?`)) return;
    try {
        await fetch(API + `/assemblies/${id}`, { method: "DELETE" });
        if (selectedAsmId === id) {
            selectedAsmId = null;
            renderPlayer(null);
        }
        await loadAssemblies();
    } catch (e) { alert(e.message); }
}

let noteTimers = {};
function saveNote(input) {
    const id = input.dataset.id;
    clearTimeout(noteTimers[id]);
    noteTimers[id] = setTimeout(async () => {
        try {
            await api("PATCH", `/assemblies/${id}`, { note: input.value || null });
        } catch { /* ignore */ }
    }, 300);
}

// Polling
let pollTimer = null;
function startPolling() {
    if (pollTimer) return;
    pollTimer = setInterval(async () => {
        const assemblies = await loadAssemblies();
        if (selectedAsmId) {
            const asm = assemblies.find(a => a.id === selectedAsmId);
            if (asm) renderPlayer(asm);
        }
        if (!assemblies.some(a => a.status === "processing")) {
            clearInterval(pollTimer);
            pollTimer = null;
        }
    }, 2000);
}

// Init
document.getElementById("reindex-btn").addEventListener("click", reindex);
document.getElementById("assembly-form").addEventListener("submit", createAssembly);
document.getElementById("new-tag-input").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); createTag(); } });
loadTags();
loadSources();
loadAssemblies().then(a => { if (a.some(x => x.status === "processing")) startPolling(); });
