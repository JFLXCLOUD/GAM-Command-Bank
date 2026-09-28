/**
 * GAM Command Bank — shared command logic (no DOM).
 *
 * Mirrors command_store.py so the desktop and web apps read and write the
 * same commands.json format:
 *
 *   { "GAM": [{ "command": "...", "description": "...", ... }], "AD": [...], "PowerShell": [...] }
 *
 * Works in the browser (window.CommandCore) and in Node (require) for tests.
 */
(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    else root.CommandCore = api;
})(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    const CATEGORIES = ['GAM', 'AD', 'PowerShell'];
    const CATEGORY_ALIASES = {
        gam: 'GAM', ad: 'AD', activedirectory: 'AD', 'active directory': 'AD',
        powershell: 'PowerShell', ps: 'PowerShell',
    };
    const KNOWN_KEYS = new Set(['command', 'description', 'favorite', 'use_count',
        'last_used', 'copied_at', 'category']);
    const MAX_RECENT_VALUES = 10;

    // <name> placeholders; excludes nested brackets and line breaks so that
    // "2>&1" or "<<EOF" are not treated as fields.
    const placeholderRe = () => /<([^<>\r\n]+)>/g;

    let nextId = 1;

    function placeholders(template) {
        const out = [];
        for (const m of String(template || '').matchAll(placeholderRe())) {
            if (!out.includes(m[1])) out.push(m[1]);
        }
        return out;
    }

    function placeholderChoices(name) {
        if (!name.includes('|')) return [];
        const parts = name.split('|').map(p => p.trim());
        return parts.every(Boolean) ? parts : [];
    }

    /** Single-pass substitution; blank values keep their <placeholder>. */
    function fill(template, values) {
        return String(template || '').replace(placeholderRe(), (whole, name) => {
            const v = String((values && values[name]) || '').trim();
            return v || whole;
        });
    }

    /** Split a template into text / value / missing segments for display. */
    function segments(template, values) {
        const out = [];
        let pos = 0;
        for (const m of String(template || '').matchAll(placeholderRe())) {
            if (m.index > pos) out.push({ type: 'text', text: template.slice(pos, m.index) });
            const v = String((values && values[m[1]]) || '').trim();
            out.push(v ? { type: 'value', text: v } : { type: 'missing', text: m[0] });
            pos = m.index + m[0].length;
        }
        if (pos < template.length) out.push({ type: 'text', text: template.slice(pos) });
        return out;
    }

    function missingValues(template, values) {
        return placeholders(template).filter(p => !String((values && values[p]) || '').trim());
    }

    function normalizeCategory(name) {
        if (typeof name !== 'string') return null;
        if (CATEGORIES.includes(name)) return name;
        return CATEGORY_ALIASES[name.trim().toLowerCase()] || null;
    }

    const norm = s => String(s || '').split(/\s+/).filter(Boolean).join(' ').toLowerCase();
    const keyOf = c => `${c.category}\u0000${norm(c.command)}\u0000${norm(c.description)}`;

    function makeCommand(category, raw) {
        if (!raw || typeof raw !== 'object') return null;
        const command = String(raw.command || '').trim();
        if (!command) return null;
        const description = String(raw.description || '').trim() || command;
        const stamps = [raw.last_used, raw.copied_at].filter(s => typeof s === 'string' && s);
        const extra = {};
        for (const [k, v] of Object.entries(raw)) if (!KNOWN_KEYS.has(k)) extra[k] = v;
        return {
            id: nextId++,
            category,
            command,
            description,
            favorite: !!raw.favorite,
            use_count: Math.max(0, parseInt(raw.use_count, 10) || 0),
            last_used: stamps.length ? stamps.sort().pop() : null,
            extra,
        };
    }

    /** Parse any supported layout into a flat, de-duplicated list. */
    function parseCommands(data) {
        if (data && typeof data === 'object' && data.commands && typeof data.commands === 'object'
            && !Array.isArray(data.commands)) {
            data = data.commands;
        }
        if (!data || typeof data !== 'object' || Array.isArray(data)) {
            throw new Error('Expected a JSON object of categories.');
        }
        const out = [];
        const seen = new Set();
        for (const [rawCat, items] of Object.entries(data)) {
            const category = normalizeCategory(rawCat);
            if (!category || !Array.isArray(items)) continue;
            for (const raw of items) {
                const cmd = makeCommand(category, raw);
                if (!cmd || seen.has(keyOf(cmd))) continue;
                seen.add(keyOf(cmd));
                out.push(cmd);
            }
        }
        return out;
    }

    function serialize(commands, { includeUsage = true } = {}) {
        const out = {};
        for (const c of CATEGORIES) out[c] = [];
        for (const c of commands) {
            const item = Object.assign({}, c.extra, {
                command: c.command,
                description: c.description,
                favorite: c.favorite,
            });
            if (includeUsage) {
                item.use_count = c.use_count;
                item.last_used = c.last_used;
            }
            (out[c.category] = out[c.category] || []).push(item);
        }
        return out;
    }

    function validate(category, command, description) {
        const cat = normalizeCategory(category);
        if (!cat) throw new Error(`Unknown category: ${category}`);
        command = String(command || '').trim();
        description = String(description || '').trim();
        if (!command) throw new Error('Command cannot be empty.');
        if (!description) throw new Error('Description cannot be empty.');
        return { category: cat, command, description };
    }

    /** Find an existing command with the same identity (optionally excluding one). */
    function findDuplicate(commands, candidate, except) {
        const k = keyOf(candidate);
        return commands.find(c => c !== except && keyOf(c) === k) || null;
    }

    /** Add commands that are not present yet. Existing ones are untouched. */
    function merge(commands, incoming) {
        const keys = new Set(commands.map(keyOf));
        let added = 0, skipped = 0;
        for (const c of incoming) {
            if (keys.has(keyOf(c))) { skipped++; continue; }
            keys.add(keyOf(c));
            commands.push(makeCommand(c.category, Object.assign({}, c.extra, {
                command: c.command, description: c.description, favorite: c.favorite,
            })));
            added++;
        }
        return { added, skipped };
    }

    function escapeRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

    /**
     * Filter and rank. Every term must match the description, command or
     * category; description matches rank higher, then favorites, then usage.
     */
    function search(commands, { query = '', category = null, favorites = false, recent = false, limit = 0 } = {}) {
        let pool = commands.filter(c =>
            (!category || c.category === category) &&
            (!favorites || c.favorite) &&
            (!recent || c.last_used));
        const terms = String(query).toLowerCase().split(/\s+/).filter(Boolean);

        if (terms.length) {
            const scored = [];
            pool.forEach((c, idx) => {
                const desc = c.description.toLowerCase();
                const hay = `${desc} ${c.command.toLowerCase()} ${c.category.toLowerCase()}`;
                if (!terms.every(t => hay.includes(t))) return;
                let score = 0;
                for (const t of terms) {
                    if (desc.startsWith(t)) score += 4;
                    else if (new RegExp(`\\b${escapeRe(t)}`).test(desc)) score += 3;
                    else if (desc.includes(t)) score += 2;
                    else score += 1;
                }
                scored.push({ c, score, idx });
            });
            scored.sort((a, b) =>
                b.score - a.score ||
                (b.c.favorite - a.c.favorite) ||
                (b.c.use_count - a.c.use_count) ||
                a.idx - b.idx);
            pool = scored.map(s => s.c);
        } else if (recent) {
            pool.sort((a, b) => (b.last_used || '').localeCompare(a.last_used || ''));
        }
        return limit ? pool.slice(0, limit) : pool;
    }

    function rememberValues(store, values) {
        for (const [name, raw] of Object.entries(values)) {
            const v = String(raw || '').trim();
            if (!v || placeholderChoices(name).length) continue;
            const prev = (store[name] || []).filter(x => x !== v);
            store[name] = [v, ...prev].slice(0, MAX_RECENT_VALUES);
        }
        return store;
    }

    return {
        CATEGORIES, placeholders, placeholderChoices, fill, segments, missingValues,
        normalizeCategory, makeCommand, parseCommands, serialize, validate,
        findDuplicate, merge, search, rememberValues,
    };
});
