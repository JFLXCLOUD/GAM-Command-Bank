'use strict';

class CommandBankApp {
    constructor() {
        this.commands = { gam: [], ad: [], powershell: [] };
        this.theme = localStorage.getItem('cbTheme') || 'dark';
        this.addPanelOpen = { gam: false, ad: false, powershell: false };
        this.searchQuery = '';
        this._statusTimer = null;
        this.init();
    }

    init() {
        this.loadCommands();
        this.applyTheme();
        this.populateSelects();
        this.updateCounts();
        this.bindEvents();
        this.setStatus('● Ready');
    }

    // ── Theme ──────────────────────────────────────────────────────────────
    applyTheme() {
        document.documentElement.setAttribute('data-theme', this.theme);
        document.getElementById('themeToggle').textContent = this.theme === 'dark' ? '☽' : '☀';
        localStorage.setItem('cbTheme', this.theme);
    }

    toggleTheme() {
        this.theme = this.theme === 'dark' ? 'light' : 'dark';
        this.applyTheme();
        this.setStatus(`${this.theme === 'dark' ? '☽' : '☀'} Switched to ${this.theme} mode`);
    }

    // ── Events ─────────────────────────────────────────────────────────────
    bindEvents() {
        document.getElementById('themeToggle').addEventListener('click', () => this.toggleTheme());

        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => this.switchTab(btn.dataset.tab));
        });

        const searchInput = document.getElementById('searchInput');
        searchInput.addEventListener('input', () => {
            this.searchQuery = searchInput.value.trim().toLowerCase();
            this.onSearch();
        });
        document.getElementById('searchClear').addEventListener('click', () => {
            searchInput.value = '';
            this.searchQuery = '';
            this.onSearch();
        });

        document.addEventListener('keydown', e => {
            if (e.ctrlKey || e.metaKey) {
                if (e.key === '1') { e.preventDefault(); this.switchTab('gam'); }
                if (e.key === '2') { e.preventDefault(); this.switchTab('ad'); }
                if (e.key === '3') { e.preventDefault(); this.switchTab('powershell'); }
                if (e.key === 'd') { e.preventDefault(); this.toggleTheme(); }
            }
        });
    }

    // ── Tabs ───────────────────────────────────────────────────────────────
    switchTab(tab) {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        document.querySelector(`[data-tab="${tab}"]`).classList.add('active');
        document.getElementById(`${tab}-tab`).classList.add('active');
    }

    // ── Search ─────────────────────────────────────────────────────────────
    onSearch() {
        const q = this.searchQuery;
        ['gam', 'ad', 'powershell'].forEach(cat => {
            const select = document.getElementById(`${cat}-select`);
            const filtered = q
                ? this.commands[cat].filter(c =>
                    c.command.toLowerCase().includes(q) ||
                    c.description.toLowerCase().includes(q))
                : this.commands[cat];

            select.innerHTML = '<option value="">Choose a command…</option>';
            filtered.forEach(cmd => {
                const realIdx = this.commands[cat].indexOf(cmd);
                const opt = document.createElement('option');
                opt.value = realIdx;
                opt.textContent = cmd.description + (cmd.favorite ? ' ★' : '');
                select.appendChild(opt);
            });

            document.getElementById(`${cat}-output`).value = '';
            document.getElementById(`${cat}-params`).innerHTML = '';
            document.getElementById(`${cat}-fav`).textContent = '☆';
        });
    }

    // ── Populate ───────────────────────────────────────────────────────────
    populateSelects() {
        ['gam', 'ad', 'powershell'].forEach(cat => {
            const select = document.getElementById(`${cat}-select`);
            const current = select.value;
            select.innerHTML = '<option value="">Choose a command…</option>';
            this.commands[cat].forEach((cmd, i) => {
                const opt = document.createElement('option');
                opt.value = i;
                opt.textContent = cmd.description + (cmd.favorite ? ' ★' : '');
                select.appendChild(opt);
            });
            if (current !== '') select.value = current;
        });
    }

    updateCounts() {
        document.getElementById('gam-count').textContent = `(${this.commands.gam.length})`;
        document.getElementById('ad-count').textContent = `(${this.commands.ad.length})`;
        document.getElementById('ps-count').textContent = `(${this.commands.powershell.length})`;
        const total = this.commands.gam.length + this.commands.ad.length + this.commands.powershell.length;
        document.getElementById('total-count').textContent = `${total} total`;
    }

    // ── Add Panel ──────────────────────────────────────────────────────────
    toggleAddPanel(cat) {
        this.addPanelOpen[cat] = !this.addPanelOpen[cat];
        document.getElementById(`${cat}-add-panel`).classList.toggle('open', this.addPanelOpen[cat]);
    }

    // ── Select Change ──────────────────────────────────────────────────────
    onSelectChange(cat) {
        const select = document.getElementById(`${cat}-select`);
        const idx = select.value;
        const paramsContainer = document.getElementById(`${cat}-params`);
        paramsContainer.innerHTML = '';

        if (idx === '') {
            document.getElementById(`${cat}-output`).value = '';
            document.getElementById(`${cat}-fav`).textContent = '☆';
            return;
        }

        const cmd = this.commands[cat][idx];
        if (!cmd) return;

        document.getElementById(`${cat}-fav`).textContent = cmd.favorite ? '★' : '☆';

        cmd.last_used = new Date().toISOString();
        cmd.use_count = (cmd.use_count || 0) + 1;
        this.saveCommands();

        const placeholders = this.extractPlaceholders(cmd.command);
        placeholders.forEach(ph => {
            const row = document.createElement('div');
            row.className = 'param-row';
            const label = document.createElement('span');
            label.className = 'param-label';
            label.textContent = `‹${ph}›`;
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'param-input';
            input.dataset.placeholder = ph;
            input.addEventListener('input', () => this.buildCommand(cat));
            row.appendChild(label);
            row.appendChild(input);
            paramsContainer.appendChild(row);
        });

        this.buildCommand(cat);
    }

    extractPlaceholders(command) {
        const matches = command.match(/<([^>]+)>/g);
        if (!matches) return [];
        return [...new Set(matches.map(m => m.slice(1, -1)))];
    }

    buildCommand(cat) {
        const select = document.getElementById(`${cat}-select`);
        const idx = select.value;
        const output = document.getElementById(`${cat}-output`);

        if (idx === '') { output.value = ''; return; }

        const cmd = this.commands[cat][idx];
        if (!cmd) return;

        let result = cmd.command;
        document.querySelectorAll(`#${cat}-params .param-input`).forEach(input => {
            const ph = input.dataset.placeholder;
            result = result.replace(`<${ph}>`, input.value || `<${ph}>`);
        });
        output.value = result;
    }

    // ── CRUD ───────────────────────────────────────────────────────────────
    addCommand(cat) {
        const cmdInput = document.getElementById(`${cat}-command`);
        const descInput = document.getElementById(`${cat}-description`);
        const command = cmdInput.value.trim();
        const description = descInput.value.trim();

        if (!command) { this.setStatus('✖ Command cannot be empty.'); return; }
        if (!description) { this.setStatus('✖ Description cannot be empty.'); return; }

        const isDupe = this.commands[cat].some(c =>
            c.command === command && c.description === description);
        if (isDupe) { this.setStatus('✖ Duplicate command.'); return; }

        this.commands[cat].push({
            command, description,
            favorite: false, last_used: null, use_count: 0
        });
        this.saveCommands();
        this.populateSelects();
        this.updateCounts();

        cmdInput.value = '';
        descInput.value = '';
        this.addPanelOpen[cat] = false;
        document.getElementById(`${cat}-add-panel`).classList.remove('open');

        this.setStatus(`✔ Added to ${cat.toUpperCase()}.`);
    }

    removeCommand(cat) {
        const select = document.getElementById(`${cat}-select`);
        const idx = select.value;
        if (idx === '') { this.setStatus('No command selected.'); return; }

        const cmd = this.commands[cat][idx];
        if (!confirm(`Remove "${cmd.description}"?`)) return;

        this.commands[cat].splice(idx, 1);
        this.saveCommands();
        this.populateSelects();
        this.updateCounts();
        document.getElementById(`${cat}-output`).value = '';
        document.getElementById(`${cat}-params`).innerHTML = '';
        document.getElementById(`${cat}-fav`).textContent = '☆';
        this.setStatus(`⌫ Removed "${cmd.description}".`);
    }

    toggleFavorite(cat) {
        const select = document.getElementById(`${cat}-select`);
        const idx = select.value;
        if (idx === '') return;

        const cmd = this.commands[cat][idx];
        if (!cmd) return;

        cmd.favorite = !cmd.favorite;
        document.getElementById(`${cat}-fav`).textContent = cmd.favorite ? '★' : '☆';
        this.saveCommands();
        this.populateSelects();
        select.value = idx;
        this.setStatus(`${cmd.favorite ? '★ Added to' : 'Removed from'} favorites: "${cmd.description}"`);
    }

    // ── Actions ────────────────────────────────────────────────────────────
    copyCommand(cat) {
        const text = document.getElementById(`${cat}-output`).value.trim();
        if (!text) { this.setStatus('Nothing to copy.'); return; }

        const select = document.getElementById(`${cat}-select`);
        const idx = select.value;
        if (idx !== '' && this.commands[cat][idx]) {
            this.commands[cat][idx].copied_at = new Date().toISOString();
            this.saveCommands();
        }

        navigator.clipboard.writeText(text).then(() => {
            this.setStatus('⎘ Copied to clipboard.');
        }).catch(() => {
            const ta = document.getElementById(`${cat}-output`);
            ta.removeAttribute('readonly');
            ta.select();
            document.execCommand('copy');
            ta.setAttribute('readonly', '');
            this.setStatus('⎘ Copied to clipboard.');
        });
    }

    executeCommand(cat) {
        const text = document.getElementById(`${cat}-output`).value.trim();
        if (!text) { this.setStatus('Nothing to execute.'); return; }

        this.copyCommand(cat);
        if (cat === 'gam') {
            window.open('https://shell.cloud.google.com/', '_blank');
            this.setStatus('↗ Google Cloud Shell opened — command is on your clipboard.');
        } else {
            this.setStatus('⎘ Command copied — paste into your terminal to execute.');
        }
    }

    clearOutput(cat) {
        document.getElementById(`${cat}-output`).value = '';
        document.getElementById(`${cat}-params`).innerHTML = '';
        document.getElementById(`${cat}-select`).value = '';
        document.getElementById(`${cat}-fav`).textContent = '☆';
        this.setStatus('Cleared.');
    }

    // ── Persistence ────────────────────────────────────────────────────────
    loadCommands() {
        const saved = localStorage.getItem('gamCommandBank_v3');
        if (saved) {
            try { this.commands = JSON.parse(saved); return; } catch {}
        }
        this.loadDefaults();
    }

    loadDefaults() {
        this.commands = {
            gam: [
                { command: "gam group <group> members", description: "List members of a group", favorite: false, use_count: 0, last_used: null },
                { command: "gam user <user> suspended on", description: "Suspend a user", favorite: false, use_count: 0, last_used: null },
                { command: "gam user <user> unsuspended", description: "Unsuspend a user", favorite: false, use_count: 0, last_used: null },
                { command: "gam user <user> change password newpassword <newpassword>", description: "Change a user's password", favorite: false, use_count: 0, last_used: null },
                { command: "gam create group <group>", description: "Create a new group", favorite: false, use_count: 0, last_used: null },
                { command: "gam delete group <group>", description: "Delete a group", favorite: false, use_count: 0, last_used: null },
                { command: "gam user <user> add group <group>", description: "Add a user to a group", favorite: false, use_count: 0, last_used: null },
                { command: "gam user <user> remove group <group>", description: "Remove a user from a group", favorite: false, use_count: 0, last_used: null },
                { command: "gam info domain", description: "Show domain information", favorite: false, use_count: 0, last_used: null },
                { command: "gam info user <Email Address>", description: "Show user info", favorite: false, use_count: 0, last_used: null },
            ],
            ad: [
                { command: "Get-ADUser -Identity <user>", description: "Get a specific user", favorite: false, use_count: 0, last_used: null },
                { command: "Get-ADGroup -Identity <group>", description: "Get a specific group", favorite: false, use_count: 0, last_used: null },
                { command: "Disable-ADAccount -Identity <user>", description: "Disable a user account", favorite: false, use_count: 0, last_used: null },
                { command: "Enable-ADAccount -Identity <user>", description: "Enable a user account", favorite: false, use_count: 0, last_used: null },
                { command: "Set-ADUser -Identity <user> -Password <securepassword>", description: "Set a user's password", favorite: false, use_count: 0, last_used: null },
                { command: "New-ADGroup -Name <group> -GroupCategory Security -GroupScope Global", description: "Create a new security group", favorite: false, use_count: 0, last_used: null },
                { command: "Remove-ADGroup -Identity <group>", description: "Delete a group", favorite: false, use_count: 0, last_used: null },
                { command: "Add-ADGroupMember -Identity <group> -Members <user>", description: "Add a user to a group", favorite: false, use_count: 0, last_used: null },
                { command: "Remove-ADGroupMember -Identity <group> -Members <user>", description: "Remove a user from a group", favorite: false, use_count: 0, last_used: null },
                { command: "Get-ADDomain", description: "Get domain information", favorite: false, use_count: 0, last_used: null },
            ],
            powershell: [
                { command: "Get-Process", description: "List all running processes", favorite: false, use_count: 0, last_used: null },
                { command: "Stop-Process -Id <process_id>", description: "Stop a process by ID", favorite: false, use_count: 0, last_used: null },
                { command: "Get-Service", description: "List all services", favorite: false, use_count: 0, last_used: null },
                { command: "Start-Service -Name <service_name>", description: "Start a service", favorite: false, use_count: 0, last_used: null },
                { command: "Stop-Service -Name <service_name>", description: "Stop a service", favorite: false, use_count: 0, last_used: null },
                { command: "Get-Item <path>", description: "Get a file or folder", favorite: false, use_count: 0, last_used: null },
                { command: "New-Item -Path <path> -ItemType File", description: "Create a new file", favorite: false, use_count: 0, last_used: null },
                { command: "New-Item -Path <path> -ItemType Directory", description: "Create a new folder", favorite: false, use_count: 0, last_used: null },
                { command: "Remove-Item -Path <path>", description: "Delete a file or folder", favorite: false, use_count: 0, last_used: null },
                { command: "Get-ChildItem -Path <path>", description: "Get files and folders at a path", favorite: false, use_count: 0, last_used: null },
                { command: "Get-EventLog -LogName System -EntryType Error", description: "Get system error events", favorite: false, use_count: 0, last_used: null },
                { command: "Restart-Computer", description: "Restart the computer", favorite: false, use_count: 0, last_used: null },
                { command: "Get-Credential", description: "Get user credentials", favorite: false, use_count: 0, last_used: null },
                { command: "$PSVersionTable.PSVersion", description: "Show PowerShell version", favorite: false, use_count: 0, last_used: null },
            ]
        };
        this.saveCommands();
    }

    saveCommands() {
        localStorage.setItem('gamCommandBank_v3', JSON.stringify(this.commands));
    }

    // ── Status ─────────────────────────────────────────────────────────────
    setStatus(text, ms = 4000) {
        const el = document.getElementById('status-text');
        el.textContent = text;
        clearTimeout(this._statusTimer);
        this._statusTimer = setTimeout(() => { el.textContent = '● Ready'; }, ms);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.app = new CommandBankApp();

    try {
        new CalmingStarfield({
            container: '#starfield-background',
            starCount: 150,
            driftSensitivity: 0.3,
            colors: ['#2F81F7', '#58A6FF', '#FFFFFF', '#8B949E', '#E3B341'],
            reducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches
        });
    } catch {}
});
