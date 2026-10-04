// Frame-accurate render: seek(t) -> screenshot -> ffmpeg, then mux the mix.
//   node scripts/render.mjs [--from 0] [--to 43] [--fps 30] [--out out/offers-ki-duniya-promo.mp4]
//   node scripts/render.mjs --parts 3      (splits the timeline across pages, then concatenates)
import { chromium } from 'playwright'
import { spawn, execFileSync } from 'node:child_process'
import { readFileSync, mkdirSync, writeFileSync, existsSync, rmSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve } from 'node:path'
import { serve } from './serve.mjs'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const TL = JSON.parse(readFileSync(join(root, 'timeline.json'), 'utf8'))
const arg = (k, d) => { const i = process.argv.indexOf(`--${k}`); return i > 0 ? process.argv[i + 1] : d }
const fps = +arg('fps', TL.fps)
const from = +arg('from', 0)
const to = +arg('to', TL.duration)
const parts = +arg('parts', 1)
const out = resolve(root, arg('out', 'out/offers-ki-duniya-promo.mp4'))
const audio = join(root, 'audio/build/mix.wav')
const work = join(root, 'out/.work')
mkdirSync(work, { recursive: true })

async function renderRange(browser, url, f0, f1, file, label) {
  const page = await browser.newPage({ viewport: { width: TL.width, height: TL.height }, deviceScaleFactor: 1 })
  page.on('pageerror', (e) => console.error(`[${label}] pageerror`, e.message))
  await page.goto(`${url}/src/index.html`)
  await page.waitForFunction('window.__ready === true', null, { timeout: 120000 })
  const ff = spawn('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-level', '4.2',
    '-x264-params', 'keyint=60:min-keyint=30', '-r', String(fps), file], { stdio: ['pipe', 'inherit', 'inherit'] })
  const done = new Promise((res, rej) => ff.on('close', (c) => (c === 0 ? res() : rej(new Error(`ffmpeg exited ${c}`)))))
  const t0 = Date.now()
  for (let f = f0; f < f1; f++) {
    await page.evaluate((t) => window.seek(t), f / fps)
    const buf = await page.screenshot({ type: 'jpeg', quality: 95 })
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r))
    if ((f - f0) % 90 === 0) console.log(`[${label}] frame ${f - f0}/${f1 - f0}  ${((Date.now() - t0) / 1000).toFixed(0)}s`)
  }
  ff.stdin.end()
  await done
  await page.close()
}

const { server, url } = await serve(root)
const browser = await chromium.launch({ args: ['--disable-gpu-vsync', '--font-render-hinting=none'] })
const F0 = Math.round(from * fps), F1 = Math.round(to * fps)
const step = Math.ceil((F1 - F0) / parts)
const files = []
const jobs = []
for (let p = 0; p < parts; p++) {
  const a = F0 + p * step, b = Math.min(F1, a + step)
  if (a >= b) break
  const file = join(work, `part${p}.mp4`)
  files.push(file)
  jobs.push(renderRange(browser, url, a, b, file, `part${p}`))
}
await Promise.all(jobs)
await browser.close(); server.close()

let video = files[0]
if (files.length > 1) {
  const list = join(work, 'parts.txt')
  writeFileSync(list, files.map((f) => `file '${f}'`).join('\n'))
  video = join(work, 'video.mp4')
  execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', video])
}
mkdirSync(dirname(out), { recursive: true })
if (existsSync(audio) && from === 0) {
  execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-i', video, '-i', audio, '-map', '0:v', '-map', '1:a',
    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-shortest', '-movflags', '+faststart', out])
} else {
  execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-i', video, '-c', 'copy', '-movflags', '+faststart', out])
}
if (!process.argv.includes('--keep')) rmSync(work, { recursive: true, force: true })
console.log('wrote', out)
