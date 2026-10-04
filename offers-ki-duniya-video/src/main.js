// Offers Ki Duniya promo — every visual is a pure function of time.
// window.seek(t) paints the frame at t seconds; the renderer screenshots it.
import { pizza, breadsticks, lavaCake, toURL, mulberry32 } from './art.js'

const TL = await (await fetch('../timeline.json')).json()
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
  outQuint: (x) => 1 - (1 - x) ** 5,
  ioQuint: (x) => (x < 0.5 ? 16 * x ** 5 : 1 - (-2 * x + 2) ** 5 / 2),
  outExpo: (x) => (x >= 1 ? 1 : 1 - 2 ** (-10 * x)),
  inExpo: (x) => (x <= 0 ? 0 : 2 ** (10 * x - 10)),
  outBack: (x) => 1 + 2.7 * (x - 1) ** 3 + 1.7 * (x - 1) ** 2,
}
// Damped spring from 0 to 1; `t` is seconds since release.
function spring(t, f = 2.4, z = 0.42) {
  if (t <= 0) return 0
  const w = TAU * f, wd = w * Math.sqrt(1 - z * z)
  return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + ((z * w) / wd) * Math.sin(wd * t))
}
const inr = (n) => '₹' + Math.round(n).toLocaleString('en-IN')

function T(el, o = {}) {
  const { x = 0, y = 0, s = 1, sx, sy, r = 0, op, blur, c = '' } = o
  const pre = c === 'x' ? 'translate(-50%,0) ' : c === 'xy' ? 'translate(-50%,-50%) ' : ''
  el.style.transform = `${pre}translate(${x.toFixed(2)}px,${y.toFixed(2)}px) rotate(${r.toFixed(3)}deg) scale(${(sx ?? s).toFixed(4)},${(sy ?? s).toFixed(4)})`
  if (op !== undefined) el.style.opacity = op.toFixed(3)
  if (blur !== undefined) el.style.filter = blur > 0.05 ? `blur(${blur.toFixed(2)}px)` : 'none'
}
const show = (el, on) => { el.style.visibility = on ? 'visible' : 'hidden' }
// Sections switch with display: a child's own `visibility: visible` would leak through a hidden parent.
const scene = (el, on) => { el.style.display = on ? 'block' : 'none' }
const setText = (el, s) => { if (el.textContent !== s) el.textContent = s }
const setHTML = (el, s) => { if (el.__h !== s) { el.innerHTML = s; el.__h = s } }

/* ------------------------------------------------------------- the offer */
const D = TL.cart.delivery
const tierFor = (sub) => TL.tiers.filter((t) => sub >= t.min).at(-1) || null
const nextTier = (sub) => TL.tiers.find((t) => t.min > sub) || null
const S = TL.site
// One event per item added: what the bar shows before and after the offer lands.
const EV = (() => {
  let sub = 0, pay = 0
  return TL.cart.items.map((it, i) => {
    const from = pay
    sub += it.price
    const tier = tierFor(sub), next = nextTier(sub)
    const save = tier ? tier.off + D : 0
    const dom = sub + D
    pay = dom - save
    const reachedMin = tier ? tier.min : 0
    const meter = next ? clamp((sub - reachedMin) / (next.min - reachedMin)) : 1
    return {
      id: it.id, add: S.adds[i], up: S.ups[i], drop: S.drops[i], count: i + 1,
      from, upTo: i === 0 ? dom : from + it.price, to: pay, dom, save, meter,
      hint: next ? `Add ${inr(next.min - sub)} more to save ${inr(next.off + D)}` : `Top offer unlocked — you save ${inr(save)}`,
      toast: !next ? `Top offer! ${inr(save)} OFF` : i === 0 ? `${inr(save)} OFF applied · free delivery` : `${inr(save)} OFF unlocked`,
    }
  })
})()

/* --------------------------------------------------------------- the menu */
const MENU = [
  { id: 'vegx', name: 'Veg Extravaganza', price: 609, v: 'Medium · Hand Tossed' },
  { id: 'peppy', name: 'Peppy Paneer', price: 459, v: 'Medium · Hand Tossed' },
  { id: 'garlic', name: 'Garlic Breadsticks', price: 129, v: 'Serves 1–2' },
  { id: 'farm', name: 'Farmhouse', price: 459, v: 'Medium · Hand Tossed' },
  { id: 'lava', name: 'Choco Lava Cake', price: 119, v: 'Single' },
  { id: 'marg', name: 'Margherita', price: 259, v: 'Medium · Hand Tossed' },
]

const ART = {}
const A = {}          // anchors in phone-screen coordinates
let CAM = []          // camera keyframes
let FING = []         // finger keyframes
const TAPS = [S.adds[0], S.adds[1], S.adds[2], S.view]

async function init() {
  ART.vegx = toURL(pizza('vegx', 640, 7)); ART.peppy = toURL(pizza('peppy', 640, 11))
  ART.farm = toURL(pizza('farm', 640, 5)); ART.marg = toURL(pizza('marg', 640, 3))
  ART.garlic = toURL(breadsticks(640)); ART.lava = toURL(lavaCake(640))
  ART.hero = toURL(pizza('vegx', 1400, 21)); ART.prom = toURL(pizza('peppy', 1300, 31))

  $('#grid').innerHTML = MENU.map((m) => `
    <div class="card" id="c-${m.id}"><div class="ph"><img src="${ART[m.id]}" alt=""><i class="veg"></i>
      <div class="add"><span class="a-txt">ADD +</span><span class="a-step"><b>−</b><b>1</b><b>+</b></span></div></div>
      <div class="info"><div class="nm">${m.name}</div><div class="pr"><b>${inr(m.price)}</b><span>${m.v}</span></div></div></div>`).join('')
  $('#lines').innerHTML = [TL.cart.items[0], TL.cart.items[2], TL.cart.items[1]].map((it) => `
    <div class="ln"><img src="${ART[it.id]}" alt=""><div><div class="n">${it.name}</div><div class="v">${it.variant}</div></div><span class="q">× 1</span><span class="p">${inr(it.price)}</span></div>`).join('')
  $('#heroPizza').src = ART.hero
  $('#promPizza').src = ART.prom
  $('#ctaPizza').src = ART.hero
  $('#flyImg').src = ART.vegx
  $('#bring').innerHTML = [...'We bring to you…'].map((ch) => `<span>${ch === ' ' ? '&nbsp;' : ch}</span>`).join('')
  $('#ladRows').innerHTML = TL.tiers.map((t, i) => `
    <div class="lr${i === TL.tiers.length - 1 ? ' max' : ''}"><i class="fill"></i>
      <div class="lr-min"><div class="k">${i === TL.tiers.length - 1 ? '<span class="badge">BEST</span>' : ''}ORDER</div><div class="v">${inr(t.min)}+</div></div>
      <div class="lr-off"><div class="v">${inr(t.off + D)} <small>OFF</small></div><div class="s">${inr(t.off)} OFF + <b>${inr(D)} Free Delivery</b></div></div></div>`).join('')

  await Promise.all($$('img').map((im) => (im.complete ? im.decode().catch(() => {}) : new Promise((r) => { im.onload = im.onerror = r }))))
  await document.fonts.ready
  await Promise.all(['900 100px "Fraunces Variable"', 'italic 900 100px "Fraunces Variable"', '800 20px "Inter Variable"', '800 20px "JetBrains Mono"'].map((f) => document.fonts.load(f, '₹0aA')))

  measure()
  window.__ready = true
}

function measure() {
  scene($('#sSite'), true)
  const rig = $('#rig'), bbar = $('#bbar'), sheet = $('#sheet')
  rig.style.transform = 'none'; bbar.style.transform = 'none'; sheet.style.transform = 'none'
  const sc = $('#screen').getBoundingClientRect()
  const rel = (el) => { const r = el.getBoundingClientRect(); return { x: r.left - sc.left + r.width / 2, y: r.top - sc.top + r.height / 2, l: r.left - sc.left, t: r.top - sc.top, w: r.width, h: r.height } }
  A.add = {}; A.img = {}
  for (const m of MENU) { A.add[m.id] = rel($(`#c-${m.id} .add`)); A.img[m.id] = rel($(`#c-${m.id} .ph img`)) }
  A.bag = rel($('#bbar .bag')); A.bbar = rel(bbar); A.view = rel($('#bView'))
  A.vNum = rel($('#vNum')); A.bill = rel($('.bill')); A.url = rel($('.ub-pill')); A.verdict = rel($('#verdict'))
  bbar.style.transform = ''; sheet.style.transform = ''
  scene($('#sSite'), false)

  const fy = 1010, bb = A.bbar.y
  const V = A.add.vegx, G = A.add.garlic, Pp = A.add.peppy
  // [t, focusX, focusY, scale, frameY, ease]
  CAM = [
    [10.0, 215, 466, 1.62, 2980],
    [10.85, 215, 466, 1.62, fy, 'outC'],
    [11.9, 215, 466, 1.62, fy],
    [13.85, 215, 485, 1.76, fy, 'ioC'],
    [14.3, V.x - 40, V.y - 30, 2.5, fy, 'ioC'],
    [14.68, V.x - 40, V.y - 30, 2.5, fy],
    [15.1, 215, 640, 1.95, fy, 'ioC'],
    [15.55, 215, bb - 110, 2.6, fy, 'ioC'],
    [16.95, 220, bb - 110, 2.64, fy, 'lin'],
    [17.2, G.x - 20, G.y - 40, 2.35, fy, 'ioC'],
    [17.45, G.x - 20, G.y - 40, 2.35, fy],
    [17.85, 215, bb - 130, 2.5, fy, 'ioC'],
    [18.45, 215, bb - 130, 2.52, fy, 'lin'],
    [18.68, Pp.x - 40, Pp.y - 20, 2.35, fy, 'ioC'],
    [18.9, Pp.x - 40, Pp.y - 20, 2.35, fy],
    [19.3, 215, bb - 130, 2.5, fy, 'ioC'],
    [20.15, 240, bb - 120, 2.56, fy, 'lin'],
    [20.42, A.view.x - 50, A.view.y - 70, 2.6, fy, 'ioC'],
    [20.55, A.view.x - 50, A.view.y - 70, 2.6, fy],
    [21.0, 215, 500, 1.7, fy, 'ioC'],
    [21.45, 215, A.bill.y - 70, 2.2, fy, 'ioC'],
    [23.1, 215, A.bill.y - 90, 2.3, fy, 'lin'],
    [23.97, A.vNum.x, A.vNum.y, 8.5, 960, 'inC'],
  ]
  // [t, x, y, opacity]
  FING = [
    [13.8, V.x + 70, V.y + 190, 0],
    [14.05, V.x + 40, V.y + 110, 1],
    [14.44, V.x, V.y, 1],
    [14.85, V.x + 30, V.y + 90, 1],
    [17.0, G.x + 40, G.y + 100, 1],
    [17.25, G.x, G.y, 1],
    [17.65, G.x + 40, G.y + 80, 1],
    [18.45, Pp.x + 20, Pp.y + 120, 1],
    [18.7, Pp.x, Pp.y, 1],
    [19.15, Pp.x - 20, Pp.y + 140, 1],
    [20.2, A.view.x + 20, A.view.y + 70, 1],
    [20.4, A.view.x, A.view.y, 1],
    [20.75, A.view.x + 40, A.view.y + 160, 0],
  ]
}

function camAt(t) {
  const K = CAM
  if (t <= K[0][0]) return K[0]
  for (let i = 0; i < K.length - 1; i++) {
    const a = K[i], b = K[i + 1]
    if (t <= b[0]) {
      const e = E[b[5] || 'ioC'](P(t, a[0], b[0]))
      return [t, lerp(a[1], b[1], e), lerp(a[2], b[2], e), Math.exp(lerp(Math.log(a[3]), Math.log(b[3]), e)), lerp(a[4], b[4], e)]
    }
  }
  return K.at(-1)
}
const toFrame = (c, x, y) => ({ x: 540 + (x - c[1]) * c[3], y: c[4] + (y - c[2]) * c[3] })

function fingerAt(t) {
  const K = FING
  if (t <= K[0][0]) return K[0]
  for (let i = 0; i < K.length - 1; i++) {
    const a = K[i], b = K[i + 1]
    if (t <= b[0]) { const e = E.ioC(P(t, a[0], b[0])); return [t, lerp(a[1], b[1], e), lerp(a[2], b[2], e), lerp(a[3], b[3], e)] }
  }
  return K.at(-1)
}

/* -------------------------------------------------------------- particles */
const fx = $('#fx').getContext('2d')
const GOLD = ['#fce3a3', '#f6d48a', '#f2c35e', '#e3a73d', '#fff6dc']
const BURSTS = [
  { t0: 8.02, at: () => ({ x: 540, y: 860 }), n: 70, seed: 11, speed: 1900, spread: TAU, dir: 0, grav: 1500, drag: 1.6, life: 2.0, size: 34, kinds: ['coin', 'coin', 'spark', 'spark', 'spark'] },
  { t0: 8.02, at: () => ({ x: 540, y: 860 }), n: 90, seed: 12, speed: 2600, spread: TAU, dir: 0, grav: 600, drag: 2.4, life: 1.2, size: 10, kinds: ['dot'] },
  { t0: S.drops[2] + 0.45, at: 'bag', n: 46, seed: 21, speed: 1500, spread: 2.2, dir: -Math.PI / 2, grav: 2200, drag: 1.2, life: 1.5, size: 28, kinds: ['coin', 'spark', 'conf'] },
  { t0: 27.5, at: () => ({ x: 540, y: 690 + 4 * 196 + 88 }), n: 40, seed: 31, speed: 1500, spread: 2.4, dir: -Math.PI / 2, grav: 2000, drag: 1.3, life: 1.6, size: 26, kinds: ['coin', 'spark', 'conf'] },
  { t0: 37.75, at: () => ({ x: 540, y: 1003 }), n: 36, seed: 41, speed: 1300, spread: TAU, dir: 0, grav: 900, drag: 2.0, life: 1.3, size: 22, kinds: ['spark', 'conf', 'coin'] },
]

function drawCoin(ctx, r, flip) {
  ctx.scale(Math.max(0.12, Math.abs(flip)), 1)
  const g = ctx.createRadialGradient(-r * 0.3, -r * 0.3, r * 0.1, 0, 0, r)
  g.addColorStop(0, '#fff3c4'); g.addColorStop(0.55, '#f2c35e'); g.addColorStop(1, '#b9822b')
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, 0, r, 0, TAU); ctx.fill()
  ctx.strokeStyle = 'rgba(140,90,20,0.8)'; ctx.lineWidth = r * 0.12; ctx.beginPath(); ctx.arc(0, 0, r * 0.78, 0, TAU); ctx.stroke()
  ctx.fillStyle = '#8a5a12'; ctx.font = `900 ${r * 1.15}px "Inter Variable"`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
  ctx.fillText('₹', 0, r * 0.06)
}
function drawSpark(ctx, r, col) {
  ctx.fillStyle = col
  ctx.beginPath()
  for (let i = 0; i < 8; i++) { const a = (i / 8) * TAU, rr = i % 2 ? r * 0.28 : r; ctx.lineTo(Math.cos(a) * rr, Math.sin(a) * rr) }
  ctx.closePath(); ctx.fill()
}
function drawBursts(t, cam) {
  for (const b of BURSTS) {
    const age = t - b.t0
    if (age < 0 || age > b.life * 1.2) continue
    let o = b.at === 'bag' ? (b._o ||= toFrame(camAt(b.t0), A.bag.x, A.bag.y)) : b.at()
    const rnd = mulberry32(b.seed * 9973)
    for (let i = 0; i < b.n; i++) {
      const a = b.dir + (rnd() - 0.5) * b.spread
      const sp = b.speed * (0.3 + rnd() * 0.8)
      const life = b.life * (0.55 + rnd() * 0.55)
      const kind = b.kinds[(rnd() * b.kinds.length) | 0]
      const size = b.size * (0.55 + rnd() * 0.7)
      const spin = (rnd() - 0.5) * 16, ph = rnd() * TAU
      const col = GOLD[(rnd() * GOLD.length) | 0]
      if (age > life) continue
      const k = b.drag, decay = (1 - Math.exp(-k * age)) / k
      const x = o.x + Math.cos(a) * sp * decay
      const y = o.y + Math.sin(a) * sp * decay + 0.5 * b.grav * age * age
      const alpha = 1 - E.inQ(age / life)
      fx.save(); fx.globalAlpha = alpha; fx.translate(x, y); fx.rotate(ph + spin * age * 0.3)
      if (kind === 'coin') drawCoin(fx, size, Math.cos(ph + spin * age))
      else if (kind === 'spark') { fx.shadowColor = 'rgba(255,220,140,0.9)'; fx.shadowBlur = size * 0.8; drawSpark(fx, size * 0.7, col) }
      else if (kind === 'conf') { fx.fillStyle = i % 3 ? col : '#d8232b'; fx.scale(1, Math.cos(ph + spin * age)); fx.fillRect(-size * 0.35, -size * 0.18, size * 0.7, size * 0.36) }
      else { fx.fillStyle = col; fx.beginPath(); fx.arc(0, 0, size * 0.35, 0, TAU); fx.fill() }
      fx.restore()
    }
  }
}
// slow gold dust for the dark, quiet moments
function drawDust(t, a, b, alpha) {
  const k = clamp(Math.min(P(t, a, a + 0.6), 1 - P(t, b - 0.6, b))) * alpha
  if (k <= 0) return
  const rnd = mulberry32(77)
  for (let i = 0; i < 60; i++) {
    const x0 = rnd() * 1080, y0 = rnd() * 1920, v = 20 + rnd() * 60, ph = rnd() * TAU, r = 1.5 + rnd() * 3.5, tw = 0.5 + rnd()
    const x = x0 + Math.sin(t * 0.6 + ph) * 30
    const y = ((y0 - t * v) % 1920 + 1920) % 1920
    fx.globalAlpha = k * (0.35 + 0.35 * Math.sin(t * 3 * tw + ph))
    fx.fillStyle = '#f6d48a'; fx.beginPath(); fx.arc(x, y, r, 0, TAU); fx.fill()
  }
  fx.globalAlpha = 1
}

/* ------------------------------------------------------------------ scenes */
function wordIn(el, t, t0, { dist = 1.15, dur = 0.42 } = {}) {
  const k = E.outBack(P(t, t0, t0 + dur))
  T(el, { y: (1 - k) * el.offsetHeight * dist, op: P(t, t0, t0 + 0.12) })
}

function hook(t) {
  const sc = $('#sHook')
  scene(sc, t < 6.05)
  if (t >= 6.05) return
  // hero pizza
  const pin = spring(t - 0.02, 1.25, 0.55)
  const dim = E.ioC(P(t, 1.6, 2.3))
  const out = E.inC(P(t, 5.65, 6.0))
  const ps = lerp(0.62, 1, pin) * lerp(1, 0.86, dim) * lerp(1, 0.7, out)
  T($('#heroPizza'), { y: lerp(260, 0, pin) + dim * 150 + out * 400, s: ps, r: t * 7, op: clamp(pin * 1.4) * (1 - out) })
  $('#heroPizza').style.filter = `brightness(${lerp(1, 0.55, dim).toFixed(3)}) saturate(${lerp(1.05, 0.75, dim).toFixed(3)})`
  $('#hookGlow').style.opacity = (lerp(1, 0.35, dim) * (1 - out)).toFixed(3)

  // "Love pizza?"
  const lw = $$('#kLove .kw span')
  const loveOut = E.inC(P(t, 1.42, 1.62))
  wordIn(lw[0], t, 0.3); wordIn(lw[1], t, 0.55)
  T($('#kLove'), { y: -loveOut * 160, op: 1 - loveOut, blur: loveOut * 8 })
  show($('#kLove'), t < 1.65)
  // "But hate the bill?"
  const hw = $$('#kHate .kw span')
  wordIn(hw[0], t, 1.6); wordIn(hw[1], t, 1.86)
  const shake = Math.exp(-(t - 1.95) * 7) * (t > 1.95 ? 1 : 0)
  hw[1].style.transform += ` translateX(${(Math.sin(t * 95) * 16 * shake).toFixed(2)}px)`
  const hateOut = E.inC(P(t, 3.1, 3.32))
  T($('#kHate'), { y: -hateOut * 160, op: 1 - hateOut, blur: hateOut * 8 })
  show($('#kHate'), t >= 1.55 && t < 3.35)

  // receipt
  const rc = $('#receipt')
  const rin = E.outC(P(t, 1.95, 2.5))
  const lift = E.ioC(P(t, 3.2, 3.8))
  const push = E.ioC(P(t, 3.3, 5.6))
  const rout = E.inC(P(t, 5.62, 5.98))
  const thump = t > 4.95 ? Math.exp(-(t - 4.95) * 10) * Math.sin((t - 4.95) * 70) * 10 : 0
  T(rc, { y: lerp(1350, 0, rin) - lift * 90 + thump - rout * 1900, r: lerp(9, -2, rin) - rout * 7, s: lerp(1, 1.05, push) })
  rc.style.filter = `drop-shadow(0 30px 40px rgba(0,0,0,0.5))${rout > 0.01 ? ` blur(${(rout * 14).toFixed(1)}px)` : ''}`
  show(rc, t >= 1.9)
  $$('.rc-l', rc).forEach((l, i) => { const k = E.outC(P(t, 2.55 + i * 0.3, 2.7 + i * 0.3)); T(l, { x: (1 - k) * -24, op: k }) })
  const tot = E.outC(P(t, 3.95, 4.6))
  setText($('#rcTotal'), inr(tot * 1242))
  T($('.rc-tot'), { op: P(t, 3.85, 3.95), s: 1 + 0.06 * Math.exp(-(t - 4.6) * 8) * (t > 4.6 ? 1 : 0) })
  const st = $('#stampFull')
  const sk = E.outQuint(P(t, 4.95, 5.13))
  T(st, { c: 'x', s: lerp(2.6, 1, sk), r: -13, op: sk * 0.92 })
  show(st, t >= 4.95)

  // "Why pay full price, for the same pizza?"
  const ww = $$('#kWhy .kw span')
  wordIn(ww[0], t, 3.35); wordIn(ww[1], t, 3.65)
  const whyOut = E.inC(P(t, 5.6, 5.95))
  T($('#kWhy'), { y: -whyOut * 220, op: 1 - whyOut, blur: whyOut * 10 })
  show($('#kWhy'), t >= 3.3)
}

function reveal(t) {
  const sc = $('#sReveal')
  scene(sc, t >= 5.85 && t < 10.95)
  if (!(t >= 5.85 && t < 10.95)) return
  const on = P(t, 5.9, 6.4)
  const exit = E.inC(P(t, 10.55, 10.95))
  $('#spot').style.opacity = ((0.25 + 0.6 * P(t, 5.9, 7.6)) + (t > 8 ? 0.15 : 0)) * (1 - exit)
  const rays = $('#rays')
  rays.style.opacity = (lerp(0, 0.45, E.inQ(P(t, 6.3, 7.95))) + (t > 8 ? 0.55 * Math.exp(-(t - 8) * 1.2) : 0)) * (1 - exit)
  T(rays, { r: t * 9, s: 1 + (t > 8 ? 0.15 * E.outC(P(t, 8, 9)) : 0) })

  // "We bring to you…"
  const letters = $$('#bring span')
  letters.forEach((l, i) => {
    const t0 = 6.5 + i * 0.038, k = E.outC(P(t, t0, t0 + 0.32))
    T(l, { y: (1 - k) * 46, op: k, blur: (1 - k) * 8 })
  })
  const bOut = E.inQ(P(t, 7.72, 7.98))
  T($('#bring'), { s: 1 + 0.18 * E.inQ(P(t, 7.0, 7.98)), op: 1 - bOut, blur: bOut * 6 })
  show($('#bring'), t < 8.0)

  // logo slam
  const lg = $('#logoBig')
  const lk = spring(t - 8.0, 2.1, 0.42)
  const lExit = E.ioC(P(t, 9.82, 10.32))
  T(lg, { s: lerp(2.6, 1, lk) * lerp(1, 0.62, lExit), y: -lExit * 330, r: lerp(-6, 0, lk), op: (t >= 8.0 ? 1 : 0) * (1 - lExit) })
  show(lg, t >= 8.0)
  const shine = $('#logoBig .shine')
  T(shine, { x: lerp(-260, 1100, E.ioC(P(t, 8.85, 9.55))), r: 0 })
  $$('#logoBig .spk').forEach((s, i) => T(s, { s: 0.75 + 0.35 * Math.sin(t * 5 + i * 2), r: t * 40 * (i ? -1 : 1), op: P(t, 8.3, 8.6) }))
  const ring = $('#ring'), rk = E.outC(P(t, 8.0, 8.75))
  ring.style.width = ring.style.height = `${lerp(10, 1700, rk)}px`
  ring.style.margin = `${-lerp(10, 1700, rk) / 2}px 0 0 ${-lerp(10, 1700, rk) / 2}px`
  ring.style.borderWidth = `${lerp(26, 2, rk)}px`
  ring.style.opacity = t >= 8.0 ? (1 - rk) * 0.9 : 0

  // tagline + typed URL
  const tg = E.outC(P(t, 8.55, 9.0))
  T($('#tagline'), { y: (1 - tg) * 40 - lExit * 200, op: tg * (1 - E.inQ(P(t, 9.8, 10.1))) })
  const up = $('#urlPill')
  const pIn = spring(t - 9.1, 2.4, 0.5)
  const n = Math.floor(P(t, 9.3, 9.92) * 18)
  setText($('#urlTyped'), 'offerskiduniya.com'.slice(0, n))
  $('#urlPill .caret').style.opacity = (t < 9.95 && (t * 2.6) % 1 < 0.62) || (t > 9.25 && t < 9.95) ? 1 : 0
  // match cut: the pill flies up into the browser's address bar as the phone rises
  const fly = E.ioC(P(t, 9.98, 10.82))
  const c = CAM.length ? camAt(10.85) : [0, 215, 466, 1.62, 1010]
  const target = toFrame(c, A.url?.x ?? 215, A.url?.y ?? 72)
  T(up, { c: 'xy', x: 0, y: lerp(1270, target.y, fly) - 1215, s: lerp(Math.min(1, pIn * 1.15), 0.55, fly), op: clamp(pIn * 2) * (1 - P(t, 10.78, 10.92)) })
  up.style.top = '1215px'
  show(up, t >= 9.1)
  sc.style.background = 'transparent'
  $('#sReveal').style.opacity = on
}

const CAPS = [
  { a: 11.75, b: 13.95, t: 'The same <em>Domino</em> menu', s: 'Same kitchen · same pizza' },
  { a: 13.95, b: 16.1, t: 'Just <em>add to cart</em>', s: 'Tap. That’s it.' },
  { a: 16.1, b: 19.55, t: 'Watch the price <em>drop</em>', s: 'Live, with every item' },
  { a: 19.55, b: 22.35, t: 'Best offer, <em>auto-applied</em>', s: 'Free delivery included' },
  { a: 22.35, b: 23.75, t: 'No coupon code.', s: 'The saving shows up by itself' },
]

function site(t) {
  const sc = $('#sSite')
  const on = t >= 9.95 && t < 24.05
  scene(sc, on)
  if (!on) return
  const c = camAt(t)
  const rig = $('#rig')
  rig.style.transform = `translate(${(540 - c[1] * c[3]).toFixed(2)}px,${(c[4] - c[2] * c[3]).toFixed(2)}px) scale(${c[3].toFixed(4)})`
  $('#siteGlow').style.opacity = P(t, 9.95, 10.6)

  // page load
  $('#loadbar').style.width = `${(E.outC(P(t, 10.85, 11.55)) * 100).toFixed(1)}%`
  $('#loadbar').style.opacity = 1 - P(t, 11.55, 11.75)
  $('#skeleton').style.opacity = 1 - P(t, 11.5, 11.8)
  const cards = $$('.card')
  cards.forEach((cd, i) => { const k = E.outC(P(t, 11.6 + i * 0.07, 12.0 + i * 0.07)); T(cd, { y: (1 - k) * 26, op: k }) })
  T($('#page'), { op: P(t, 11.45, 11.7) })

  // finger
  const f = fingerAt(t), fe = $('#finger')
  let press = 0, rip = -1
  for (const tp of TAPS) { if (t > tp - 0.08 && t < tp + 0.16) press = Math.max(press, Math.sin(P(t, tp - 0.08, tp + 0.16) * Math.PI)); if (t >= tp && t < tp + 0.45) rip = P(t, tp, tp + 0.45) }
  fe.style.left = `${f[1].toFixed(1)}px`; fe.style.top = `${f[2].toFixed(1)}px`
  T(fe, { s: 1 - press * 0.22, op: f[3] * 0.95 })
  const ri = $('#finger .rip')
  ri.style.opacity = rip >= 0 ? (1 - rip).toFixed(3) : 0
  ri.style.transform = `translate(-50%,-50%) scale(${rip >= 0 ? 1 + rip * 1.6 : 1})`

  // ADD buttons → steppers, and the fly-to-cart
  for (const e of EV) {
    const btn = $(`#c-${e.id} .add`)
    const k = P(t, e.add + 0.03, e.add + 0.2)
    $('.a-step', btn).style.opacity = k
    const pop = t > e.add ? 1 + 0.16 * Math.sin(P(t, e.add, e.add + 0.25) * Math.PI) : 1 - 0.08 * Math.sin(P(t, e.add - 0.08, e.add) * Math.PI)
    T(btn, { s: pop })
  }
  const flying = EV.find((e) => t >= e.add + 0.04 && t < e.add + 0.55)
  const fl = $('#flyImg')
  if (flying) {
    const k = E.inQ(P(t, flying.add + 0.04, flying.add + 0.52))
    const a = A.img[flying.id], b = A.bag
    const cx = lerp(a.x, b.x, 0.5), cy = Math.min(a.y, b.y) - 160
    const x = (1 - k) ** 2 * a.x + 2 * (1 - k) * k * cx + k * k * b.x
    const y = (1 - k) ** 2 * a.y + 2 * (1 - k) * k * cy + k * k * b.y
    if (fl.__id !== flying.id) { fl.src = ART[flying.id]; fl.__id = flying.id }
    fl.style.left = `${(x - 72).toFixed(1)}px`; fl.style.top = `${(y - 72).toFixed(1)}px`
    T(fl, { s: lerp(1, 0.22, k), r: k * 220, op: 1 - P(t, flying.add + 0.47, flying.add + 0.55) })
  } else fl.style.opacity = 0

  // cart count in the header
  setText($('#hdrCount'), String(EV.filter((e) => t >= e.add + 0.5).length))

  // bottom bar
  const bar = $('#bbar')
  const bin = E.outBack(P(t, S.barIn, S.barIn + 0.38))
  let k = -1
  for (let i = 0; i < EV.length; i++) if (t >= EV[i].add + 0.4) k = i
  const bump = EV.reduce((m, e) => Math.max(m, t > e.drop + 0.5 ? Math.exp(-(t - e.drop - 0.5) * 9) * Math.sin((t - e.drop - 0.5) * 30) * 0.035 : 0), 0)
  bar.style.transform = `translateY(${((1 - bin) * 140).toFixed(2)}%) scale(${(1 + bump).toFixed(4)})`
  if (k >= 0) {
    const e = EV[k]
    const prev = EV[k - 1]
    let pay, green = 0
    if (t < e.drop) pay = lerp(e.from, e.upTo, E.outC(P(t, e.up, e.up + 0.38)))
    else { const dk = P(t, e.drop, e.drop + 0.55); pay = lerp(e.upTo, e.to, E.ioC(dk)); green = Math.sin(dk * Math.PI) + (dk >= 1 ? 0 : 0) }
    const pb = $('#bPay')
    setText(pb, inr(pay))
    pb.style.color = green > 0.01 ? `color-mix(in srgb, #8fe3b0 ${(green * 100).toFixed(0)}%, #fff8ee)` : '#fff8ee'
    const dropped = t >= e.drop
    const domShown = dropped ? e.dom : prev ? prev.dom : null
    const ds = $('#bDom')
    setText(ds, domShown ? inr(domShown) : '')
    ds.style.opacity = dropped ? P(t, e.drop, e.drop + 0.25) : prev ? 1 : 0
    setText($('#bCount'), String(e.count))
    setText($('#bLbl'), `${e.count} item${e.count > 1 ? 's' : ''} · ${dropped || prev ? 'offer applied' : 'Domino price'}`)
    const sv = $('#bSave'), saveShown = t >= e.drop + 0.5 ? e.save : prev ? prev.save : null
    setText(sv, saveShown ? `−${inr(saveShown)}` : '')
    const spop = t >= e.drop + 0.5 ? 1 + 0.35 * Math.exp(-(t - e.drop - 0.5) * 7) * Math.sin(P(t, e.drop + 0.5, e.drop + 0.8) * Math.PI) : 1
    T(sv, { s: spop, op: saveShown ? 1 : 0 })
    const hintShown = t >= e.drop + 0.5 ? e.hint : prev ? prev.hint : 'Offers apply automatically as you add'
    setText($('#hintTxt'), hintShown)
    // The meter measures the stretch to the next rung; reaching a rung fills it, then it restarts.
    const m0 = prev ? prev.meter : 0
    const rung = prev && (e.meter < m0 || e.meter === 1)
    let mf = m0
    if (t >= e.drop && rung) mf = t < e.drop + 0.5 ? lerp(m0, 1, E.ioC(P(t, e.drop, e.drop + 0.45))) : e.meter === 1 ? 1 : lerp(0, e.meter, E.ioC(P(t, e.drop + 0.5, e.drop + 0.95)))
    else if (t >= e.drop + 0.5) mf = lerp(m0, e.meter, E.ioC(P(t, e.drop + 0.5, e.drop + 0.95)))
    $('#meterFill').style.width = `${(mf * 100).toFixed(2)}%`
    // toast
    const ts = $('#toast'), ta = e.drop + 0.55, tb = k === EV.length - 1 ? S.view - 0.1 : e.drop + 1.75
    const tk = E.outBack(P(t, ta, ta + 0.3)) * (1 - E.inQ(P(t, tb - 0.2, tb)))
    setText($('#toastTxt'), e.toast)
    T(ts, { c: 'x', y: (1 - tk) * 30, s: lerp(0.8, 1, tk), op: tk })
  } else { $('#toast').style.opacity = 0 }

  // cart sheet
  const sk = E.outQuint(P(t, S.sheet, S.sheet + 0.5))
  $('#sheet').style.transform = `translateY(${((1 - sk) * 105).toFixed(2)}%)`
  $('#scrim').style.opacity = sk
  $$('.b-row').forEach((r, i) => { const rk = E.outC(P(t, S.rows[i], S.rows[i] + 0.28)); T(r, { x: (1 - rk) * 30, op: lerp(0.15, 1, rk) }) })
  const offRow = $('.b-row.off')
  offRow.style.background = t > S.rows[1] ? `rgba(47,165,98,${(0.16 * Math.exp(-(t - S.rows[1]) * 1.5)).toFixed(3)})` : 'transparent'
  setText($('#payYours'), inr(lerp(1242, 947, E.ioC(P(t, S.pay, S.pay + 0.65)))))
  setText($('#vNum'), inr(lerp(0, 295, E.outC(P(t, S.sheet + 0.3, S.sheet + 1.1)))))
  T($('.v-shine'), { x: lerp(-200, 900, E.ioC(P(t, S.pay + 0.7, S.pay + 1.3))) })
  const stc = $('#stampCode'), stk = E.outQuint(P(t, S.stamp, S.stamp + 0.18))
  T(stc, { c: 'x', s: lerp(2.4, 1, stk), r: -9, op: stk })

  // captions
  const capEl = $('#caption')
  const cur = CAPS.find((q) => t >= q.a && t < q.b + 0.3)
  capEl.innerHTML = ''
  for (const q of CAPS) {
    if (t < q.a || t > q.b + 0.32) continue
    const kin = E.outC(P(t, q.a, q.a + 0.38)), kout = E.inC(P(t, q.b, q.b + 0.3))
    const d = document.createElement('div')
    d.className = 'cap'
    d.innerHTML = `<div class="t">${q.t}</div><div class="s">${q.s}</div>`
    T(d, { y: (1 - kin) * 70 - kout * 60, op: kin * (1 - kout), blur: (1 - kin) * 10 + kout * 6 })
    capEl.appendChild(d)
  }
  $('#capScrim').style.opacity = P(t, 11.4, 11.9) * (1 - P(t, 23.5, 23.9))
  capEl.style.opacity = 1 - P(t, 23.5, 23.8)
  void cur
}

function ladder(t) {
  const sc = $('#sLadder')
  const on = t >= 23.9 && t < 32.2
  scene(sc, on)
  if (!on) return
  const hk = $('.lh-k'), hn = $('.lh-n'), hs = $('.lh-s')
  T(hk, { y: (1 - E.outC(P(t, 24.1, 24.5))) * 30, op: P(t, 24.1, 24.4) })
  const nk = spring(t - 24.0, 1.9, 0.5)
  T(hn, { s: lerp(1.9, 1, nk), op: P(t, 23.95, 24.05) })
  T(hs, { y: (1 - E.outC(P(t, 24.7, 25.1))) * 30, op: P(t, 24.7, 25.0) })
  const drift = (t - 24) * 3
  $$('.lr').forEach((r, i) => {
    const t0 = 25.0 + i * 0.5, rk = E.outBack(P(t, t0, t0 + 0.45))
    T(r, { x: (1 - rk) * 160, y: -drift, op: P(t, t0, t0 + 0.2) })
    const fill = $('.fill', r), off = TL.tiers[i].off + D, max = TL.tiers.at(-1).off + D
    fill.style.width = `${(E.outC(P(t, t0 + 0.15, t0 + 0.75)) * (off / max) * 100).toFixed(2)}%`
  })
  const best = $('.lr.max'), bk = P(t, 27.5, 27.8)
  best.style.boxShadow = `0 0 ${(30 + 60 * bk + 20 * Math.sin(t * 4) * bk).toFixed(1)}px rgba(242,195,94,${(0.15 + 0.3 * bk).toFixed(3)})`
  T($('.lr.max .badge'), { s: lerp(2, 1, E.outQuint(P(t, 27.5, 27.7))), op: P(t, 27.5, 27.6) })
  const rb = $('#ribbon'), rbk = spring(t - 28.5, 2.2, 0.5)
  T(rb, { c: 'x', y: (1 - rbk) * 60 - drift, s: lerp(0.7, 1, rbk), op: P(t, 28.5, 28.65) })
  $('#ladGlow').style.opacity = 0.7 + 0.3 * Math.sin(t * 1.6)
}

function promise(t) {
  const sc = $('#sPromise')
  const on = t >= 31.7 && t < 36.5
  scene(sc, on)
  if (!on) return
  T($('#wipe'), { y: (1 - E.ioC(P(t, 31.72, 32.08))) * 1920 })
  const lines = [['#pl1', 32.1], ['#pl2', 33.4], ['#pl3', 34.9]]
  for (const [id, t0] of lines) {
    const el = $(id), ic = $('.ic', el), tx = $('span', el)
    const ik = spring(t - t0, 2.3, 0.45)
    T(ic, { s: lerp(0.2, 1, ik), r: lerp(-30, 0, ik), op: P(t, t0, t0 + 0.08) })
    const xk = E.outQuint(P(t, t0 + 0.05, t0 + 0.5))
    T(tx, { x: (1 - xk) * 120, op: P(t, t0 + 0.05, t0 + 0.2), blur: (1 - xk) * 8 })
    T(el, { y: -E.ioC(P(t, 35.9, 36.3)) * 80 })
  }
  $('#pl3 u').style.setProperty('--u', `${(E.outC(P(t, 35.3, 35.75)) * 100).toFixed(1)}%`)
  const pz = $('#promPizza'), pk = E.outC(P(t, 32.05, 32.7))
  T(pz, { y: (1 - pk) * 500, r: t * 10, op: pk })
}

function cta(t) {
  const sc = $('#sCta')
  const on = t >= 35.95
  scene(sc, on)
  if (!on) return
  const ik = E.outC(P(t, 35.92, 36.42))
  $('#iris').style.clipPath = `circle(${(ik * 1720).toFixed(1)}px at 540px 1500px)`
  $('#ctaGlow').style.opacity = P(t, 36.2, 36.8) * (0.75 + 0.25 * Math.sin(t * 2))
  const lg = $('#logoEnd'), lk = spring(t - 36.4, 2.0, 0.45)
  T(lg, { s: lerp(0.3, 1, lk), r: lerp(8, 0, lk), op: P(t, 36.4, 36.48) })
  const cp = $('#ctaPizza'), ck = E.outC(P(t, 36.3, 37.1))
  T(cp, { y: (1 - ck) * 420, r: t * 8, op: ck })
  T($('#logoEnd .shine'), { x: lerp(-260, 1000, E.ioC(P(t, 39.1, 39.75))) })
  $$('#logoEnd .spk').forEach((s, i) => T(s, { s: 0.75 + 0.35 * Math.sin(t * 5 + i * 2), r: t * 40 * (i ? -1 : 1) }))
  T($('#ctaK'), { y: (1 - E.outC(P(t, 36.6, 37.0))) * 30, op: P(t, 36.6, 36.9) })
  const uk = spring(t - 36.85, 2.2, 0.5)
  T($('#ctaUrl'), { c: 'x', s: lerp(0.5, 1, uk), op: P(t, 36.85, 36.95) })
  const bk = spring(t - 37.3, 2.2, 0.5)
  const tap = 37.7, press = t > tap - 0.06 && t < tap + 0.2 ? Math.sin(P(t, tap - 0.06, tap + 0.2) * Math.PI) : 0
  const idle = t > 38.6 ? 1 + 0.025 * Math.sin((t - 38.6) * 5) : 1
  T($('#ctaBtn'), { c: 'x', s: lerp(0.5, 1, bk) * (1 - press * 0.07) * idle, op: P(t, 37.3, 37.4) })
  const rp = $('#ctaBtn .rip'), rk = P(t, tap, tap + 0.6)
  rp.style.opacity = t >= tap ? (1 - rk) * 0.9 : 0
  rp.style.transform = `translate(-50%,-50%) scale(${1 + rk * 5})`
  const fg = $('#ctaFinger')
  const fk = E.ioC(P(t, 37.15, 37.65))
  fg.style.left = `${lerp(820, 600, fk)}px`; fg.style.top = `${lerp(1300, 1003, fk)}px`
  T(fg, { s: 1 - press * 0.2, op: P(t, 37.15, 37.3) * (1 - P(t, 38.1, 38.4)) * 0.95 })
  $$('#ctaChips span').forEach((s, i) => { const k = spring(t - (38.1 + i * 0.15), 2.4, 0.5); T(s, { y: (1 - k) * 40, s: lerp(0.6, 1, k), op: P(t, 38.1 + i * 0.15, 38.2 + i * 0.15) }) })
  T($('#ctaTag'), { y: (1 - E.outC(P(t, 40.25, 40.7))) * 30, op: P(t, 40.25, 40.6) })
  T($('#ctaFine'), { op: P(t, 40.6, 41.0) * 0.9 })
}

/* ------------------------------------------------------------------- seek */
window.seek = function seek(t) {
  hook(t); reveal(t); site(t); ladder(t); promise(t); cta(t)
  // flash: logo slam, and the zoom-through into the ladder
  const fl = $('#flash')
  const f1 = t >= 7.98 ? Math.exp(-(t - 7.98) * 7) : 0
  const f2 = P(t, 23.82, 23.98) * (t < 24.0 ? 1 : 0) + (t >= 24.0 ? Math.exp(-(t - 24.0) * 6) : 0)
  fl.style.opacity = clamp(Math.max(f1, f2 * 0.95)).toFixed(3)
  // bg
  $('#bg').style.opacity = 1
  fx.clearRect(0, 0, 1080, 1920)
  drawDust(t, 6.0, 10.6, 1)
  drawDust(t, 24.0, 31.8, 0.6)
  drawDust(t, 36.3, 43.0, 0.8)
  drawBursts(t)
  $('#vignette').style.opacity = t >= 31.8 && t < 36.2 ? 0.35 : 1
}

await init()
const q = new URLSearchParams(location.search)
if (q.has('t')) window.seek(parseFloat(q.get('t')))
