// Procedural food art. Every image is drawn from a seed, so a render is
// repeatable frame for frame and nothing depends on a remote image host.

export function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const TAU = Math.PI * 2

// A circle with a hand-made wobble: a few low harmonics with random phase.
function blob(ctx, cx, cy, r, rnd, amp = 0.03) {
  const ph = [0, 1, 2, 3].map(() => rnd() * TAU)
  const fr = [3, 5, 8, 13]
  const am = [amp, amp * 0.55, amp * 0.35, amp * 0.2]
  ctx.beginPath()
  for (let i = 0; i <= 200; i++) {
    const a = (i / 200) * TAU
    let k = 1
    for (let j = 0; j < 4; j++) k += am[j] * Math.sin(fr[j] * a + ph[j])
    const x = cx + Math.cos(a) * r * k, y = cy + Math.sin(a) * r * k
    i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)
  }
  ctx.closePath()
}

function rrect(ctx, x, y, w, h, r) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}

// Dart-throwing Poisson sampling inside a disc.
function scatter(rnd, R, minD, tries = 3000) {
  const pts = []
  for (let i = 0; i < tries; i++) {
    const a = rnd() * TAU, r = Math.sqrt(rnd()) * R
    const x = Math.cos(a) * r, y = Math.sin(a) * r
    if (pts.every((p) => (p.x - x) ** 2 + (p.y - y) ** 2 > minD * minD)) pts.push({ x, y })
  }
  return pts
}

/* ---------------------------------------------------------------- toppings */

const T = {
  capsicum(ctx, u, rnd) {
    const rad = u * (1.2 + rnd() * 0.9), half = (u * (0.9 + rnd() * 0.5)) / rad
    const arc = (w, col, dy = 0) => {
      ctx.strokeStyle = col; ctx.lineWidth = w
      ctx.beginPath(); ctx.arc(0, rad + dy, rad, -Math.PI / 2 - half, -Math.PI / 2 + half); ctx.stroke()
    }
    ctx.lineCap = 'round'
    arc(u * 0.44, '#245f22')
    arc(u * 0.3, '#3f9431')
    ctx.shadowColor = 'transparent'
    arc(u * 0.09, 'rgba(214,255,170,0.65)', u * 0.06)
  },
  onion(ctx, u, rnd) {
    const rad = u * (0.9 + rnd() * 0.7), half = (u * (0.8 + rnd() * 0.6)) / rad
    ctx.lineCap = 'round'
    const ring = (r, w, col) => {
      ctx.strokeStyle = col; ctx.lineWidth = w
      ctx.beginPath(); ctx.arc(0, rad, r, -Math.PI / 2 - half, -Math.PI / 2 + half); ctx.stroke()
    }
    ring(rad, u * 0.2, '#8f3f80')
    ctx.shadowColor = 'transparent'
    ring(rad - u * 0.02, u * 0.09, '#f3dcef')
    if (rnd() < 0.5) { ring(rad - u * 0.28, u * 0.15, '#a35093'); ring(rad - u * 0.3, u * 0.06, '#f6e6f2') }
  },
  tomato(ctx, u, rnd) {
    const r = u * (0.7 + rnd() * 0.15)
    ctx.fillStyle = '#b8261a'
    ctx.beginPath(); ctx.arc(0, 0, r, Math.PI, TAU); ctx.closePath(); ctx.fill()
    ctx.shadowColor = 'transparent'
    ctx.fillStyle = '#e04a33'
    ctx.beginPath(); ctx.arc(0, -u * 0.02, r * 0.82, Math.PI, TAU); ctx.closePath(); ctx.fill()
    for (const s of [-0.42, 0, 0.42]) {
      ctx.fillStyle = '#f2876a'
      ctx.beginPath(); ctx.ellipse(s * r, -r * 0.38, r * 0.19, r * 0.26, 0, 0, TAU); ctx.fill()
      ctx.fillStyle = '#f7d77e'
      ctx.beginPath(); ctx.ellipse(s * r, -r * 0.38, r * 0.06, r * 0.1, 0, 0, TAU); ctx.fill()
    }
    ctx.strokeStyle = 'rgba(255,220,200,0.5)'; ctx.lineWidth = u * 0.05
    ctx.beginPath(); ctx.arc(0, 0, r * 0.93, Math.PI * 1.15, Math.PI * 1.55); ctx.stroke()
  },
  mushroom(ctx, u) {
    ctx.fillStyle = '#c9a77c'
    ctx.beginPath()
    ctx.moveTo(-u * 0.85, u * 0.05)
    ctx.bezierCurveTo(-u * 0.85, -u * 0.95, u * 0.85, -u * 0.95, u * 0.85, u * 0.05)
    ctx.lineTo(u * 0.28, u * 0.05)
    ctx.lineTo(u * 0.24, u * 0.62)
    ctx.quadraticCurveTo(0, u * 0.78, -u * 0.24, u * 0.62)
    ctx.lineTo(-u * 0.28, u * 0.05)
    ctx.closePath(); ctx.fill()
    ctx.shadowColor = 'transparent'
    ctx.strokeStyle = '#9c7b55'; ctx.lineWidth = u * 0.09; ctx.stroke()
    ctx.strokeStyle = 'rgba(150,118,80,0.55)'; ctx.lineWidth = u * 0.045
    for (let i = -2; i <= 2; i++) {
      ctx.beginPath(); ctx.moveTo(i * u * 0.08, u * 0.02); ctx.lineTo(i * u * 0.3, -u * 0.45); ctx.stroke()
    }
    ctx.fillStyle = 'rgba(255,248,230,0.45)'
    ctx.beginPath(); ctx.ellipse(-u * 0.3, -u * 0.42, u * 0.22, u * 0.09, -0.5, 0, TAU); ctx.fill()
  },
  paneer(ctx, u, rnd) {
    const w = u * (0.85 + rnd() * 0.2)
    const g = ctx.createLinearGradient(-w / 2, -w / 2, w / 2, w / 2)
    g.addColorStop(0, '#fffaf0'); g.addColorStop(1, '#f1dcb6')
    ctx.fillStyle = g
    rrect(ctx, -w / 2, -w / 2, w, w, u * 0.14); ctx.fill()
    ctx.shadowColor = 'transparent'
    ctx.strokeStyle = 'rgba(150,90,30,0.5)'; ctx.lineWidth = u * 0.05; ctx.stroke()
    ctx.save(); rrect(ctx, -w / 2, -w / 2, w, w, u * 0.14); ctx.clip()
    for (const [cx, cy] of [[w / 2, w / 2], [-w / 2, w / 2 * (rnd() - 0.5)], [w * (rnd() - 0.5), -w / 2]]) {
      const rg = ctx.createRadialGradient(cx, cy, 0, cx, cy, w * 0.55)
      rg.addColorStop(0, 'rgba(184,96,28,0.9)'); rg.addColorStop(1, 'rgba(196,112,38,0)')
      ctx.fillStyle = rg; ctx.fillRect(-w, -w, w * 2, w * 2)
    }
    ctx.strokeStyle = 'rgba(120,60,20,0.45)'; ctx.lineWidth = u * 0.08
    ctx.beginPath(); ctx.moveTo(-w * 0.6, -w * 0.1); ctx.lineTo(w * 0.2, w * 0.6); ctx.stroke()
    ctx.restore()
  },
  corn(ctx, u, rnd) {
    const n = 3 + ((rnd() * 2) | 0)
    for (let i = 0; i < n; i++) {
      const x = (i - (n - 1) / 2) * u * 0.42 + (rnd() - 0.5) * u * 0.1, y = (rnd() - 0.5) * u * 0.5
      const g = ctx.createLinearGradient(x, y - u * 0.2, x, y + u * 0.2)
      g.addColorStop(0, '#ffd23f'); g.addColorStop(1, '#d98a00')
      ctx.fillStyle = g
      rrect(ctx, x - u * 0.2, y - u * 0.17, u * 0.4, u * 0.34, u * 0.13); ctx.fill()
      ctx.strokeStyle = 'rgba(150,80,0,0.55)'; ctx.lineWidth = u * 0.04; ctx.stroke()
      ctx.save(); ctx.shadowColor = 'transparent'
      ctx.fillStyle = 'rgba(255,255,255,0.7)'
      ctx.beginPath(); ctx.ellipse(x - u * 0.06, y - u * 0.07, u * 0.07, u * 0.04, 0, 0, TAU); ctx.fill()
      ctx.restore()
    }
  },
  olive(ctx, u) {
    ctx.strokeStyle = '#1d1918'; ctx.lineWidth = u * 0.28
    ctx.beginPath(); ctx.arc(0, 0, u * 0.4, 0, TAU); ctx.stroke()
    ctx.shadowColor = 'transparent'
    ctx.strokeStyle = 'rgba(255,255,255,0.28)'; ctx.lineWidth = u * 0.06
    ctx.beginPath(); ctx.arc(0, 0, u * 0.45, Math.PI * 1.1, Math.PI * 1.5); ctx.stroke()
  },
  jalapeno(ctx, u, rnd) {
    ctx.fillStyle = '#2f6b20'
    ctx.beginPath(); ctx.arc(0, 0, u * 0.5, 0, TAU); ctx.fill()
    ctx.shadowColor = 'transparent'
    ctx.fillStyle = '#c9dd94'
    ctx.beginPath(); ctx.arc(0, 0, u * 0.36, 0, TAU); ctx.fill()
    ctx.fillStyle = '#f4f1cf'
    for (let i = 0; i < 4; i++) {
      const a = rnd() * TAU
      ctx.beginPath(); ctx.ellipse(Math.cos(a) * u * 0.14, Math.sin(a) * u * 0.14, u * 0.07, u * 0.045, a, 0, TAU); ctx.fill()
    }
    ctx.strokeStyle = 'rgba(255,255,255,0.3)'; ctx.lineWidth = u * 0.05
    ctx.beginPath(); ctx.arc(0, 0, u * 0.44, Math.PI * 1.1, Math.PI * 1.5); ctx.stroke()
  },
  paprika(ctx, u, rnd) {
    const rad = u * (0.8 + rnd() * 0.5), half = (u * 0.7) / rad
    ctx.lineCap = 'round'
    ctx.strokeStyle = '#a5170f'; ctx.lineWidth = u * 0.26
    ctx.beginPath(); ctx.arc(0, rad, rad, -Math.PI / 2 - half, -Math.PI / 2 + half); ctx.stroke()
    ctx.shadowColor = 'transparent'
    ctx.strokeStyle = '#e8503c'; ctx.lineWidth = u * 0.09
    ctx.beginPath(); ctx.arc(0, rad + u * 0.03, rad, -Math.PI / 2 - half * 0.8, -Math.PI / 2 + half * 0.8); ctx.stroke()
  },
  chicken(ctx, u, rnd) {
    const g = ctx.createRadialGradient(-u * 0.1, -u * 0.1, 0, 0, 0, u * 0.7)
    g.addColorStop(0, '#d79a5d'); g.addColorStop(1, '#8a4a20')
    ctx.fillStyle = g
    blob(ctx, 0, 0, u * 0.55, rnd, 0.14); ctx.fill()
    ctx.shadowColor = 'transparent'
    ctx.strokeStyle = 'rgba(70,35,10,0.6)'; ctx.lineWidth = u * 0.08
    for (const k of [-0.2, 0.15]) { ctx.beginPath(); ctx.moveTo(-u * 0.4, k * u); ctx.lineTo(u * 0.4, k * u - u * 0.2); ctx.stroke() }
  },
}

/* ------------------------------------------------------------------- pizza */

export const RECIPES = {
  vegx: { mix: [['olive', 3], ['onion', 3], ['capsicum', 3], ['mushroom', 2], ['corn', 3], ['tomato', 2], ['jalapeno', 2]], minD: 0.135 },
  peppy: { mix: [['paneer', 5], ['capsicum', 3], ['paprika', 3]], minD: 0.145 },
  farm: { mix: [['onion', 3], ['capsicum', 3], ['tomato', 2], ['mushroom', 3]], minD: 0.145 },
  marg: { mix: [], minD: 0.2, extraCheese: true },
  mexi: { mix: [['onion', 3], ['capsicum', 3], ['tomato', 2], ['jalapeno', 3]], minD: 0.145 },
  chick: { mix: [['chicken', 5], ['onion', 3], ['capsicum', 2]], minD: 0.15 },
  corn: { mix: [['corn', 1]], minD: 0.12, extraCheese: true },
}

export function pizza(kind, px = 900, seed = 7) {
  const recipe = RECIPES[kind]
  const c = document.createElement('canvas')
  c.width = c.height = px
  const ctx = c.getContext('2d')
  const rnd = mulberry32(seed * 7919 + kind.charCodeAt(0) * 131 + kind.length)
  const R = px * 0.455
  ctx.translate(px / 2, px / 2)

  // contact shadow
  ctx.save()
  ctx.shadowColor = 'rgba(0,0,0,0.5)'; ctx.shadowBlur = px * 0.035; ctx.shadowOffsetY = px * 0.016
  blob(ctx, 0, 0, R, rnd, 0.008); ctx.fillStyle = '#b8732f'; ctx.fill()
  ctx.restore()

  // crust
  blob(ctx, 0, 0, R, rnd, 0.008)
  let g = ctx.createRadialGradient(-R * 0.14, -R * 0.18, R * 0.55, 0, 0, R * 1.02)
  g.addColorStop(0, '#f6d394'); g.addColorStop(0.55, '#eeb565'); g.addColorStop(0.8, '#d98f44'); g.addColorStop(1, '#9f5a23')
  ctx.fillStyle = g; ctx.fill()
  ctx.save(); ctx.clip()
  ctx.filter = `blur(${px * 0.006}px)`
  ctx.strokeStyle = 'rgba(255,232,180,0.45)'; ctx.lineWidth = R * 0.045
  ctx.beginPath(); ctx.arc(-R * 0.01, -R * 0.015, R * 0.925, Math.PI * 0.95, Math.PI * 1.85); ctx.stroke()
  ctx.filter = 'none'
  for (let i = 0; i < 260; i++) {
    const a = rnd() * TAU, rr = R * (0.865 + rnd() * 0.13), s = R * (0.004 + rnd() * 0.017)
    ctx.fillStyle = `rgba(${(105 + rnd() * 45) | 0},${(52 + rnd() * 25) | 0},${(16 + rnd() * 14) | 0},${0.12 + rnd() * 0.38})`
    ctx.beginPath(); ctx.ellipse(Math.cos(a) * rr, Math.sin(a) * rr, s * 1.7, s, a, 0, TAU); ctx.fill()
  }
  for (let i = 0; i < 140; i++) {
    const a = rnd() * TAU, rr = R * (0.87 + rnd() * 0.1), s = R * (0.002 + rnd() * 0.005)
    ctx.fillStyle = `rgba(255,243,214,${0.25 + rnd() * 0.35})`
    ctx.beginPath(); ctx.arc(Math.cos(a) * rr, Math.sin(a) * rr, s, 0, TAU); ctx.fill()
  }
  ctx.restore()

  // sauce
  blob(ctx, 0, 0, R * 0.882, rnd, 0.012)
  g = ctx.createRadialGradient(0, 0, R * 0.6, 0, 0, R * 0.9)
  g.addColorStop(0, '#c43a20'); g.addColorStop(1, '#8e2112')
  ctx.fillStyle = g; ctx.fill()
  ctx.strokeStyle = 'rgba(70,15,5,0.5)'; ctx.lineWidth = R * 0.012; ctx.stroke()

  // cheese
  const RC = R * 0.845
  blob(ctx, 0, 0, RC, rnd, 0.035)
  g = ctx.createRadialGradient(-R * 0.18, -R * 0.2, R * 0.05, 0, 0, RC)
  g.addColorStop(0, '#ffeeb0'); g.addColorStop(0.5, '#f8cf6a'); g.addColorStop(1, '#e8a43c')
  ctx.fillStyle = g; ctx.fill()
  ctx.save(); ctx.clip()
  for (let i = 0; i < 150; i++) {
    const a = rnd() * TAU, r = Math.sqrt(rnd()) * RC, s = R * (0.02 + rnd() * 0.06)
    ctx.fillStyle = `rgba(255,249,222,${0.18 + rnd() * 0.25})`
    blob(ctx, Math.cos(a) * r, Math.sin(a) * r, s, rnd, 0.15); ctx.fill()
  }
  const blisters = recipe.extraCheese ? 170 : 110
  for (let i = 0; i < blisters; i++) {
    const a = rnd() * TAU, r = Math.sqrt(rnd()) * RC * 0.98, s = R * (0.012 + rnd() * 0.04)
    const x = Math.cos(a) * r, y = Math.sin(a) * r
    const rg = ctx.createRadialGradient(x, y, 0, x, y, s)
    rg.addColorStop(0, `rgba(160,80,18,${0.55 + rnd() * 0.35})`); rg.addColorStop(0.5, 'rgba(210,128,40,0.42)'); rg.addColorStop(1, 'rgba(214,138,48,0)')
    ctx.fillStyle = rg; ctx.beginPath(); ctx.arc(x, y, s, 0, TAU); ctx.fill()
  }
  for (let i = 0; i < 26; i++) {
    const a = rnd() * TAU, r = Math.sqrt(rnd()) * RC * 0.95, s = R * (0.008 + rnd() * 0.018)
    ctx.fillStyle = 'rgba(190,60,28,0.42)'
    blob(ctx, Math.cos(a) * r, Math.sin(a) * r, s, rnd, 0.2); ctx.fill()
  }
  for (let i = 0; i < 70; i++) {
    const a = rnd() * TAU, r = Math.sqrt(rnd()) * RC * 0.95, s = R * (0.006 + rnd() * 0.014)
    ctx.fillStyle = `rgba(255,255,245,${0.35 + rnd() * 0.35})`
    ctx.beginPath(); ctx.ellipse(Math.cos(a) * r, Math.sin(a) * r, s * 1.6, s, rnd() * TAU, 0, TAU); ctx.fill()
  }
  ctx.restore()

  // toppings
  // Weights, not counts: every scattered spot gets a topping, picked by weight.
  const pts = recipe.mix.length ? scatter(rnd, R * 0.74, R * recipe.minD) : []
  const total = recipe.mix.reduce((a, [, w]) => a + w, 0)
  const bag = pts.map(() => {
    let r = rnd() * total
    for (const [k, w] of recipe.mix) { if ((r -= w) <= 0) return k }
    return recipe.mix[0][0]
  })
  const u = R * 0.1
  pts.forEach((p, i) => {
    ctx.save()
    ctx.translate(p.x, p.y); ctx.rotate(rnd() * TAU)
    ctx.shadowColor = 'rgba(80,32,0,0.42)'; ctx.shadowBlur = u * 0.45; ctx.shadowOffsetY = u * 0.14
    T[bag[i]](ctx, u * (0.92 + rnd() * 0.18), rnd)
    ctx.restore()
  })

  // oregano
  for (let i = 0; i < 260; i++) {
    const a = rnd() * TAU, r = Math.sqrt(rnd()) * RC * 0.95, s = R * (0.003 + rnd() * 0.006)
    ctx.fillStyle = rnd() < 0.6 ? 'rgba(52,78,24,0.85)' : 'rgba(110,138,46,0.85)'
    ctx.save(); ctx.translate(Math.cos(a) * r, Math.sin(a) * r); ctx.rotate(rnd() * TAU)
    ctx.fillRect(-s, -s * 0.5, s * 2, s); ctx.restore()
  }

  // slice cuts
  const off = rnd() * TAU
  for (let i = 0; i < 8; i++) {
    const a = off + (i / 8) * TAU
    ctx.strokeStyle = 'rgba(100,45,10,0.3)'; ctx.lineWidth = R * 0.009
    ctx.beginPath(); ctx.moveTo(Math.cos(a) * R * 0.04, Math.sin(a) * R * 0.04); ctx.lineTo(Math.cos(a) * R * 0.88, Math.sin(a) * R * 0.88); ctx.stroke()
    ctx.strokeStyle = 'rgba(255,236,190,0.2)'; ctx.lineWidth = R * 0.004
    ctx.beginPath(); ctx.moveTo(Math.cos(a + 0.006) * R * 0.05, Math.sin(a + 0.006) * R * 0.05); ctx.lineTo(Math.cos(a + 0.006) * R * 0.87, Math.sin(a + 0.006) * R * 0.87); ctx.stroke()
  }

  // soft key light from top-left
  g = ctx.createRadialGradient(-R * 0.38, -R * 0.42, 0, -R * 0.2, -R * 0.2, R * 1.1)
  g.addColorStop(0, 'rgba(255,255,255,0.16)'); g.addColorStop(1, 'rgba(255,255,255,0)')
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, 0, R, 0, TAU); ctx.fill()
  return c
}

/* ----------------------------------------------------------- garlic sticks */

export function breadsticks(px = 900, seed = 3) {
  const c = document.createElement('canvas'); c.width = c.height = px
  const ctx = c.getContext('2d'); const rnd = mulberry32(seed * 104729)
  ctx.translate(px / 2, px / 2)
  // plate
  ctx.save(); ctx.shadowColor = 'rgba(0,0,0,0.35)'; ctx.shadowBlur = px * 0.03; ctx.shadowOffsetY = px * 0.012
  let g = ctx.createRadialGradient(-px * 0.1, -px * 0.12, px * 0.05, 0, 0, px * 0.46)
  g.addColorStop(0, '#fffaf1'); g.addColorStop(1, '#e7d7bd')
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, 0, px * 0.455, 0, TAU); ctx.fill(); ctx.restore()
  ctx.strokeStyle = 'rgba(120,90,50,0.12)'; ctx.lineWidth = px * 0.006
  ctx.beginPath(); ctx.arc(0, 0, px * 0.38, 0, TAU); ctx.stroke()
  // parchment
  ctx.save(); ctx.rotate(-0.18)
  ctx.fillStyle = '#f2e1bf'; rrect(ctx, -px * 0.3, -px * 0.33, px * 0.6, px * 0.62, px * 0.02); ctx.fill()
  for (let i = 0; i < 9; i++) {
    const x = (rnd() - 0.5) * px * 0.5, y = (rnd() - 0.5) * px * 0.5
    ctx.fillStyle = 'rgba(214,170,90,0.22)'; blob(ctx, x, y, px * (0.015 + rnd() * 0.03), rnd, 0.2); ctx.fill()
  }
  ctx.restore()
  // sticks
  const n = 6
  for (let i = 0; i < n; i++) {
    ctx.save()
    const x = (i - (n - 1) / 2) * px * 0.082
    ctx.translate(x, (rnd() - 0.5) * px * 0.03); ctx.rotate(-0.18 + (rnd() - 0.5) * 0.06)
    const L = px * (0.56 + rnd() * 0.04), W = px * 0.072
    ctx.shadowColor = 'rgba(90,45,10,0.4)'; ctx.shadowBlur = px * 0.012; ctx.shadowOffsetY = px * 0.006
    g = ctx.createLinearGradient(-W / 2, 0, W / 2, 0)
    g.addColorStop(0, '#b9722c'); g.addColorStop(0.35, '#f0c27a'); g.addColorStop(0.65, '#e6ad5f'); g.addColorStop(1, '#a8621f')
    ctx.fillStyle = g; rrect(ctx, -W / 2, -L / 2, W, L, W * 0.48); ctx.fill()
    ctx.shadowColor = 'transparent'
    ctx.save(); rrect(ctx, -W / 2, -L / 2, W, L, W * 0.48); ctx.clip()
    for (let k = 0; k < 10; k++) {
      const yy = (rnd() - 0.5) * L, s = W * (0.15 + rnd() * 0.3)
      const rg = ctx.createRadialGradient(0, yy, 0, 0, yy, s)
      rg.addColorStop(0, 'rgba(150,80,20,0.45)'); rg.addColorStop(1, 'rgba(150,80,20,0)')
      ctx.fillStyle = rg; ctx.fillRect(-W, yy - s, W * 2, s * 2)
    }
    ctx.strokeStyle = 'rgba(255,246,214,0.55)'; ctx.lineWidth = W * 0.12
    ctx.beginPath(); ctx.moveTo(-W * 0.12, -L * 0.42); ctx.lineTo(-W * 0.12, L * 0.42); ctx.stroke()
    for (let k = 0; k < 26; k++) {
      ctx.fillStyle = rnd() < 0.55 ? 'rgba(58,96,30,0.9)' : 'rgba(255,250,232,0.9)'
      const s = W * (0.04 + rnd() * 0.05)
      ctx.fillRect((rnd() - 0.5) * W * 0.8, (rnd() - 0.5) * L * 0.9, s, s)
    }
    ctx.restore(); ctx.restore()
  }
  // dip
  ctx.save(); ctx.translate(px * 0.27, px * 0.27)
  ctx.shadowColor = 'rgba(0,0,0,0.35)'; ctx.shadowBlur = px * 0.02; ctx.shadowOffsetY = px * 0.01
  ctx.fillStyle = '#fbf7ef'; ctx.beginPath(); ctx.arc(0, 0, px * 0.11, 0, TAU); ctx.fill()
  ctx.shadowColor = 'transparent'
  g = ctx.createRadialGradient(-px * 0.02, -px * 0.02, 0, 0, 0, px * 0.085)
  g.addColorStop(0, '#ffe58a'); g.addColorStop(1, '#eeb02b')
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, 0, px * 0.085, 0, TAU); ctx.fill()
  ctx.fillStyle = 'rgba(255,255,255,0.6)'; ctx.beginPath(); ctx.ellipse(-px * 0.03, -px * 0.035, px * 0.03, px * 0.012, -0.6, 0, TAU); ctx.fill()
  ctx.restore()
  return c
}

/* -------------------------------------------------------------- lava cake */

export function lavaCake(px = 900, seed = 5) {
  const c = document.createElement('canvas'); c.width = c.height = px
  const ctx = c.getContext('2d'); const rnd = mulberry32(seed * 15485863)
  ctx.translate(px / 2, px / 2)
  // plate
  ctx.save(); ctx.shadowColor = 'rgba(0,0,0,0.35)'; ctx.shadowBlur = px * 0.03; ctx.shadowOffsetY = px * 0.014
  let g = ctx.createRadialGradient(-px * 0.1, -px * 0.12, px * 0.05, 0, 0, px * 0.46)
  g.addColorStop(0, '#fffaf2'); g.addColorStop(1, '#e6d6bd')
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, 0, px * 0.455, 0, TAU); ctx.fill(); ctx.restore()
  ctx.strokeStyle = 'rgba(120,90,50,0.12)'; ctx.lineWidth = px * 0.006
  ctx.beginPath(); ctx.arc(0, 0, px * 0.38, 0, TAU); ctx.stroke()

  const R = px * 0.25, a0 = -0.35, a1 = 0.42   // the wedge that has been cut out
  // molten pool spilling out of the cut
  g = ctx.createRadialGradient(R * 0.9, R * 0.1, 0, R * 0.9, R * 0.1, R * 0.95)
  g.addColorStop(0, '#6b2e10'); g.addColorStop(0.6, '#4a1d08'); g.addColorStop(1, '#2d0f04')
  ctx.fillStyle = g
  blob(ctx, R * 0.95, R * 0.08, R * 0.62, rnd, 0.09); ctx.fill()
  ctx.fillStyle = 'rgba(255,200,150,0.35)'
  ctx.beginPath(); ctx.ellipse(R * 0.8, -R * 0.12, R * 0.22, R * 0.05, -0.3, 0, TAU); ctx.fill()
  ctx.beginPath(); ctx.ellipse(R * 1.15, R * 0.25, R * 0.12, R * 0.035, 0.4, 0, TAU); ctx.fill()

  // cake with the wedge removed
  ctx.save()
  ctx.beginPath(); ctx.moveTo(0, 0); ctx.arc(0, 0, R, a1, a0 + TAU); ctx.closePath()
  ctx.shadowColor = 'rgba(30,10,2,0.55)'; ctx.shadowBlur = px * 0.03; ctx.shadowOffsetY = px * 0.012
  g = ctx.createRadialGradient(-R * 0.35, -R * 0.4, R * 0.1, 0, 0, R)
  g.addColorStop(0, '#7a3b1c'); g.addColorStop(0.7, '#43190a'); g.addColorStop(1, '#250c03')
  ctx.fillStyle = g; ctx.fill()
  ctx.clip()
  ctx.shadowColor = 'transparent'
  ctx.strokeStyle = 'rgba(15,4,1,0.65)'; ctx.lineWidth = px * 0.004
  for (let i = 0; i < 12; i++) {
    let x = (rnd() - 0.5) * R * 1.6, y = (rnd() - 0.5) * R * 1.6
    ctx.beginPath(); ctx.moveTo(x, y)
    for (let k = 0; k < 4; k++) { x += (rnd() - 0.5) * R * 0.3; y += (rnd() - 0.5) * R * 0.3; ctx.lineTo(x, y) }
    ctx.stroke()
  }
  for (let i = 0; i < 900; i++) {
    const a = rnd() * TAU, r = Math.sqrt(rnd()) * R
    ctx.fillStyle = `rgba(255,255,255,${0.3 + rnd() * 0.55})`
    const s = px * (0.002 + rnd() * 0.003)
    ctx.fillRect(Math.cos(a) * r, Math.sin(a) * r, s, s)
  }
  ctx.restore()
  // molten centre visible in the cut
  ctx.save()
  ctx.beginPath(); ctx.moveTo(0, 0); ctx.arc(0, 0, R * 0.98, a0, a1); ctx.closePath(); ctx.clip()
  g = ctx.createRadialGradient(R * 0.2, 0, 0, R * 0.2, 0, R)
  g.addColorStop(0, '#8a3f17'); g.addColorStop(0.5, '#5a230b'); g.addColorStop(1, '#3a1305')
  ctx.fillStyle = g; ctx.fillRect(-R, -R, R * 2, R * 2)
  ctx.strokeStyle = 'rgba(255,190,140,0.4)'; ctx.lineWidth = px * 0.006; ctx.lineCap = 'round'
  ctx.beginPath(); ctx.moveTo(R * 0.15, -R * 0.06); ctx.quadraticCurveTo(R * 0.5, -R * 0.12, R * 0.9, -R * 0.02); ctx.stroke()
  ctx.restore()
  // cut edges
  ctx.strokeStyle = 'rgba(30,10,3,0.9)'; ctx.lineWidth = px * 0.008
  ctx.beginPath(); ctx.moveTo(Math.cos(a0) * R, Math.sin(a0) * R); ctx.lineTo(0, 0); ctx.lineTo(Math.cos(a1) * R, Math.sin(a1) * R); ctx.stroke()
  return c
}

export function toURL(canvas) { return canvas.toDataURL('image/png') }
