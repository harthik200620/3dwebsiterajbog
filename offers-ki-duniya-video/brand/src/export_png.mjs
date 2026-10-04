import { chromium } from '../../node_modules/playwright/index.mjs'
import { readFileSync } from 'node:fs'
const svg = (f) => 'data:image/svg+xml;base64,' + Buffer.from(readFileSync('../' + f)).toString('base64')
const jobs = [
  // name, svg, width, background (null = transparent), padding fraction, square?
  ['offers-ki-duniya-logo@2x.png', 'offers-ki-duniya-logo.svg', 1600, null, 0.04],
  ['offers-ki-duniya-logo-cream.png', 'offers-ki-duniya-logo.svg', 1600, '#fff6e8', 0.08],
  ['offers-ki-duniya-logo-dark.png', 'offers-ki-duniya-logo-dark.svg', 1600, '#1e120c', 0.08],
  ['offers-ki-duniya-logo-tagline.png', 'offers-ki-duniya-logo-tagline.svg', 1600, null, 0.04],
  ['offers-ki-duniya-logo-stacked.png', 'offers-ki-duniya-logo-stacked.svg', 1000, null, 0.06],
  ['offers-ki-duniya-icon-1024.png', 'offers-ki-duniya-icon.svg', 1024, null, 0.0, true],
  ['app-icon-1024.png', 'offers-ki-duniya-icon.svg', 1024, '#fff6e8', 0.1, true],
  ['apple-touch-icon.png', 'offers-ki-duniya-icon.svg', 180, '#fff6e8', 0.08, true],
  ['favicon-32.png', 'offers-ki-duniya-icon.svg', 32, null, 0.0, true],
  ['favicon-16.png', 'offers-ki-duniya-icon.svg', 16, null, 0.0, true],
  ['social-avatar-1080.png', 'offers-ki-duniya-logo-stacked.svg', 1080, '#fff6e8', 0.16, true],
]
const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1200, height: 1200 }, deviceScaleFactor: 1 })
for (const [name, file, W, bg, padf, square] of jobs) {
  const src = readFileSync('../' + file, 'utf8')
  const [, , vw, vh] = src.match(/viewBox="([-\d.]+) ([-\d.]+) ([\d.]+) ([\d.]+)"/).slice(1).map(Number)
  const pad = Math.round(W * padf)
  const iw = W - 2 * pad
  const ih = square ? iw : Math.round(iw * vh / vw)
  const H = square ? W : ih + 2 * pad
  const fit = square ? `width:${Math.min(iw, iw * vw / vh)}px;height:${Math.min(iw, iw * vh / vw)}px` : `width:${iw}px;height:${ih}px`
  await p.setViewportSize({ width: W, height: H })
  await p.setContent(`<html><body style="margin:0;width:${W}px;height:${H}px;display:flex;align-items:center;justify-content:center;background:${bg || 'transparent'}"><img src="${svg(file)}" style="${fit}"></body></html>`)
  await p.waitForFunction(() => [...document.images].every((i) => i.complete))
  await p.screenshot({ path: '../' + name, omitBackground: !bg })
  console.log(name, W + 'x' + H)
}
await b.close()
