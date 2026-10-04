// Render a contact sheet of stills: node scripts/stills.mjs out.png t1 t2 ...
import { chromium } from 'playwright'
import { serve } from './serve.mjs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import { execFileSync } from 'node:child_process'
import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const [out, ...ts] = process.argv.slice(2)
const { server, url } = await serve(root)
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } })
page.on('pageerror', (e) => console.log('[pageerror]', e.message))
page.on('console', (m) => { if (m.type() === 'error') console.log('[console]', m.text()) })
await page.goto(`${url}/src/index.html`)
await page.waitForFunction('window.__ready === true', null, { timeout: 60000 })
const dir = mkdtempSync(join(tmpdir(), 'stills-'))
const files = []
for (const t of ts) {
  await page.evaluate((t) => window.seek(t), +t)
  const f = join(dir, `${String(files.length).padStart(3, '0')}.png`)
  await page.screenshot({ path: f })
  files.push(f)
}
await browser.close(); server.close()
const cols = Math.min(files.length, 4)
execFileSync('ffmpeg', ['-y', '-loglevel', 'error', ...files.flatMap((f) => ['-i', f]), '-filter_complex',
  files.map((_, i) => `[${i}:v]scale=360:640,drawtext=text='${ts[i]}s':x=10:y=10:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.6[v${i}]`).join(';') + ';' +
  files.map((_, i) => `[v${i}]`).join('') + `xstack=inputs=${files.length}:layout=${files.map((_, i) => `${(i % cols) * 360}_${Math.floor(i / cols) * 640}`).join('|')}${files.length < 2 ? '' : ''}[o]`,
  '-map', '[o]', out])
console.log('wrote', out)
