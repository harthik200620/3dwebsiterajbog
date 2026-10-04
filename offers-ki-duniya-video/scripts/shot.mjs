// Screenshot any page of the composition: node scripts/shot.mjs <page> <out.png> [w h] [evalJS]
import { chromium } from 'playwright'
import { serve } from './serve.mjs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const [page = 'src/index.html', out = 'shot.png', w = '1080', h = '1920', js = ''] = process.argv.slice(2)
const { server, url } = await serve(root)
const browser = await chromium.launch()
const p = await browser.newPage({ viewport: { width: +w, height: +h } })
p.on('console', (m) => console.log('[page]', m.text()))
p.on('pageerror', (e) => console.log('[pageerror]', e.message))
await p.goto(`${url}/${page}`)
await p.waitForFunction('window.__ready === true', null, { timeout: 60000 })
if (js) await p.evaluate(js)
await p.screenshot({ path: out })
await browser.close(); server.close()
