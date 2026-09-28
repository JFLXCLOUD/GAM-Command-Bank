// Run with: node --test tests/web_core.test.js
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Core = require('../web-version/core.js');

test('placeholders are unique and ordered', () => {
    assert.deepEqual(Core.placeholders('gam user <o> add acl <id> user <o>'), ['o', 'id']);
    assert.deepEqual(Core.placeholders('Get-Thing 2>&1 | Out-File <path>'), ['path']);
});

test('fill replaces every occurrence in a single pass', () => {
    assert.equal(Core.fill('<e> teacherID <e>', { e: 'a@b' }), 'a@b teacherID a@b');
    assert.equal(Core.fill('<a> <b>', { a: '<b>', b: 'x' }), '<b> x');
    assert.equal(Core.fill('<a> <b>', { a: '1' }), '1 <b>');
    assert.deepEqual(Core.missingValues('<a> <b>', { a: '1', b: ' ' }), ['b']);
});

test('choices and segments', () => {
    assert.deepEqual(Core.placeholderChoices('reader|writer'), ['reader', 'writer']);
    assert.deepEqual(Core.placeholderChoices('user'), []);
    assert.deepEqual(Core.segments('x <a> <b>', { a: '1' }).map(s => s.type),
        ['text', 'value', 'text', 'missing']);
});

test('parses desktop and legacy web layouts', () => {
    const cmds = Core.parseCommands({
        gam: [{ command: 'gam info domain', description: 'd', copied_at: '2026-02', last_used: '2026-01', x: 1 }],
        PowerShell: [{ command: 'Get-Process', description: 'p' }, { command: 'get-process ', description: 'P' }],
        nope: [{ command: 'x', description: 'y' }],
    });
    assert.equal(cmds.length, 2);
    assert.equal(cmds[0].category, 'GAM');
    assert.equal(cmds[0].last_used, '2026-02');
    const out = Core.serialize(cmds);
    assert.deepEqual(Object.keys(out), ['GAM', 'AD', 'PowerShell']);
    assert.equal(out.GAM[0].x, 1);
    assert.equal('copied_at' in out.GAM[0], false);
    assert.throws(() => Core.parseCommands([1]));
});

test('merge adds only new commands and keeps favorites', () => {
    const mine = Core.parseCommands({ GAM: [{ command: 'a', description: 'A' }] });
    const other = Core.parseCommands({ GAM: [{ command: 'a', description: 'A' }, { command: 'b', description: 'B', favorite: true, use_count: 5 }] });
    assert.deepEqual(Core.merge(mine, other), { added: 1, skipped: 1 });
    assert.equal(mine[1].favorite, true);
    assert.equal(mine[1].use_count, 0);
    assert.deepEqual(Object.keys(mine[1].extra), []);
});

test('search ranks description matches and filters', () => {
    const cmds = Core.parseCommands({
        GAM: [{ command: 'gam print users', description: 'List all' },
              { command: 'gam user <u> suspended on', description: 'Suspend a user' }],
        AD: [{ command: 'Get-ADUser <u>', description: 'Get a user' }],
    });
    assert.equal(Core.search(cmds, { query: 'suspend user' })[0].description, 'Suspend a user');
    assert.equal(Core.search(cmds, { query: 'users' })[0].description, 'List all');
    assert.equal(Core.search(cmds, { query: 'user', category: 'AD' }).length, 1);
    assert.equal(Core.search(cmds, { favorites: true }).length, 0);
});

test('rememberValues keeps most recent first and skips choices', () => {
    const store = {};
    Core.rememberValues(store, { u: 'a', 'x|y': 'x' });
    Core.rememberValues(store, { u: 'b' });
    Core.rememberValues(store, { u: 'a' });
    assert.deepEqual(store, { u: ['a', 'b'] });
});

test('shipped commands.json parses without loss', () => {
    const raw = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'commands.json'), 'utf8'));
    const total = Object.values(raw).reduce((n, l) => n + l.length, 0);
    assert.equal(Core.parseCommands(raw).length, total);
});
