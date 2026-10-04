// Full-size stills for review: node scripts/frames.mjs <out_dir> t1 t2 ...  -> <out_dir>/t<time>.png
import { chromium } from 'playwright'
import { serve } from './serve.mjs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import { mkdirSync } from 'node:fs'
const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const [out, ...ts] = process.argv.slice(2)
mkdirSync(out, { recursive: true })
const { server, url } = await serve(root)
const browser = await chromium.launch({ args: ['--font-render-hinting=none'] })
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } })
page.on('pageerror', (e) => console.log('[pageerror]', e.message))
page.on('console', (m) => { if (m.type() === 'error') console.log('[console]', m.text()) })
await page.goto(`${url}/src/index.html`)
await page.waitForFunction('window.__ready === true', null, { timeout: 60000 })
for (const t of ts) {
  await page.evaluate((t) => window.seek(t), +t)
  await page.screenshot({ path: join(out, `t${(+t).toFixed(2)}.png`) })
}
await browser.close(); server.close()
console.log('wrote', ts.length, 'frames to', out)
