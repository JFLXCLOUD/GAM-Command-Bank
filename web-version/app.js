'use strict';

/* global CommandCore, CalmingStarfield */
const Core = CommandCore;

const STORAGE_KEY = 'gamCommandBank.v4';
const LEGACY_KEYS = ['gamCommandBank_v3'];
const SETTINGS_KEY = 'gamCommandBank.settings';
const LIBRARY_URLS = ['../commands.json', 'commands.json'];
const CLOUD_SHELL = 'https://shell.cloud.google.com/';
const FILTERS = ['All', 'Favorites', 'Recent', ...Core.CATEGORIES];
const FILTER_ICONS = { Favorites: '★ ', Recent: '⌚ ' };

// Used only when commands.json can't be fetched (e.g. opened from file://).
const FALLBACK_LIBRARY = {
    GAM: [
        { command: 'gam info user <email>', description: 'Users › Show user info' },
        { command: 'gam user <email> suspended on', description: 'Users › Suspend user' },
        { command: 'gam user <email> suspended off', description: 'Users › Unsuspend user' },
        { command: 'gam update user <email> password <new_password> changepassword on', description: 'Users › Reset password (force change)' },
        { command: 'gam print group-members group <group_email>', description: 'Groups › List members' },
        { command: 'gam update group <group_email> add member user <email>', description: 'Groups › Add member' },
        { command: 'gam update group <group_email> remove member user <email>', description: 'Groups › Remove member' },
        { command: 'gam info domain', description: 'Customer › Show domain info' },
    ],
    AD: [
        { command: 'Get-ADUser -Identity <username> -Properties *', description: 'Users › Get user (all properties)' },
        { command: 'Disable-ADAccount -Identity <username>', description: 'Users › Disable account' },
        { command: 'Enable-ADAccount -Identity <username>', description: 'Users › Enable account' },
        { command: 'Unlock-ADAccount -Identity <username>', description: 'Users › Unlock account' },
        { command: 'Add-ADGroupMember -Identity <group> -Members <username>', description: 'Groups › Add member' },
        { command: 'Get-ADGroupMember -Identity <group>', description: 'Groups › List members' },
    ],
    PowerShell: [
        { command: 'Get-Process', description: 'List all running processes' },
        { command: 'Stop-Process -Id <process_id>', description: 'Stop a process by its ID' },
        { command: 'Get-Service -Name <service_name>', description: 'Get a service' },
        { command: 'Restart-Service -Name <service_name>', description: 'Restart a service' },
        { command: 'Test-NetConnection <hostname_or_IP> -Port <port>', description: 'Test a TCP port' },
        { command: '$PSVersionTable.PSVersion', description: 'Show the current PowerShell version' },
    ],
};

// ── small DOM helpers ─────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
function h(tag, props = {}, ...children) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(props)) {
        if (v == null || v === false) continue;
        if (k === 'class') el.className = v;
        else if (k === 'dataset') Object.assign(el.dataset, v);
        else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
        else if (k in el && typeof v !== 'string') el[k] = v;
        else el.setAttribute(k, v === true ? '' : v);
    }
    for (const c of children.flat()) {
        if (c != null && c !== false) el.append(c instanceof Node ? c : String(c));
    }
    return el;
}
const isTyping = el => el && (el.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName));

// localStorage can throw (private mode, quota, disabled storage).
const storage = {
    get(key) { try { return localStorage.getItem(key); } catch { return null; } },
    set(key, value) {
        try { localStorage.setItem(key, value); return true; } catch { return false; }
    },
};

class CommandBankApp {
    constructor() {
        this.commands = [];
        this.settings = Object.assign(
            { theme: null, filter: 'All', recentValues: {} },
            this._readJson(SETTINGS_KEY) || {});
        if (!FILTERS.includes(this.settings.filter)) this.settings.filter = 'All';
        this.filter = this.settings.filter;
        this.query = '';
        this.current = null;
        this.values = {};          // field values, shared across commands by name
        this.visible = [];
        this.lastDeleted = null;
        this._statusTimer = null;
        this._toastTimer = null;
        this.storageOk = true;
    }

    async init() {
        this.applyTheme();
        this.buildChips();
        this.bindEvents();
        await this.loadCommands();
        this.render();
    }

    // ── persistence ──────────────────────────────────────────────────────
    _readJson(key) {
        const raw = storage.get(key);
        if (!raw) return null;
        try { return JSON.parse(raw); } catch { return null; }
    }

    async loadCommands() {
        const saved = this._readJson(STORAGE_KEY);
        if (saved) {
            try {
                this.commands = Core.parseCommands(saved);
                this.setStatus(`Loaded ${this.commands.length} commands.`);
                return;
            } catch { /* fall through to legacy / library */ }
        }
        for (const key of LEGACY_KEYS) {
            const legacy = this._readJson(key);
            if (!legacy) continue;
            try {
                this.commands = Core.parseCommands(legacy);
                // Bring in the full library alongside what the old version stored.
                const lib = await this.fetchLibrary();
                if (lib) Core.merge(this.commands, lib.commands);
                this.save();
                this.setStatus(`Upgraded your saved commands (${this.commands.length} total).`);
                return;
            } catch { /* ignore broken legacy data */ }
        }
        const lib = await this.fetchLibrary();
        this.commands = lib ? lib.commands : Core.parseCommands(FALLBACK_LIBRARY);
        this.save();
        this.setStatus(lib
            ? `Loaded ${this.commands.length} built-in commands.`
            : 'Loaded starter commands. Use ⋯ › Import to load the full commands.json.', 10000);
    }

    async fetchLibrary() {
        if (location.protocol === 'file:') return null;
        for (const url of LIBRARY_URLS) {
            try {
                const res = await fetch(url, { cache: 'no-cache' });
                if (res.ok) return { url, commands: Core.parseCommands(await res.json()) };
            } catch { /* try the next location */ }
        }
        return null;
    }

    save() {
        this.storageOk = storage.set(STORAGE_KEY, JSON.stringify(Core.serialize(this.commands)));
        if (!this.storageOk) {
            this.setStatus('⚠ Could not save — browser storage is unavailable. Export to keep your changes.', 10000);
        }
        this.renderStorageInfo();
    }

    saveSettings() {
        this.settings.filter = this.filter;
        storage.set(SETTINGS_KEY, JSON.stringify(this.settings));
    }

    // ── theme ────────────────────────────────────────────────────────────
    applyTheme() {
        const theme = this.settings.theme ||
            (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
        document.documentElement.setAttribute('data-theme', theme);
        $('themeToggle').textContent = theme === 'dark' ? '☽' : '☀';
    }

    toggleTheme() {
        const now = document.documentElement.getAttribute('data-theme');
        this.settings.theme = now === 'dark' ? 'light' : 'dark';
        this.saveSettings();
        this.applyTheme();
    }

    // ── events ───────────────────────────────────────────────────────────
    bindEvents() {
        const search = $('searchInput');
        search.addEventListener('input', () => {
            this.query = search.value.trim();
            this.renderList({ autoselect: true });
        });
        search.addEventListener('keydown', e => {
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                e.preventDefault();
                this.moveSelection(e.key === 'ArrowDown' ? 1 : -1);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (!this.current && this.visible[0]) this.select(this.visible[0]);
                this.focusFirstField();
            } else if (e.key === 'Escape') {
                search.value = '';
                this.query = '';
                this.renderList();
            }
        });

        const list = $('commandList');
        list.addEventListener('keydown', e => {
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                e.preventDefault();
                this.moveSelection(e.key === 'ArrowDown' ? 1 : -1);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                this.focusFirstField();
            } else if (e.key === 'Delete') {
                e.preventDefault();
                this.deleteCurrent();
            }
        });

        $('newBtn').addEventListener('click', () => this.openEditor(null));
        $('themeToggle').addEventListener('click', () => this.toggleTheme());
        $('favBtn').addEventListener('click', () => this.toggleFavorite());
        $('editBtn').addEventListener('click', () => this.openEditor(this.current));
        $('deleteBtn').addEventListener('click', () => this.deleteCurrent());
        $('copyBtn').addEventListener('click', () => this.copy());
        $('shellBtn').addEventListener('click', () => this.openCloudShell());
        $('resetBtn').addEventListener('click', () => this.resetFields());
        $('backBtn').addEventListener('click', () => {
            document.body.classList.remove('show-detail');
            this.focusListItem();
        });
        $('fields').addEventListener('submit', e => { e.preventDefault(); this.copy(); });

        // menu
        const menu = $('menu'), menuBtn = $('menuBtn');
        const closeMenu = () => { menu.hidden = true; menuBtn.setAttribute('aria-expanded', 'false'); };
        menuBtn.addEventListener('click', e => {
            e.stopPropagation();
            menu.hidden = !menu.hidden;
            menuBtn.setAttribute('aria-expanded', String(!menu.hidden));
            if (!menu.hidden) menu.querySelector('button, a').focus();
        });
        document.addEventListener('click', e => { if (!menu.contains(e.target)) closeMenu(); });
        menu.addEventListener('keydown', e => { if (e.key === 'Escape') { closeMenu(); menuBtn.focus(); } });
        menu.addEventListener('click', e => {
            const action = e.target.closest('[data-action]')?.dataset.action;
            if (!action) return;
            closeMenu();
            ({
                import: () => $('importFile').click(),
                export: () => this.exportCommands(),
                builtins: () => this.mergeLibrary(),
                'clear-history': () => this.clearHistory(),
                'forget-values': () => this.forgetValues(),
                shortcuts: () => $('helpDialog').showModal(),
            })[action]?.();
        });
        $('importFile').addEventListener('change', e => this.importFile(e.target.files[0]));

        // editor dialog
        $('editCategory').append(...Core.CATEGORIES.map(c => h('option', { value: c }, c)));
        $('editCommand').addEventListener('input', () => this.updateEditorHint());
        $('editCommand').addEventListener('keydown', e => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); this.saveEditor(); }
        });
        $('editForm').addEventListener('submit', e => { e.preventDefault(); this.saveEditor(); });
        $('editCancel').addEventListener('click', () => $('editDialog').close());

        $('toastAction').addEventListener('click', () => this._toastHandler?.());

        document.addEventListener('keydown', e => this.onGlobalKey(e));
        window.addEventListener('storage', e => {
            // keep several open tabs in sync
            if (e.key === STORAGE_KEY && e.newValue) {
                try {
                    const cur = this.current && [this.current.category, this.current.command, this.current.description];
                    this.commands = Core.parseCommands(JSON.parse(e.newValue));
                    this.current = cur ? this.commands.find(c =>
                        c.category === cur[0] && c.command === cur[1] && c.description === cur[2]) || null : null;
                    this.render();
                } catch { /* ignore */ }
            }
        });
    }

    onGlobalKey(e) {
        if (document.querySelector('dialog[open]')) return;
        const mod = e.ctrlKey || e.metaKey;
        if (mod && e.key === 'Enter') { e.preventDefault(); this.copy(); return; }
        if (mod && e.key.toLowerCase() === 'k') { e.preventDefault(); this.focusSearch(); return; }
        if (isTyping(e.target)) return;
        if (mod && e.key.toLowerCase() === 'z' && this.lastDeleted) { e.preventDefault(); this.undoDelete(); return; }
        if (mod || e.altKey) return;
        const k = e.key;
        if (k === '/') { e.preventDefault(); this.focusSearch(); }
        else if (k === '?') { $('helpDialog').showModal(); }
        else if (k === 'n' || k === 'N') { e.preventDefault(); this.openEditor(null); }
        else if ((k === 'e' || k === 'E') && this.current) { e.preventDefault(); this.openEditor(this.current); }
        else if ((k === 'f' || k === 'F') && this.current) { this.toggleFavorite(); }
        else if (k === 'Delete' && this.current) { this.deleteCurrent(); }
        else if (/^[1-6]$/.test(k)) { this.setFilter(FILTERS[+k - 1]); }
        else if (k === 'Escape' && this.query) {
            $('searchInput').value = ''; this.query = ''; this.renderList();
        }
    }

    // ── rendering ────────────────────────────────────────────────────────
    render() {
        this.renderList();
        this.renderDetail();
        this.renderStorageInfo();
    }

    buildChips() {
        const chips = $('chips');
        chips.replaceChildren(...FILTERS.map((f, i) => h('button', {
            class: 'chip', role: 'tab', dataset: { filter: f },
            title: `${f} (${i + 1})`,
            onclick: () => this.setFilter(f),
        })));
    }

    renderChips() {
        const counts = { All: this.commands.length, Favorites: 0 };
        for (const c of this.commands) {
            counts[c.category] = (counts[c.category] || 0) + 1;
            if (c.favorite) counts.Favorites++;
        }
        for (const chip of $('chips').children) {
            const f = chip.dataset.filter;
            const n = f === 'Recent' ? '' : ` ${counts[f] || 0}`;
            chip.replaceChildren(`${FILTER_ICONS[f] || ''}${f}`, h('span', { class: 'chip-count' }, n));
            chip.classList.toggle('active', f === this.filter);
            chip.setAttribute('aria-selected', String(f === this.filter));
        }
    }

    setFilter(f) {
        this.filter = f;
        this.saveSettings();
        this.renderList();
    }

    renderList({ autoselect = false } = {}) {
        const f = this.filter;
        this.visible = Core.search(this.commands, {
            query: this.query,
            category: Core.CATEGORIES.includes(f) ? f : null,
            favorites: f === 'Favorites',
            recent: f === 'Recent',
            limit: f === 'Recent' ? 50 : 0,
        });
        this.renderChips();

        const singleCat = Core.CATEGORIES.includes(f);
        const list = $('commandList');
        list.replaceChildren(...this.visible.map(c => h('div', {
            class: 'item' + (c === this.current ? ' selected' : ''),
            role: 'option',
            'aria-selected': String(c === this.current),
            dataset: { id: c.id },
            onclick: () => { this.select(c); this.showDetailOnMobile(); },
            ondblclick: () => this.focusFirstField(),
        },
        h('span', { class: 'item-star' }, c.favorite ? '★' : ''),
        h('span', { class: 'item-body' },
            h('span', { class: 'item-desc' }, c.description),
            h('code', { class: 'item-cmd' }, c.command)),
        singleCat ? null : h('span', { class: `item-cat cat-${c.category.toLowerCase()}` }, c.category))));

        const info = $('listInfo');
        const where = f === 'All' ? '' : ` in ${f}`;
        if (this.query) {
            info.textContent = `${this.visible.length} match${this.visible.length === 1 ? '' : 'es'} for “${this.query}”${where}`;
        } else if (!this.visible.length && f === 'Favorites') {
            info.textContent = 'No favorites yet — select a command and press ☆ or F.';
        } else if (!this.visible.length && f === 'Recent') {
            info.textContent = 'Nothing used yet — copied commands show up here.';
        } else {
            info.textContent = `${this.visible.length} of ${this.commands.length} commands${where}`;
        }

        if (this.current && this.visible.includes(this.current) && !(autoselect && this.query)) {
            this.scrollToCurrent();
        } else if (autoselect && this.query && this.visible.length) {
            this.select(this.visible[0]);
        } else if (this.current && !this.visible.includes(this.current)) {
            this.select(null);
        }
    }

    select(cmd) {
        if (cmd === this.current) return;
        this.captureValues();
        this.current = cmd;
        for (const el of $('commandList').children) {
            const on = cmd && +el.dataset.id === cmd.id;
            el.classList.toggle('selected', !!on);
            el.setAttribute('aria-selected', String(!!on));
        }
        this.scrollToCurrent();
        this.renderDetail();
    }

    scrollToCurrent() {
        if (!this.current) return;
        $('commandList').querySelector(`[data-id="${this.current.id}"]`)?.scrollIntoView({ block: 'nearest' });
    }

    moveSelection(delta) {
        if (!this.visible.length) return;
        const idx = this.visible.indexOf(this.current);
        const next = idx < 0 ? 0 : Math.min(Math.max(idx + delta, 0), this.visible.length - 1);
        this.select(this.visible[next]);
    }

    focusListItem() {
        $('commandList').focus();
        this.scrollToCurrent();
    }

    focusSearch() {
        document.body.classList.remove('show-detail');
        $('searchInput').focus();
        $('searchInput').select();
    }

    showDetailOnMobile() {
        if (matchMedia('(max-width: 820px)').matches) {
            document.body.classList.add('show-detail');
            window.scrollTo(0, 0);
        }
    }

    renderDetail() {
        const cmd = this.current;
        $('emptyState').hidden = !!cmd;
        $('card').hidden = !cmd;
        if (!cmd) { document.body.classList.remove('show-detail'); return; }

        $('cardBadge').textContent = cmd.category;
        $('cardBadge').className = `badge cat-${cmd.category.toLowerCase()}`;
        $('cardTitle').textContent = cmd.description;
        $('favBtn').textContent = cmd.favorite ? '★' : '☆';
        $('favBtn').setAttribute('aria-pressed', String(cmd.favorite));
        this.renderMeta();

        const names = Core.placeholders(cmd.command);
        $('fieldsSection').hidden = !names.length;
        $('resetBtn').hidden = !names.length;
        const form = $('fields');
        form.replaceChildren(...names.map((name, i) => {
            const id = `field-${i}`;
            const choices = Core.placeholderChoices(name);
            let input;
            if (choices.length) {
                input = h('select', { id, class: 'field-input', dataset: { name } },
                    h('option', { value: '' }, 'Choose…'),
                    ...choices.map(c => h('option', { value: c }, c)));
                input.value = choices.includes(this.values[name]) ? this.values[name] : '';
                input.addEventListener('change', () => this.renderPreview());
            } else {
                const recent = this.settings.recentValues[name] || [];
                input = h('input', {
                    id, class: 'field-input', type: 'text', spellcheck: 'false',
                    placeholder: name, list: recent.length ? `${id}-list` : null,
                    dataset: { name },
                });
                input.value = this.values[name] || '';
                input.addEventListener('input', () => this.renderPreview());
            }
            input.addEventListener('keydown', e => {
                if (e.key !== 'Enter' || e.ctrlKey || e.metaKey) return;
                e.preventDefault();
                const inputs = [...form.querySelectorAll('.field-input')];
                const next = inputs[inputs.indexOf(input) + 1];
                if (next) next.focus(); else this.copy();
            });
            const recent = choices.length ? [] : (this.settings.recentValues[name] || []);
            return h('div', { class: 'field-row' },
                h('label', { for: id, class: 'field-label' }, choices.length ? 'choose one' : name),
                input,
                recent.length ? h('datalist', { id: `${id}-list` }, recent.map(v => h('option', { value: v }))) : null);
        }));

        const isGam = cmd.category === 'GAM';
        $('shellBtn').hidden = !isGam;
        $('docsLink').hidden = !isGam;
        this.renderPreview();
    }

    renderMeta() {
        const c = this.current;
        const parts = [];
        if (c.use_count) parts.push(`Used ${c.use_count}×`);
        if (c.last_used) parts.push(`last ${new Date(c.last_used).toLocaleString()}`);
        $('cardMeta').textContent = parts.join('  ·  ');
    }

    fieldValues() {
        const out = {};
        for (const el of $('fields').querySelectorAll('.field-input')) out[el.dataset.name] = el.value;
        return out;
    }

    captureValues() {
        Object.assign(this.values, this.fieldValues());
    }

    renderPreview() {
        if (!this.current) return;
        const segs = Core.segments(this.current.command, this.fieldValues());
        $('preview').replaceChildren(...segs.map(s =>
            s.type === 'text' ? s.text : h('span', { class: s.type }, s.text)));
    }

    focusFirstField() {
        if (!this.current) return;
        this.showDetailOnMobile();
        const inputs = [...$('fields').querySelectorAll('.field-input')];
        if (!inputs.length) { this.copy(); return; }
        (inputs.find(i => !i.value.trim()) || inputs[0]).focus();
    }

    resetFields() {
        for (const el of $('fields').querySelectorAll('.field-input')) el.value = '';
        this.values = {};
        this.renderPreview();
        $('fields').querySelector('.field-input')?.focus();
    }

    renderStorageInfo() {
        $('storageInfo').textContent = this.storageOk
            ? `${this.commands.length} commands · saved in this browser`
            : 'not saved — storage unavailable';
    }

    // ── actions ──────────────────────────────────────────────────────────
    finishedCommand() {
        if (!this.current) { this.setStatus('Select a command first.'); return null; }
        const values = this.fieldValues();
        const missing = Core.missingValues(this.current.command, values);
        if (missing.length) {
            this.setStatus(`Fill in: ${missing.join(', ')}`);
            this.showDetailOnMobile();
            $('fields').querySelector(`[data-name="${CSS.escape(missing[0])}"]`)?.focus();
            return null;
        }
        return Core.fill(this.current.command, values).trim();
    }

    async writeClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch {
            // Fallback for http:// and older browsers.
            const ta = h('textarea', { style: 'position:fixed;opacity:0' });
            ta.value = text;
            document.body.append(ta);
            ta.select();
            let ok = false;
            try { ok = document.execCommand('copy'); } catch { /* ignore */ }
            ta.remove();
            return ok;
        }
    }

    recordUse() {
        const c = this.current;
        const values = this.fieldValues();
        this.captureValues();
        Core.rememberValues(this.settings.recentValues, values);
        this.saveSettings();
        c.use_count += 1;
        c.last_used = new Date().toISOString();
        this.save();
        this.renderMeta();
        if (this.filter === 'Recent') this.renderList();
    }

    async copy() {
        const text = this.finishedCommand();
        if (text == null) return false;
        if (await this.writeClipboard(text)) {
            this.recordUse();
            this.setStatus('⎘ Copied to clipboard.');
            this.flash($('copyBtn'));
            return true;
        }
        this.setStatus('✖ Copy failed — select the command and copy it manually.');
        return false;
    }

    async openCloudShell() {
        // Open synchronously so pop-up blockers allow it, then copy.
        const text = this.finishedCommand();
        if (text == null) return;
        window.open(CLOUD_SHELL, '_blank', 'noopener');
        if (await this.writeClipboard(text)) {
            this.recordUse();
            this.setStatus('↗ Cloud Shell opened — the command is on your clipboard.', 8000);
        }
    }

    toggleFavorite() {
        const c = this.current;
        if (!c) return;
        c.favorite = !c.favorite;
        this.save();
        $('favBtn').textContent = c.favorite ? '★' : '☆';
        $('favBtn').setAttribute('aria-pressed', String(c.favorite));
        this.renderList();
        this.setStatus(c.favorite ? `★ Added “${c.description}” to favorites.` : `Removed “${c.description}” from favorites.`);
    }

    deleteCurrent() {
        const c = this.current;
        if (!c) return;
        const idx = this.commands.indexOf(c);
        const pos = this.visible.indexOf(c);
        this.commands.splice(idx, 1);
        this.lastDeleted = { cmd: c, idx };
        this.save();
        this.current = null;
        this.renderList();
        const next = this.visible[Math.min(pos, this.visible.length - 1)];
        this.select(next || null);
        if (!next) this.renderDetail();
        this.toast(`Deleted “${c.description}”`, 'Undo', () => this.undoDelete());
    }

    undoDelete() {
        const d = this.lastDeleted;
        if (!d) return;
        this.lastDeleted = null;
        this.commands.splice(Math.min(d.idx, this.commands.length), 0, d.cmd);
        this.save();
        this.hideToast();
        this.renderList();
        this.select(d.cmd);
        this.setStatus(`Restored “${d.cmd.description}”.`);
    }

    // ── editor ───────────────────────────────────────────────────────────
    openEditor(cmd) {
        this.editing = cmd;
        $('editTitle').textContent = cmd ? 'Edit Command' : 'New Command';
        $('editCategory').value = cmd ? cmd.category
            : Core.CATEGORIES.includes(this.filter) ? this.filter
            : this.current ? this.current.category : 'GAM';
        $('editDescription').value = cmd ? cmd.description : '';
        $('editCommand').value = cmd ? cmd.command : '';
        $('editError').textContent = '';
        this.updateEditorHint();
        $('editDialog').showModal();
        (cmd ? $('editDescription') : $('editCommand')).focus();
    }

    updateEditorHint() {
        const names = Core.placeholders($('editCommand').value);
        $('editHint').textContent = names.length
            ? `Fields: ${names.map(n => `<${n}>`).join(', ')}`
            : 'Tip: use <name> for values you fill in each time, or <a|b|c> for a pick-list. Ctrl+Enter saves.';
    }

    saveEditor() {
        let fields;
        try {
            fields = Core.validate($('editCategory').value, $('editCommand').value, $('editDescription').value);
            const dup = Core.findDuplicate(this.commands, fields, this.editing);
            if (dup) throw new Error(`That command already exists in ${dup.category} with the same description.`);
        } catch (err) {
            $('editError').textContent = err.message;
            return;
        }
        let cmd = this.editing;
        if (cmd) {
            Object.assign(cmd, fields);
        } else {
            cmd = Core.makeCommand(fields.category, fields);
            this.commands.push(cmd);
        }
        this.save();
        $('editDialog').close();
        if (!['All', cmd.category].includes(this.filter) && !(this.filter === 'Favorites' && cmd.favorite)) {
            this.filter = this.editing ? 'All' : cmd.category;
            this.saveSettings();
        }
        if (!this.editing && this.query) { $('searchInput').value = ''; this.query = ''; }
        this.current = null;
        this.renderList();
        this.select(cmd);
        this.setStatus(this.editing ? '✔ Saved.' : `✔ Added to ${cmd.category}.`);
        this.editing = null;
    }

    // ── import / export ──────────────────────────────────────────────────
    exportCommands() {
        const data = JSON.stringify(Core.serialize(this.commands, { includeUsage: false }), null, 4);
        const url = URL.createObjectURL(new Blob([data], { type: 'application/json' }));
        const a = h('a', { href: url, download: 'commands-export.json' });
        document.body.append(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        this.setStatus(`Exported ${this.commands.length} commands.`);
    }

    async importFile(file) {
        $('importFile').value = '';
        if (!file) return;
        try {
            const incoming = Core.parseCommands(JSON.parse(await file.text()));
            const { added, skipped } = Core.merge(this.commands, incoming);
            this.save();
            this.render();
            this.setStatus(`Imported ${added} command(s); ${skipped} already present.`, 8000);
        } catch (err) {
            this.setStatus(`✖ Import failed: ${err.message}`, 10000);
        }
    }

    async mergeLibrary() {
        const lib = await this.fetchLibrary();
        const incoming = lib ? lib.commands : Core.parseCommands(FALLBACK_LIBRARY);
        const { added } = Core.merge(this.commands, incoming);
        this.save();
        this.render();
        this.setStatus(added ? `Added ${added} built-in command(s).`
            : lib ? 'You already have every built-in command.'
            : 'commands.json is not reachable from here — use Import instead.', 8000);
    }

    clearHistory() {
        if (!confirm('Reset use counts and the Recent list?')) return;
        for (const c of this.commands) { c.use_count = 0; c.last_used = null; }
        this.save();
        this.render();
    }

    forgetValues() {
        this.settings.recentValues = {};
        this.values = {};
        this.saveSettings();
        this.renderDetail();
        this.setStatus('Forgot remembered field values.');
    }

    // ── feedback ─────────────────────────────────────────────────────────
    setStatus(text, ms = 5000) {
        $('statusText').textContent = text;
        clearTimeout(this._statusTimer);
        this._statusTimer = setTimeout(() => { $('statusText').textContent = 'Ready'; }, ms);
    }

    toast(text, actionLabel, handler) {
        $('toastText').textContent = text;
        $('toastAction').textContent = actionLabel;
        this._toastHandler = handler;
        $('toast').hidden = false;
        clearTimeout(this._toastTimer);
        this._toastTimer = setTimeout(() => this.hideToast(), 10000);
    }

    hideToast() {
        $('toast').hidden = true;
        this._toastHandler = null;
    }

    flash(el) {
        el.classList.remove('flash');
        void el.offsetWidth;
        el.classList.add('flash');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.app = new CommandBankApp();
    window.app.init();

    try {
        new CalmingStarfield({
            container: '#starfield-background',
            starCount: 150,
            driftSensitivity: 0.3,
            colors: ['#2F81F7', '#58A6FF', '#FFFFFF', '#8B949E', '#E3B341'],
            reducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
        });
    } catch { /* decorative only */ }
});
