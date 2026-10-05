// Offline end-to-end check of the fictional example. Requires Node 18+.
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { parseArgs } = require('node:util');
const assert = require('node:assert/strict');

const { values } = parseArgs({ options: {
  config: { type: 'string' }, out: { type: 'string' },
  'executable-path': { type: 'string' }, help: { type: 'boolean' }
}});
if (values.help) {
  console.log('node check_review_page.cjs --config examples/config_v2.json --out examples/output/browser-check [--executable-path /path/to/chromium]');
  process.exit(0);
}
if (!values.config || !values.out) throw new Error('--config and --out are required');
const configPath = path.resolve(values.config);
const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
const htmlPath = path.resolve(path.dirname(configPath), config.html);
const output = path.resolve(values.out);
fs.mkdirSync(output, { recursive: true });
const results = [];
function check(name, value) { assert.ok(value, name); results.push({name, ok: true}); }

(async () => {
  let browser;
  try {
    const { chromium } = require('playwright');
    browser = await chromium.launch({headless: true, ...(values['executable-path'] ? {executablePath: values['executable-path']} : {})});
    const context = await browser.newContext({viewport: {width: 1600, height: 1000}, acceptDownloads: true});
    const page = await context.newPage();
    const errors = [], requests = [];
    page.on('pageerror', error => errors.push(String(error)));
    page.on('request', request => {if (/^https?:/.test(request.url())) requests.push(request.url());});
    page.on('dialog', dialog => dialog.accept());
    // Exercise the browser-independent download fallback instead of native save dialogs.
    await page.addInitScript(() => {window.showSaveFilePicker = undefined;});
    await page.goto(pathToFileURL(htmlPath).href);
    await page.waitForSelector('#M-003');
    check('fictional block and translation counts', await page.locator('.row').count() === 14 && await page.locator('.sum-text').count() === 8);
    await page.screenshot({path: path.join(output, 'desktop.png')});
    await page.click('#helpClose');
    await page.click('#M-003 .chip[data-s="revise"]');
    await page.fill('#M-003 .note', 'Confirm the new opening day. 请核对开放日。');
    async function highlight(selector, note) {
      await page.locator(selector).scrollIntoViewIfNeeded();
      await page.locator(selector).evaluate(el => {
        const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
        let text;
        while (walker.nextNode()) if (walker.currentNode.textContent.trim().length > 3) {text = walker.currentNode; break;}
        const range = document.createRange(); range.setStart(text, 0); range.setEnd(text, Math.min(text.length, 16));
        const selection = getSelection(); selection.removeAllRanges(); selection.addRange(range);
      });
      await page.dispatchEvent(selector, 'mouseup');
      await page.waitForSelector('#selPop:not([hidden])');
      await page.click('#popMark');
      const row = page.locator(selector).locator('xpath=ancestor::article');
      await row.locator('.hl-note').last().fill(note);
    }
    await highlight('#M-003 [data-field="en"]', 'Source highlight');
    await highlight('#M-003 [data-field="strict"]', '译文高亮');
    await highlight('#M-007 [data-field="table"]', 'Table highlight');
    await page.click('#M-002 .add-note');
    await page.fill('#M-002 .note', 'Heading note');
    await page.waitForTimeout(500);
    const before = await page.evaluate(key => JSON.parse(localStorage.getItem(key)), config.storage_key);
    check('statuses notes and three field highlights saved', before.blocks['M-003'].status === 'revise' && before.blocks['M-003'].hls.length === 2 && before.blocks['M-007'].hls.length === 1);
    await page.reload();
    check('state and highlight notes restored after reload', await page.locator('#M-003').getAttribute('data-status') === 'revise' && await page.locator('#M-003 mark.hl').count() >= 2 && await page.locator('#M-002 .note').inputValue() === 'Heading note');
    await page.check('#fMarked');
    check('marked filter', await page.locator('#M-004').evaluate(el => el.classList.contains('hide')));
    await page.uncheck('#fMarked');
    await page.check('#fTodo');
    check('undecided filter', await page.locator('#M-003').evaluate(el => el.classList.contains('hide')));
    await page.uncheck('#fTodo');
    await page.selectOption('#fStatus', 'revise');
    check('specific status filter', await page.locator('#M-003').isVisible() && !await page.locator('#M-004').isVisible());
    await page.selectOption('#fStatus', '');
    await page.check('#fChg');
    check('changed filter and new marker', !await page.locator('#M-004').isVisible() && await page.locator('#M-005 .chg-new').isVisible());
    await page.uncheck('#fChg');
    await page.check('#fOpen');
    check('word diff contains removed and added words', (await page.locator('#M-003 .chg-body del').textContent()).includes('Friday') && (await page.locator('#M-003 .chg-body ins').textContent()).includes('Saturday'));
    for (const mode of ['sum', 'strict', 'both']) {
      await page.click(`#viewSeg [data-view="${mode}"]`);
      check('translation view ' + mode, await page.locator('body').getAttribute('data-view') === mode);
    }
    await page.click('#docTabs [data-doc="si"]');
    check('supplement switch', await page.locator('#S-003').isVisible() && !await page.locator('#M-003').isVisible());
    await page.click('#docTabs [data-doc="main"]');
    await page.locator('.fig img').scrollIntoViewIfNeeded();
    check('embedded figure loads', await page.locator('.fig img').evaluate(el => el.complete && el.naturalWidth > 0));
    await page.locator('.fig img').click();
    check('figure zoom', await page.locator('#lightbox').isVisible());
    await page.keyboard.press('Escape');
    async function download(button, filename) {
      const ready = page.waitForEvent('download');
      await page.click(button);
      const file = await ready;
      await file.saveAs(path.join(output, filename));
      return path.join(output, filename);
    }
    const jsonFile = await download('#expJson', 'marks.json');
    const mdFile = await download('#expMd', 'marks.md');
    const payload = JSON.parse(fs.readFileSync(jsonFile, 'utf8'));
    check('JSON and Markdown exports preserve notes', payload.state.blocks['M-003'].note.includes('开放日') && fs.readFileSync(mdFile, 'utf8').includes('bilingual-review-state:'));
    for (const [format, file] of [['JSON', jsonFile], ['Markdown', mdFile]]) {
      await download('#clearAll', 'backup-' + format + '.json');
      check('clear resets state before ' + format + ' import', await page.locator('#M-003 .note').inputValue() === '');
      await page.setInputFiles('#impFile', file);
      await page.waitForFunction(() => document.querySelector('#M-003 .note').value.includes('开放日'));
      check(format + ' import restores highlights', await page.locator('#M-003 mark.hl').count() >= 2);
    }
    // Malformed import must fail without mutating existing marks.
    const invalid = {...payload, state: {...payload.state, blocks: {'M-003': {note: 7}}}};
    await page.setInputFiles('#impFile', {name:'invalid.json', mimeType:'application/json', buffer:Buffer.from(JSON.stringify(invalid))});
    await page.waitForTimeout(100);
    check('malformed import preserves current notes', (await page.locator('#M-003 .note').inputValue()).includes('开放日'));
    for (const width of [900, 390]) {
      await page.setViewportSize({width, height: 1000});
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({path: path.join(output, `narrow-${width}.png`)});
      check('no horizontal overflow at ' + width, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    }
    check('no page errors or external network requests', errors.length === 0 && requests.length === 0);
    console.log(JSON.stringify({status:'passed', checks:results.length}));
    fs.writeFileSync(path.join(output, 'results.json'), JSON.stringify({status:'passed', results, errors, requests}, null, 2));
  } catch (error) {
    fs.writeFileSync(path.join(output, 'results.json'), JSON.stringify({status:'failed', results, error:String(error)}, null, 2));
    console.error(String(error));
    process.exitCode = 1;
  } finally { if (browser) await browser.close(); }
})();
