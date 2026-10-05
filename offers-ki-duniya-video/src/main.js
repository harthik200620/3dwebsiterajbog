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

/* ---------------------------------------------------------------- assets */
const FOOD = '../food/renders'
const PULL_LAST = 59
const pullSrc = (i) => `${FOOD}/pull/pull_${String(i).padStart(3, '0')}.jpg`
const recSrc = (i) => `site/${String(i + 1).padStart(5, '0')}.jpg`

/* ------------------------------------------------- the real site, edited */
// Output time -> source time in the recording, segment by segment (timeline.json site_edl).
const EDL = (() => {
  let o = TL.scenes.site[0]
  return TL.site_edl.map((s) => { const r = { o0: o, o1: o + s.dur, a: s.src[0], b: s.src[1], cap: s.cap }; o += s.dur; return r })
})()
function srcTimeAt(t) {
  if (t <= EDL[0].o0) return EDL[0].a
  for (const s of EDL) if (t < s.o1) return s.a + (s.b - s.a) * (t - s.o0) / (s.o1 - s.o0)
  return EDL.at(-1).b
}
// The newest recorded frame at or before that source time (the recording is variable-rate).
function recIndexAt(t) {
  const st = srcTimeAt(t) + 1e-4, ts = REC.times
  if (st <= ts[0]) return 0
  let lo = 0, hi = ts.length - 1
  while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (ts[mid] <= st) lo = mid; else hi = mid - 1 }
  return lo
}

// The phone is shown at K screen pixels per recording pixel. A camera keyframe puts the
// recording point (fx, fy) at frame position (cx, cy) with zoom s.
const K = 640 / 576
const HOME = [288, 648, 540, 1110]
const BAR = [288, 1180, 540, 1250]
const CAMS = [
  // t, fx, fy, cx, cy, s, ease into this key
  [9.62, 288, 648, 540, 1110 + 1500, 1.0],
  [10.4, ...HOME, 1.0, 'outC'],
  [15.8, ...HOME, 1.035, 'lin'],
  [16.22, ...BAR, 1.45, 'ioC'],
  [17.0, ...BAR, 1.47, 'lin'],
  [17.5, 288, 805, 540, 1090, 1.4, 'ioC'],
  [18.95, 288, 805, 540, 1090, 1.43, 'lin'],
  [19.32, ...HOME, 1.0, 'ioC'],
  [20.0, ...HOME, 1.015, 'lin'],
  [20.34, ...BAR, 1.45, 'ioC'],
  [21.0, ...BAR, 1.47, 'lin'],
  [21.38, 288, 880, 540, 1090, 1.4, 'ioC'],
  [22.0, 288, 880, 540, 1090, 1.42, 'lin'],
  [22.42, 300, 965, 540, 1130, 1.36, 'ioC'],
  [24.0, 300, 965, 540, 1130, 1.46, 'lin'],
]
function camAt(t) {
  const Kf = CAMS
  if (t <= Kf[0][0]) return Kf[0].slice(1, 6)
  for (let i = 0; i < Kf.length - 1; i++) {
    const a = Kf[i], b = Kf[i + 1]
    if (t <= b[0]) {
      const e = E[b[6] || 'ioC'](P(t, a[0], b[0]))
      return [1, 2, 3, 4].map((j) => lerp(a[j], b[j], e)).concat(Math.exp(lerp(Math.log(a[5]), Math.log(b[5]), e)))
    }
  }
  return Kf.at(-1).slice(1, 6)
}

const CAPS = [
  [10.05, 11.7, 'Set your location', 'Menu &amp; prices from your nearest Domino kitchen'],
  [11.7, 13.7, 'The same <em>Domino</em> menu', 'Same kitchen · same pizza'],
  [13.7, 15.93, 'Just add to cart', 'Peppy Paneer · Medium · Cheese Burst'],
  [15.93, 19.03, 'Watch the price <em>drop</em>', 'Saving ₹195 on one pizza'],
  [19.03, 22.03, 'Best offer, <em>auto-applied</em>', 'No coupon code'],
  [22.03, 24.1, 'You save <em>₹295</em>', '₹250 off + free delivery'],
]

// A handheld camera never sits perfectly still: a slow drift of a few pixels.
const hand = (t, k = 1) => ({ x: k * (3.2 * Math.sin(t * 0.83) + 1.6 * Math.sin(t * 2.07 + 1.3)), y: k * (2.6 * Math.sin(t * 1.11 + 0.4) + 1.3 * Math.sin(t * 2.71 + 2.1)) })

/* -------------------------------------------------------------- overlays */
const steamCtx = $('#steam').getContext('2d')
const grainCtx = $('#grain').getContext('2d')
let GRAIN = []
// Steam: soft puffs that rise, widen, sway and fade; every puff is a pure function of t.
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

/* ------------------------------------------------------------------ build */
async function init() {
  const b = TL.bill
  $('#rcLines').innerHTML = b.items.map((it) => `<div class="rc-l"><span>${it.name.toUpperCase()}<small>${it.variant}</small></span><b>${inr(it.price, 2)}</b></div>`).join('') +
    `<div class="rc-l"><span>TAXES &amp; CHARGES</span><b>${inr(b.taxes, 2)}</b></div>`
  const D = TL.delivery
  $('#ladRows').innerHTML = TL.tiers.map((t, i) => `
    <div class="lr${i === TL.tiers.length - 1 ? ' max' : ''}">
      <div class="lr-min"><div class="k">ORDER</div><div class="v">${inr(t.min)}+</div></div>
      <div class="lr-off"><div class="v">${inr(t.off + D)} <small>OFF</small></div><div class="s">${inr(t.off)} off + <b>free delivery</b></div></div></div>`).join('')
  $('#caps').innerHTML = CAPS.map(([, , t, s]) => `<div class="cap"><div class="t">${t}</div><div class="s">${s}</div></div>`).join('')

  const still = [['#hero', 'hero.jpg'], ['#siteBgImg', 'hero.jpg'], ['#topImg', 'top.jpg'], ['#ctaImg', 'top.jpg']]
  await Promise.all(still.map(([id, f]) => setImg($(id), `${FOOD}/${f}`)))
  await Promise.all($$('img').filter((im) => !im.__src).map((im) => (im.complete ? im.decode().catch(() => {}) : new Promise((r) => { im.onload = im.onerror = r }))))
  await document.fonts.ready
  await Promise.all(['800 100px "Inter Variable"', '600 40px "Inter Variable"', 'italic 800 100px "Fraunces Variable"', '900 100px "Fraunces Variable"',
    'italic 500 60px "Fraunces Variable"', '800 30px "JetBrains Mono"', '500 30px "JetBrains Mono"'].map((f) => document.fonts.load(f, '₹0aA')))
  makeGrain()
  window.__ready = true
}

/* ----------------------------------------------------------------- scenes */
function hook(t, pend) {
  const on = t < 3.3
  scene($('#sHook'), on)
  if (!on) return
  // the pull plays in real time, already lifting at the first frame, and peaks at ~1.6 s
  // (on "Love pizza?"); it holds, dimmed, while the bill arrives
  pend.push(setImg($('#pull'), pullSrc(clamp(Math.round(10 + t * 30), 10, PULL_LAST))))
  const dim = E.ioC(P(t, 1.65, 2.35))
  T($('#pull'), { ...hand(t), s: lerp(1.02, 1.09, E.outQ(P(t, 0, 3.3))) })
  $('#pull').style.filter = dim > 0.001 ? `brightness(${lerp(1, 0.48, dim).toFixed(3)}) blur(${(dim * 7).toFixed(2)}px)` : 'none'

  const lin = E.outC(P(t, 0.3, 0.75)), lout = E.inQ(P(t, 1.42, 1.6))
  T($('#kLove'), { y: (1 - lin) * 36 - lout * 24, op: lin * (1 - lout) })
  const hin = E.outC(P(t, 1.6, 2.05)), hout = E.inQ(P(t, 3.12, 3.3))
  T($('#kHate'), { y: (1 - hin) * 36, op: hin * (1 - hout) })

  const rc = $('#receipt'), rin = E.outC(P(t, 1.85, 2.5))
  T(rc, { c: 'x', y: lerp(1250, 0, rin), r: lerp(-8, -2.5, rin) })
  $$('.rc-l', rc).forEach((l, i) => { const k = E.outC(P(t, 2.25 + i * 0.2, 2.4 + i * 0.2)); T(l, { x: (1 - k) * -18, op: k }) })
  // the total prints like every other line: a receipt doesn't count up
  setText($('#rcTotal'), inr(TL.bill.domino, 2))
  const tk = E.outC(P(t, 2.9, 3.05))
  T($('.rc-tot'), { x: (1 - tk) * -18, op: tk })
}

function problem(t, pend) {
  const on = t >= 3.3 && t < 8.2
  scene($('#sProblem'), on)
  if (!on) return
  const push = P(t, 3.3, 8.2)
  const dark = E.ioC(P(t, 5.7, 6.35))
  const hero = $('#hero')
  const hh = hand(t)
  T(hero, { x: hh.x, y: lerp(0, -40, push) + hh.y, s: lerp(1.04, 1.13, E.outQ(push)) })
  hero.style.filter = dark > 0.001 ? `brightness(${lerp(1, 0.3, dark).toFixed(3)}) blur(${(dark * 12).toFixed(2)}px)` : 'none'
  const sp = $$('#kWhy > span')
  const out = E.inQ(P(t, 5.62, 5.92))
  sp.forEach((s, i) => { const k = E.outC(P(t, 3.36 + i * 0.36, 3.8 + i * 0.36)); T(s, { y: (1 - k) * 34 - out * 20, op: k * (1 - out) }) })
  $('#strike').style.width = `${(E.ioC(P(t, 3.95, 4.25)) * 104).toFixed(2)}%`
}

function reveal(t) {
  const on = t >= 6.0 && t < 10.35
  scene($('#sReveal'), on)
  if (!on) return
  // "We bring to you…" over the darkened pizza
  const bin = E.outC(P(t, 6.48, 6.95)), bout = E.inQ(P(t, 7.8, 8.02))
  const bs = $('#bring span')
  T(bs, { y: (1 - bin) * 30, s: lerp(1, 1.06, P(t, 6.5, 8.0)), op: bin * (1 - bout) })
  $('#bring').style.display = t < 8.05 ? 'block' : 'none'
  // the cream opens from the centre on the downbeat
  const cream = $('#cream'), ik = E.inQ(P(t, 7.92, 8.12))
  cream.style.display = t >= 7.92 ? 'block' : 'none'
  cream.style.clipPath = ik < 1 ? `circle(${(ik * 1250).toFixed(1)}px at 540px 820px)` : 'none'
  const ex = E.ioC(P(t, 9.62, 10.3))
  cream.style.transform = `translateY(${(-ex * 1960).toFixed(1)}px)`
  // the logo settles, a light passes over it
  const lk = E.outC(P(t, 8.04, 8.62))
  T($('#logoBox'), { s: lerp(0.92, 1, lk) * lerp(1, 1.02, P(t, 8.6, 9.6)), op: lk })
  $('#sheen').style.backgroundPosition = `${lerp(140, -40, E.ioC(P(t, 8.88, 9.5))).toFixed(1)}% 0`
  const tg = E.outC(P(t, 8.7, 9.1))
  T($('#tag'), { y: (1 - tg) * 26, op: tg })
  const uk = E.outC(P(t, 8.98, 9.4))
  T($('#url'), { c: 'x', y: (1 - uk) * 26, op: uk })
}

function site(t, pend) {
  const on = t >= 9.55 && t < 24.3
  scene($('#sSite'), on)
  if (!on) return
  pend.push(setImg($('#rec'), recSrc(recIndexAt(t))))
  const [fx, fy, cx, cy, s] = camAt(t)
  $('#rig').style.transform = `translate(${(cx - fx * K * s).toFixed(2)}px,${(cy - fy * K * s).toFixed(2)}px) scale(${s.toFixed(4)})`
  T($('#siteBgImg'), { s: 1.12 + 0.04 * Math.sin(t * 0.25), x: Math.sin(t * 0.21) * 20 })

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

  // captions
  $$('#caps .cap').forEach((el, i) => {
    const [a, b] = CAPS[i]
    const k = E.outC(P(t, a, a + 0.35)), out = i === CAPS.length - 1 ? 0 : E.inQ(P(t, b - 0.12, b + 0.12))
    el.style.display = t >= a && t < b + 0.12 ? 'block' : 'none'
    T(el, { y: (1 - k) * 28 - out * 18, op: k * (1 - out) })
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
  const nk = E.outC(P(t, 24.12, 24.6))
  T($('.lh-n'), { s: lerp(1.1, 1, nk), op: nk })
  T($('.lh-s'), { y: (1 - E.outC(P(t, 24.6, 25.0))) * 24, op: P(t, 24.6, 24.9) })
  $$('.lr').forEach((r, i) => {
    const t0 = 25.0 + i * 0.5, rk = E.outC(P(t, t0 - 0.06, t0 + 0.4))
    T(r, { x: (1 - rk) * 90, op: rk })
  })
  const best = $('.lr.max'), bk = E.outC(P(t, 27.3, 27.7))
  best.style.boxShadow = `0 20px 40px rgba(0,0,0,0.3), 0 0 ${(70 * bk).toFixed(1)}px rgba(242,195,94,${(0.38 * bk).toFixed(3)})`
  const rb = E.outC(P(t, 28.6, 29.05))
  T($('#ribbon'), { c: 'x', y: (1 - rb) * 40, op: rb })
}

function promise(t, pend) {
  const on = t >= 31.78 && t < 36.3
  const sc = $('#sPromise')
  scene(sc, on)
  if (!on) return
  sc.style.opacity = E.outC(P(t, 31.78, 32.05)).toFixed(3)
  // the end of the pull in slow motion: frames 40-59 over four seconds, each blended into the next
  const pf = lerp(40, PULL_LAST, E.outQ(P(t, 31.78, 36.0)))
  const f0 = Math.floor(pf), f1 = Math.min(PULL_LAST, f0 + 1)
  pend.push(setImg($('#promA'), pullSrc(f0)), setImg($('#promB'), pullSrc(f1)))
  $('#promB').style.opacity = (pf - f0).toFixed(3)
  const push = E.outQ(P(t, 31.78, 36.3)), hp = hand(t)
  for (const id of ['#promA', '#promB']) T($(id), { s: lerp(1.03, 1.08, push), x: hp.x, y: 70 + hp.y })
  for (const [id, t0] of [['#pl1', 32.1], ['#pl2', 33.4], ['#pl3', 34.9]]) {
    const k = E.outC(P(t, t0, t0 + 0.42))
    T($(id), { x: (1 - k) * -40, op: k })
  }
  $('#pl3 u').style.setProperty('--u', `${(E.ioC(P(t, 35.35, 35.8)) * 100).toFixed(1)}%`)
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
  const lk = E.outC(P(t, 36.4, 36.95))
  T($('#ctaLogo'), { s: lerp(0.93, 1, lk), op: lk })
  T($('#ctaK'), { y: (1 - E.outC(P(t, 36.75, 37.1))) * 22, op: P(t, 36.75, 37.0) })
  const uk = E.outC(P(t, 36.85, 37.25))
  T($('#ctaUrl'), { c: 'x', y: (1 - uk) * 24, op: uk })
  const bk = E.outC(P(t, 37.3, 37.7))
  const pulse = t > 38.6 ? 1 + 0.018 * Math.sin((t - 38.6) * 4.2) : 1
  T($('#ctaBtn'), { c: 'x', y: (1 - bk) * 24, s: pulse, op: bk })
  $$('#ctaChips span').forEach((s, i) => { const k = E.outC(P(t, 38.1 + i * 0.15, 38.45 + i * 0.15)); T(s, { y: (1 - k) * 22, op: k }) })
  T($('#ctaFine'), { op: P(t, 40.6, 41.0) })
}

/* ------------------------------------------------------------------- seek */
window.seek = async function seek(t) {
  const pend = []
  hook(t, pend); problem(t, pend); reveal(t); site(t, pend); ladder(t); promise(t, pend); cta(t)

  steamCtx.clearRect(0, 0, 1080, 1920)
  steam(t, [140, 1180, 940, 1420, 520], 0.24 * (1 - P(t, 1.7, 2.3)))                 // off the pie, into the dark
  steam(t, [200, 1000, 880, 1200, 560], 0.3 * P(t, 3.3, 3.5) * (1 - P(t, 5.7, 6.2)))   // the whole pizza
  steam(t, [120, 1250, 960, 1450, 520], 0.26 * P(t, 31.9, 32.3) * (1 - P(t, 35.95, 36.2)))
  steam(t, [260, 1430, 820, 1560, 300], 0.13 * P(t, 36.6, 37.4))
  grain(t)
  const cream = (t >= 8.1 && t < 9.75) || t >= 36.2
  $('#vignette').style.opacity = cream ? '0.35' : '1'
  $('#grain').style.opacity = cream ? '0.045' : '0.065'
  await Promise.all(pend.filter(Boolean))
}

await init()
const q = new URLSearchParams(location.search)
if (q.has('t')) await window.seek(parseFloat(q.get('t')))
