// Offers Ki Duniya promo — every frame is a pure function of time.
// window.seek(t) paints the frame at t seconds and resolves once its images are decoded;
// the renderer screenshots it.
const TL = await (await fetch('../timeline.json')).json()
const REC = await (await fetch('site/frames.json')).json()
const $ = (s, r = document) => r.querySelector(s)
const $$ = (s, r = document) => [...r.querySelectorAll(s)]

/* ------------------------------------------------------------------ math */
const TAU = Math.PI * 2
const clamp = (x, a = 0, b = 1) => (x < a ? a : x > b ? b : x)
const lerp = (a, b, k) => a + (b - a) * k
const P = (t, a, b) => clamp((t - a) / (b - a))
const E = {
  lin: (x) => x,
  inQ: (x) => x * x,
  outQ: (x) => 1 - (1 - x) * (1 - x),
  inC: (x) => x * x * x,
  outC: (x) => 1 - (1 - x) ** 3,
  ioC: (x) => (x < 0.5 ? 4 * x ** 3 : 1 - (-2 * x + 2) ** 3 / 2),
  ioS: (x) => x * x * (3 - 2 * x),
  outQuint: (x) => 1 - (1 - x) ** 5,
  outExpo: (x) => (x >= 1 ? 1 : 1 - 2 ** (-10 * x)),
}
function mulberry32(a) {
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}
const inr = (n, dec = 0) => '₹' + n.toLocaleString('en-IN', { minimumFractionDigits: dec, maximumFractionDigits: dec })

function T(el, o = {}) {
  const { x = 0, y = 0, s = 1, r = 0, op, blur, c = '' } = o
  const pre = c === 'x' ? 'translate(-50%,0) ' : c === 'xy' ? 'translate(-50%,-50%) ' : ''
  el.style.transform = `${pre}translate(${x.toFixed(2)}px,${y.toFixed(2)}px) rotate(${r.toFixed(3)}deg) scale(${s.toFixed(4)})`
  if (op !== undefined) el.style.opacity = op.toFixed(3)
  if (blur !== undefined) el.style.filter = blur > 0.05 ? `blur(${blur.toFixed(2)}px)` : 'none'
}
// Sections switch with display: a child's own `visibility: visible` would leak through a hidden parent.
const scene = (el, on) => { el.style.display = on ? 'block' : 'none' }
const setText = (el, s) => { if (el.textContent !== s) el.textContent = s }
const setHTML = (el, s) => { if (el.__h !== s) { el.innerHTML = s; el.__h = s } }
// Swap an <img> source and hand back the decode, so seek() can wait for the pixels.
function setImg(el, src) {
  if (el.__src === src) return null
  el.__src = src
  el.src = src
  return el.decode().catch(() => {})
}
// Images used as CSS masks or text fills: decoded once before they are applied.
const cache = new Map()
function loadImg(src) {
  if (!cache.has(src)) {
    const im = new Image()
    im.src = src
    cache.set(src, im.decode().then(() => true, () => false))
    if (cache.size > 24) cache.delete(cache.keys().next().value)
  }
  return cache.get(src)
}
async function setMask(el, src) {
  if (el.__mask === src) return
  el.__mask = src
  const ok = await loadImg(src)
  // without its matte the cut-out would cover the type, so it simply stays hidden
  el.style.visibility = ok ? 'visible' : 'hidden'
  if (ok) el.style.webkitMaskImage = el.style.maskImage = `url("${src}")`
}
async function setBg(el, src) {
  if (el.__bg === src) return
  el.__bg = src
  if (await loadImg(src)) el.style.backgroundImage = `url("${src}")`
}

/* ---------------------------------------------------------------- assets */
const FOOD = '../food/renders'
const PULL_LAST = 59
const pad3 = (i) => String(i).padStart(3, '0')
const pullSrc = (i) => `${FOOD}/pull/pull_${pad3(i)}.jpg`
const matteSrc = (i) => `${FOOD}/pull/matte_${pad3(i)}.png`
const recSrc = (i) => `site/${String(i + 1).padStart(5, '0')}.jpg`

/* ------------------------------------------------- the real site, edited */
const EDL = (() => {
  let o = TL.scenes.site[0]
  return TL.site_edl.map((s) => { const r = { o0: o, o1: o + s.dur, a: s.src[0], b: s.src[1] }; o += s.dur; return r })
})()
function srcTimeAt(t) {
  if (t <= EDL[0].o0) return EDL[0].a
  for (const s of EDL) if (t < s.o1) return s.a + (s.b - s.a) * (t - s.o0) / (s.o1 - s.o0)
  return EDL.at(-1).b
}
// The newest recorded frame at or before a source time (the recording is variable-rate).
function recIndexAtSrc(st) {
  const ts = REC.times
  st += 1e-4
  if (st <= ts[0]) return 0
  let lo = 0, hi = ts.length - 1
  while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (ts[mid] <= st) lo = mid; else hi = mid - 1 }
  return lo
}

// The phone shows K screen pixels per recording pixel; at scale 1 its screen spans 220..860 x 390..1830.
const K = 640 / 576
// 3D swing of the phone: [t, rotateY, rotateX, scale, y offset]
const TILT = [
  [9.62, 24, 10, 0.86, 1500], [10.45, -7, 3, 1.0, 0], [13.65, 6, 2, 1.0, 0], [15.9, -3, 1, 1.0, 0],
  [17.6, 4, 1, 0.98, 0], [19.05, -6, 2, 1.0, 0], [20.05, 3, 1, 1.0, 0], [22.4, -3, 1, 0.98, 0], [24.0, 4, 0, 1.03, 0],
]
function tiltAt(t) {
  if (t <= TILT[0][0]) return TILT[0].slice(1)
  for (let i = 0; i < TILT.length - 1; i++) {
    const a = TILT[i], b = TILT[i + 1]
    if (t <= b[0]) { const e = (i === 0 ? E.outQuint : E.ioC)(P(t, a[0], b[0])); return [1, 2, 3, 4].map((j) => lerp(a[j], b[j], e)) }
  }
  return TILT.at(-1).slice(1)
}

// Pop-outs: a piece of the recording (frozen at source second src, crop in recording pixels)
// lifts off the phone and floats in front of it.
const POPS = [
  { t0: 16.0, t1: 17.0, src: 28.9, crop: [12, 1108, 564, 1256], y: 1150 },
  { t0: 17.66, t1: 18.95, src: 30.4, crop: [18, 650, 558, 968], y: 1060 },
  { t0: 20.1, t1: 21.0, src: 36.6, crop: [12, 1110, 564, 1258], y: 1150 },
  { t0: 21.36, t1: 22.08, src: 41.0, crop: [18, 770, 558, 992], y: 1060 },
  { t0: 22.45, t1: 24.1, src: 42.9, crop: [18, 958, 558, 1052], y: 1180 },
]
const POP_W = 1000

const CAPS = [
  [10.05, 11.7, [['SET'], ['YOUR'], ['LOCATION', 1]], 'Menu &amp; prices from your nearest Domino\'s kitchen'],
  [11.7, 13.7, [['SAME'], ["DOMINO'S", 1], ['MENU']], 'Same kitchen · same pizza'],
  [13.7, 15.93, [['JUST'], ['ADD'], ['TO'], ['CART', 1]], 'Peppy Paneer · Medium · Cheese Burst'],
  [15.93, 19.03, [['WATCH'], ['THE'], ['PRICE'], ['DROP', 1]], 'Saving ₹195 on one pizza'],
  [19.03, 22.03, [['BEST'], ['OFFER,'], ['AUTO-APPLIED', 1]], 'No coupon code'],
  [22.03, 24.1, [['YOU'], ['SAVE'], ['₹295', 1]], '₹250 off + free delivery'],
]

/* -------------------------------------------------------------- overlays */
const steamCtx = $('#steam').getContext('2d')
const grainCtx = $('#grain').getContext('2d')
const leakCtx = $('#leak').getContext('2d')
const bokehCtx = $('#bokeh').getContext('2d')
let GRAIN = []
// A handheld camera never sits perfectly still: a slow drift of a few pixels.
const hand = (t, k = 1) => ({ x: k * (3.2 * Math.sin(t * 0.83) + 1.6 * Math.sin(t * 2.07 + 1.3)), y: k * (2.6 * Math.sin(t * 1.11 + 0.4) + 1.3 * Math.sin(t * 2.71 + 2.1)) })
const PUFFS = (() => {
  const r = mulberry32(4242)
  return Array.from({ length: 34 }, () => ({
    period: 2.6 + r() * 1.8, phase: r() * 5, u: r(), v: r(), rise: 0.7 + r() * 0.6,
    sway: 0.5 + r(), freq: 0.6 + r() * 0.7, ph: r() * TAU, size: 0.7 + r() * 0.6, a: 0.6 + r() * 0.4,
  }))
})()
function steam(t, box, alpha) {
  if (alpha <= 0.001) return
  const [x0, y0, x1, y1, h] = box
  for (const p of PUFFS) {
    const age = ((t + p.phase) % p.period) / p.period
    const x = x0 + p.u * (x1 - x0) + Math.sin(t * p.freq + p.ph + age * 2.6) * 46 * p.sway * age
    const y = y0 + p.v * (y1 - y0) - age * h * p.rise
    const rad = (50 + age * 150) * p.size
    const a = alpha * p.a * Math.sin(Math.PI * age) ** 1.6
    const g = steamCtx.createRadialGradient(x, y, 0, x, y, rad)
    g.addColorStop(0, `rgba(255,248,236,${a.toFixed(4)})`)
    g.addColorStop(0.55, `rgba(255,248,236,${(a * 0.4).toFixed(4)})`)
    g.addColorStop(1, 'rgba(255,248,236,0)')
    steamCtx.fillStyle = g
    steamCtx.save()
    steamCtx.translate(x, y); steamCtx.scale(0.62, 1); steamCtx.translate(-x, -y)
    steamCtx.beginPath(); steamCtx.arc(x, y, rad, 0, TAU); steamCtx.fill()
    steamCtx.restore()
  }
}
// Warm out-of-focus lights drifting behind the phone.
const BOKEH = (() => {
  const r = mulberry32(77)
  const cols = ['255,176,90', '255,206,140', '255,140,70', '255,226,180']
  return Array.from({ length: 30 }, () => ({ x: r() * 1080, y: r() * 1920, rad: 30 + r() ** 2 * 130, a: 0.05 + r() * 0.16,
    vx: (r() - 0.5) * 18, vy: -6 - r() * 22, ph: r() * TAU, col: cols[(r() * cols.length) | 0] }))
})()
function bokeh(t, alpha) {
  bokehCtx.clearRect(0, 0, 1080, 1920)
  if (alpha <= 0.001) return
  for (const b of BOKEH) {
    const x = (((b.x + b.vx * t) % 1180) + 1180) % 1180 - 50
    const y = (((b.y + b.vy * t) % 2020) + 2020) % 2020 - 50
    const a = alpha * b.a * (0.75 + 0.25 * Math.sin(t * 1.3 + b.ph))
    const g = bokehCtx.createRadialGradient(x, y, b.rad * 0.6, x, y, b.rad)
    g.addColorStop(0, `rgba(${b.col},${a.toFixed(4)})`)
    g.addColorStop(0.85, `rgba(${b.col},${(a * 0.8).toFixed(4)})`)
    g.addColorStop(1, `rgba(${b.col},0)`)
    bokehCtx.fillStyle = g
    bokehCtx.beginPath(); bokehCtx.arc(x, y, b.rad, 0, TAU); bokehCtx.fill()
  }
}
// Light leaks: warm film flares that wash across the frame on the big cuts.
const LEAKS = [[3.24, 0.55, 1], [7.92, 0.7, -1], [9.66, 0.65, 1], [23.86, 0.6, -1], [31.72, 0.6, 1], [35.9, 0.65, -1]]
function leaks(t) {
  leakCtx.clearRect(0, 0, 540, 960)
  for (const [t0, d, dir] of LEAKS) {
    const k = P(t, t0, t0 + d)
    if (k <= 0 || k >= 1) continue
    const env = Math.sin(Math.PI * k) ** 1.4
    const cx = dir > 0 ? lerp(-150, 700, E.ioS(k)) : lerp(690, -160, E.ioS(k))
    for (const [ox, oy, r, col, a] of [[0, 300, 420, '255,140,50', 0.55], [80, 560, 300, '255,90,40', 0.35], [-60, 120, 260, '255,210,140', 0.4]]) {
      const g = leakCtx.createRadialGradient(cx + ox, oy, 0, cx + ox, oy, r)
      g.addColorStop(0, `rgba(${col},${(a * env).toFixed(4)})`)
      g.addColorStop(1, `rgba(${col},0)`)
      leakCtx.fillStyle = g
      leakCtx.fillRect(0, 0, 540, 960)
    }
  }
}
function makeGrain() {
  GRAIN = Array.from({ length: 6 }, (_, k) => {
    const c = document.createElement('canvas'); c.width = 540; c.height = 960
    const g = c.getContext('2d'), id = g.createImageData(540, 960), r = mulberry32(900 + k)
    for (let i = 0; i < id.data.length; i += 4) {
      const v = 128 + (r() + r() + r() - 1.5) * 92
      id.data[i] = id.data[i + 1] = id.data[i + 2] = v; id.data[i + 3] = 255
    }
    g.putImageData(id, 0, 0)
    return c
  })
}
function grain(t) {
  const f = Math.round(t * 30), r = mulberry32(f * 7919 + 13)
  grainCtx.drawImage(GRAIN[f % GRAIN.length], -r() * 60, -r() * 60, 1200, 2100)
}
// Camera punches: the whole picture kicks in on the hits, then settles.
const PUNCH = [[0.3, 0.03], [1.62, 0.035], [3.3, 0.03], [8.04, 0.05], [24.0, 0.04], [32.1, 0.025], [33.4, 0.025], [35.0, 0.025], [36.4, 0.035]]
const SHAKE = [[1.88, 9], [8.04, 7]]
function camera(t) {
  let s = 1, x = 0, y = 0
  for (const [t0, a] of PUNCH) if (t >= t0) s += a * Math.exp(-(t - t0) * 7)
  for (const [t0, a] of SHAKE) {
    if (t < t0 || t > t0 + 0.5) continue
    const k = Math.exp(-(t - t0) * 9)
    x += a * k * Math.sin((t - t0) * 70); y += a * 0.6 * k * Math.cos((t - t0) * 55)
  }
  $('#cam').style.transform = `translate(${x.toFixed(2)}px,${y.toFixed(2)}px) scale(${s.toFixed(4)})`
  // whip cuts: a short zoom blur as each new scene lands
  let b = 0
  for (const t0 of [3.3, 24.0, 32.0, 36.0]) if (t >= t0 && t < t0 + 0.2) b = Math.max(b, 7 * (1 - P(t, t0, t0 + 0.2)))
  $('#cam').style.filter = b > 0.05 ? `blur(${b.toFixed(2)}px)` : 'none'
}

/* ------------------------------------------------------------------ build */
async function init() {
  const b = TL.bill
  $('#rcLines').innerHTML = b.items.map((it) => `<div class="rc-l"><span>${it.name.toUpperCase()}<small>${it.variant}</small></span><b>${inr(it.price, 2)}</b></div>`).join('') +
    `<div class="rc-l"><span>TAXES &amp; CHARGES</span><b>${inr(b.taxes, 2)}</b></div>`
  setText($('#rcTotal'), inr(b.domino, 2))
  const D = TL.delivery
  $('#ladRows').innerHTML = TL.tiers.map((t, i) => `
    <div class="lr${i === TL.tiers.length - 1 ? ' max' : ''}"><i class="shine"></i>
      <div class="lr-min"><div class="k">ORDER</div><div class="v">${inr(t.min)}+</div></div>
      <div class="lr-off"><div class="v">${inr(t.off + D)} <small>OFF</small></div><div class="s">${inr(t.off)} off + <b>free delivery</b></div></div></div>`).join('')
  $('#caps').innerHTML = CAPS.map(([, , words, s]) => `<div class="cap"><div class="t">${words.map(([w, em]) => `<span class="w">${em ? `<em>${w}</em>` : w}</span>`).join(' ')}</div><div class="s">${s}</div></div>`).join('')
  $('#pops').innerHTML = POPS.map(() => '<div class="pop"><img alt=""><i class="ring"></i><i class="sweep"></i></div>').join('')
  // the CTA name gets a second, moving-light copy of itself
  const sheen = $('#ctaName').cloneNode(true)
  sheen.id = 'ctaNameSheen'
  sheen.querySelector('#ctaSheen')?.remove()
  $('#sCta').insertBefore(sheen, $('#ctaTag'))

  const still = [['#hero', 'hero.jpg'], ['#siteBgImg', 'hero.jpg'], ['#topImg', 'top.jpg'], ['#ctaImg', 'top.jpg']]
  await Promise.all(still.map(([id, f]) => setImg($(id), `${FOOD}/${f}`)))
  // the pop-out crops are frozen frames of the recording
  await Promise.all(POPS.map((p, i) => setImg($$('.pop img')[i], recSrc(recIndexAtSrc(p.src)))))
  await document.fonts.ready
  await Promise.all(['400 100px "Anton"', '800 100px "Inter Variable"', '600 40px "Inter Variable"', 'italic 800 100px "Fraunces Variable"',
    'italic 500 60px "Fraunces Variable"', '800 30px "JetBrains Mono"', '500 30px "JetBrains Mono"'].map((f) => document.fonts.load(f, '₹0aA')))
  makeGrain()
  window.__ready = true
}

/* ----------------------------------------------------------------- scenes */
function hook(t, pend) {
  const on = t < 3.3
  scene($('#sHook'), on)
  if (!on) return
  // the pull plays in real time, already lifting at the first frame; the type sits behind the slice
  const f = clamp(Math.round(10 + t * 30), 10, PULL_LAST)
  pend.push(setImg($('#pull'), pullSrc(f)), setImg($('#pullFg'), pullSrc(f)), setMask($('#pullFg'), matteSrc(f)))
  const dim = E.ioC(P(t, 1.65, 2.35))
  const hh = hand(t)
  for (const el of [$('#pull'), $('#pullFg')]) {
    T(el, { ...hh, s: lerp(1.02, 1.09, E.outQ(P(t, 0, 3.3))) })
    el.style.filter = dim > 0.001 ? `brightness(${lerp(1, 0.45, dim).toFixed(3)}) blur(${(dim * 7).toFixed(2)}px)` : 'none'
  }
  const lin = E.outQuint(P(t, 0.3, 0.85)), lout = E.inQ(P(t, 1.42, 1.6))
  T($('#kLove'), { s: lerp(1.25, 1, lin) * (1 + 0.06 * lout), op: P(t, 0.3, 0.45) * (1 - lout), blur: (1 - lin) * 14 })
  const hin = E.outQuint(P(t, 1.6, 2.05)), hout = E.inQ(P(t, 3.12, 3.3))
  T($('#kHate'), { s: lerp(1.3, 1, hin), op: P(t, 1.6, 1.72) * (1 - hout), blur: (1 - hin) * 12 })

  const rc = $('#receipt'), rin = E.outC(P(t, 1.85, 2.5))
  T(rc, { c: 'x', y: lerp(1250, 0, rin), r: lerp(-8, -2.5, rin) })
  $$('.rc-l', rc).forEach((l, i) => { const k = E.outC(P(t, 2.25 + i * 0.2, 2.4 + i * 0.2)); T(l, { x: (1 - k) * -18, op: k }) })
  const tk = E.outC(P(t, 2.9, 3.05))
  T($('.rc-tot'), { x: (1 - tk) * -18, op: tk })
}

function problem(t) {
  const on = t >= 3.3 && t < 8.2
  scene($('#sProblem'), on)
  if (!on) return
  const push = P(t, 3.3, 8.2), hh = hand(t)
  const dark = E.ioC(P(t, 5.7, 6.35))
  const hero = $('#hero')
  T(hero, { x: hh.x, y: lerp(0, -40, push) + hh.y, s: lerp(1.04, 1.13, E.outQ(push)) })
  hero.style.filter = dark > 0.001 ? `brightness(${lerp(1, 0.3, dark).toFixed(3)}) blur(${(dark * 12).toFixed(2)}px)` : 'none'
  const out = E.inQ(P(t, 5.62, 5.92))
  $$('#kWhy > span').forEach((s, i) => { const k = E.outQuint(P(t, 3.36 + i * 0.36, 3.86 + i * 0.36)); T(s, { y: (1 - k) * 60 - out * 20, op: P(t, 3.36 + i * 0.36, 3.5 + i * 0.36) * (1 - out) }) })
  $('#strike').style.width = `${(E.ioC(P(t, 3.95, 4.22)) * 104).toFixed(2)}%`
}

function reveal(t, pend) {
  const on = t >= 6.0 && t < 10.35
  scene($('#sReveal'), on)
  if (!on) return
  const bin = E.outC(P(t, 6.48, 6.95)), bout = E.inQ(P(t, 7.8, 8.0))
  T($('#bring span'), { y: (1 - bin) * 30, s: lerp(1, 1.08, P(t, 6.5, 8.0)), op: bin * (1 - bout) })
  $('#bring').style.display = t < 8.02 ? 'block' : 'none'

  const st = $('#nameStage')
  st.style.display = t >= 7.96 ? 'block' : 'none'
  if (t < 7.96) return
  // the name lands on the downbeat, filled with the cheese pull, then turns to gold
  const lk = E.outQuint(P(t, 8.0, 8.5))
  const fill = $('#nameFill')
  pend.push(setBg(fill, pullSrc(clamp(Math.round(30 + (t - 8.0) * 22), 30, PULL_LAST))))
  const gk = E.ioC(P(t, 9.0, 9.35))
  const exit = E.inC(P(t, 9.62, 10.3))
  for (const el of [fill, $('#nameGold'), $('#nameSheen')]) T(el, { s: lerp(1.3, 1, lk) * lerp(1, 3.2, exit), blur: (1 - lk) * 16 + exit * 6 })
  fill.style.opacity = (P(t, 7.98, 8.1) * (1 - gk * 0.85)).toFixed(3)
  $('#nameGold').style.opacity = gk.toFixed(3)
  $('#nameSheen').style.backgroundPosition = `${lerp(140, -40, E.ioC(P(t, 9.3, 9.85))).toFixed(1)}% 0`
  $('#nameGlow').style.opacity = (0.6 + 0.4 * gk).toFixed(3)
  const tg = E.outC(P(t, 8.75, 9.15))
  T($('#tag'), { y: (1 - tg) * 26, op: tg * (1 - exit) })
  const uk = E.outC(P(t, 9.0, 9.4))
  T($('#url'), { c: 'x', y: (1 - uk) * 26, op: uk * (1 - exit) })
  st.style.opacity = (1 - E.inQ(P(t, 9.75, 10.3))).toFixed(3)
}

function site(t, pend) {
  const on = t >= 9.55 && t < 24.3
  scene($('#sSite'), on)
  if (!on) return
  pend.push(setImg($('#rec'), recSrc(recIndexAtSrc(srcTimeAt(t)))))
  const [ry, rx, s, dy] = tiltAt(t)
  // a pop-out dims the phone behind it and pushes it back a little
  let focus = 0
  for (const p of POPS) focus = Math.max(focus, E.ioC(P(t, p.t0, p.t0 + 0.3)) * (1 - E.ioC(P(t, p.t1 - 0.2, p.t1))))
  const sc = s * (1 - 0.06 * focus)
  $('#tilt').style.transform = `perspective(2400px) translateY(${dy.toFixed(1)}px) rotateY(${ry.toFixed(3)}deg) rotateX(${rx.toFixed(3)}deg)`
  $('#rig').style.transform = `translate(${(540 - 320 * sc).toFixed(2)}px,${(1110 - 720 * sc).toFixed(2)}px) scale(${sc.toFixed(4)})`
  $('#rig').style.filter = focus > 0.01 ? `brightness(${(1 - 0.5 * focus).toFixed(3)}) blur(${(2.5 * focus).toFixed(2)}px)` : 'none'
  T($('#siteBgImg'), { s: 1.12 + 0.04 * Math.sin(t * 0.25), x: Math.sin(t * 0.21) * 20 })
  bokeh(t, P(t, 9.6, 10.4))

  // touches, as Android's "show taps" would draw them
  let html = ''
  for (const [tt, x, y] of TL.taps) {
    if (t < tt - 0.16 || t > tt + 0.5) continue
    const press = t < tt ? E.outC(P(t, tt - 0.16, tt)) : 1 - E.inQ(P(t, tt + 0.1, tt + 0.38))
    const squish = 1 - 0.14 * Math.sin(Math.PI * P(t, tt - 0.05, tt + 0.15))
    html += `<i class="tap" style="left:${(x * K - 37).toFixed(1)}px;top:${(y * K - 37).toFixed(1)}px;opacity:${press.toFixed(3)};transform:scale(${squish.toFixed(3)})"></i>`
    if (t >= tt) {
      const rk = P(t, tt, tt + 0.5)
      html += `<i class="rip" style="left:${(x * K - 37).toFixed(1)}px;top:${(y * K - 37).toFixed(1)}px;opacity:${((1 - rk) * 0.9).toFixed(3)};transform:scale(${(1 + E.outQ(rk) * 1.9).toFixed(3)})"></i>`
    }
  }
  setHTML($('#taps'), html)

  // pop-outs: lift off the screen where the element sits, float forward, settle back
  $$('.pop').forEach((el, i) => {
    const p = POPS[i]
    const live = t >= p.t0 && t < p.t1 + 0.05
    el.style.display = live ? 'block' : 'none'
    if (!live) return
    const [x0, y0, x1, y1] = p.crop
    const k = POP_W / (x1 - x0)
    const w = POP_W, h = (y1 - y0) * k
    const img = el.querySelector('img')
    el.style.width = `${w}px`; el.style.height = `${h.toFixed(1)}px`
    img.style.width = `${(576 * k).toFixed(1)}px`; img.style.height = `${(1296 * k).toFixed(1)}px`
    img.style.left = `${(-x0 * k).toFixed(1)}px`; img.style.top = `${(-y0 * k).toFixed(1)}px`
    const kin = E.outQuint(P(t, p.t0, p.t0 + 0.42)), kout = E.inC(P(t, p.t1 - 0.22, p.t1))
    const k2 = kin * (1 - kout)
    const fromY = 1110 - 720 * sc + ((y0 + y1) / 2) * K * sc         // the element's centre on the phone
    const from = { y: fromY - h / 2, s: (K * sc) / k }
    const yTop = lerp(from.y, p.y - h / 2, k2)
    const scl = lerp(from.s, 1, k2) * (1 + 0.012 * Math.sin((t - p.t0) * 3.2) * k2)
    el.style.left = `${((1080 - w) / 2).toFixed(1)}px`
    el.style.top = `${yTop.toFixed(1)}px`
    el.style.transform = `perspective(1600px) rotateX(${((1 - k2) * 18).toFixed(2)}deg) scale(${scl.toFixed(4)})`
    el.style.opacity = clamp(k2 * 1.6).toFixed(3)
    el.querySelector('.ring').style.opacity = (Math.exp(-Math.max(0, t - p.t0 - 0.3) * 3) * kin).toFixed(3)
    T(el.querySelector('.sweep'), { x: lerp(-450, 1400, E.ioC(P(t, p.t0 + 0.2, p.t0 + 0.8))) })
  })

  // captions: word by word
  $$('#caps .cap').forEach((el, i) => {
    const [a, b] = CAPS[i]
    const out = i === CAPS.length - 1 ? 0 : E.inQ(P(t, b - 0.12, b + 0.1))
    el.style.display = t >= a && t < b + 0.1 ? 'block' : 'none'
    if (el.style.display === 'none') return
    $$('.w', el).forEach((w, j) => { const k = E.outQuint(P(t, a + j * 0.07, a + j * 0.07 + 0.4)); T(w, { y: (1 - k) * 70, op: P(t, a + j * 0.07, a + j * 0.07 + 0.12) }) })
    const sk = E.outC(P(t, a + 0.25, a + 0.6))
    T(el.querySelector('.s'), { y: (1 - sk) * 20, op: sk })
    el.style.opacity = (1 - out).toFixed(3)
  })
  $('#capScrim').style.opacity = P(t, 9.9, 10.4).toFixed(3)
  $('#caps').style.opacity = (1 - P(t, 23.85, 24.05)).toFixed(3)
}

function ladder(t) {
  const on = t >= 23.88 && t < 32.25
  const sc = $('#sLadder')
  scene(sc, on)
  if (!on) return
  const enter = E.outC(P(t, 23.88, 24.12))
  sc.style.opacity = enter.toFixed(3)
  T($('#topImg'), { s: lerp(1.08, 1.0, enter) + 0.03 * P(t, 24, 32), r: (t - 24) * 3.2 })
  T($('.lh-k'), { y: (1 - E.outC(P(t, 24.08, 24.45))) * 24, op: P(t, 24.08, 24.35) })
  const nk = E.outQuint(P(t, 24.12, 24.6))
  T($('.lh-n'), { s: lerp(1.25, 1, nk), op: nk, blur: (1 - nk) * 10 })
  T($('.lh-s'), { y: (1 - E.outC(P(t, 24.6, 25.0))) * 24, op: P(t, 24.6, 24.9) })
  $$('.lr').forEach((r, i) => {
    const t0 = 25.0 + i * 0.5, rk = E.outQuint(P(t, t0 - 0.06, t0 + 0.4))
    T(r, { x: (1 - rk) * 140, op: P(t, t0 - 0.06, t0 + 0.1) })
    T(r.querySelector('.shine'), { x: lerp(-400, 1200, E.ioC(P(t, t0 + 0.05, t0 + 0.65))) })
  })
  const best = $('.lr.max'), bk = E.outC(P(t, 27.3, 27.7))
  best.style.boxShadow = `0 20px 40px rgba(0,0,0,0.3), 0 0 ${(80 * bk + 20 * Math.sin(t * 4) * bk).toFixed(1)}px rgba(242,195,94,${(0.42 * bk).toFixed(3)})`
  const rb = E.outQuint(P(t, 28.6, 29.05))
  T($('#ribbon'), { c: 'x', y: (1 - rb) * 50, s: lerp(0.9, 1, rb), op: rb })
}

function promise(t, pend) {
  const on = t >= 31.78 && t < 36.3
  const sc = $('#sPromise')
  scene(sc, on)
  if (!on) return
  sc.style.opacity = E.outC(P(t, 31.78, 32.05)).toFixed(3)
  // the end of the pull in slow motion, each frame blended into the next; the type sits above the slice
  const pf = lerp(40, PULL_LAST, E.outQ(P(t, 31.78, 36.0)))
  const f0 = Math.floor(pf), f1 = Math.min(PULL_LAST, f0 + 1), a = (pf - f0).toFixed(3)
  pend.push(setImg($('#promA'), pullSrc(f0)), setImg($('#promB'), pullSrc(f1)))
  $('#promB').style.opacity = a
  const push = E.outQ(P(t, 31.78, 36.3)), hp = hand(t)
  for (const id of ['#promA', '#promB']) T($(id), { s: lerp(1.03, 1.08, push), x: hp.x, y: 70 + hp.y })
  for (const [id, t0] of [['#pl1', 32.1], ['#pl2', 33.4], ['#pl3', 35.0]]) {
    const k = E.outQuint(P(t, t0, t0 + 0.45))
    T($(id), { x: (1 - k) * -90, op: P(t, t0, t0 + 0.12), blur: (1 - k) * 8 })
  }
  $('#pl3 u').style.setProperty('--u', `${(E.ioC(P(t, 35.4, 35.85)) * 100).toFixed(1)}%`)
}

function cta(t) {
  const on = t >= 35.95
  const sc = $('#sCta')
  scene(sc, on)
  if (!on) return
  const wk = E.ioC(P(t, 35.95, 36.35))
  sc.style.clipPath = wk < 1 ? `inset(${((1 - wk) * 100).toFixed(2)}% 0 0 0)` : 'none'
  const pk = E.outC(P(t, 36.1, 37.0))
  T($('#ctaPizza'), { y: (1 - pk) * 420, r: (t - 36) * 4.5 })
  const nk = E.outQuint(P(t, 36.4, 36.95))
  for (const el of [$('#ctaName'), $('#ctaNameSheen')]) T(el, { s: lerp(1.25, 1, nk), op: nk, blur: (1 - nk) * 12 })
  $('#ctaNameSheen').style.backgroundPosition = `${lerp(140, -40, E.ioC(P(t, 39.1, 39.7))).toFixed(1)}% 0`
  T($('#ctaTag'), { y: (1 - E.outC(P(t, 39.4, 39.8))) * 22, op: P(t, 39.4, 39.7) })
  const uk = E.outC(P(t, 36.85, 37.25))
  T($('#ctaUrl'), { c: 'x', y: (1 - uk) * 24, op: uk })
  const bk = E.outQuint(P(t, 37.3, 37.7))
  const pulse = t > 38.6 ? 1 + 0.022 * Math.sin((t - 38.6) * 4.2) : 1
  T($('#ctaBtn'), { c: 'x', y: (1 - bk) * 24, s: lerp(0.85, 1, bk) * pulse, op: bk })
  $('#ctaBtn').style.boxShadow = `0 22px 60px rgba(239,75,54,${(0.35 + 0.15 * Math.sin(t * 4.2)).toFixed(3)})`
  $$('#ctaChips span').forEach((s, i) => { const k = E.outC(P(t, 38.1 + i * 0.15, 38.45 + i * 0.15)); T(s, { y: (1 - k) * 22, op: k }) })
  T($('#ctaFine'), { op: P(t, 40.6, 41.0) })
}

/* ------------------------------------------------------------------- seek */
window.seek = async function seek(t) {
  const pend = []
  hook(t, pend); problem(t); reveal(t, pend); site(t, pend); ladder(t); promise(t, pend); cta(t)
  camera(t)
  steamCtx.clearRect(0, 0, 1080, 1920)
  steam(t, [140, 1180, 940, 1420, 520], 0.24 * (1 - P(t, 1.7, 2.3)))
  steam(t, [200, 1000, 880, 1200, 560], 0.3 * P(t, 3.3, 3.5) * (1 - P(t, 5.7, 6.2)))
  steam(t, [120, 1250, 960, 1450, 520], 0.26 * P(t, 31.9, 32.3) * (1 - P(t, 35.95, 36.2)))
  steam(t, [260, 1460, 820, 1580, 300], 0.16 * P(t, 36.6, 37.4))
  leaks(t)
  grain(t)
  await Promise.all(pend.filter(Boolean))
}

await init()
const q = new URLSearchParams(location.search)
if (q.has('t')) await window.seek(parseFloat(q.get('t')))
