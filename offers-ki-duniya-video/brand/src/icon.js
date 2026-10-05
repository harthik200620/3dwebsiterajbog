// Pizza-percent mark: a pizza split along "/" with one big topping in each half, so the
// whole pie reads as "%". Cheese strands stretch across the gap.
export function iconSVG({ size = 240, gap = 17, strands = true, flat = false } = {}) {
  const c = 120, R = 104
  const d = gap / 2 / Math.SQRT2
  const leaf = (x, y, r, rot) => `<path transform="translate(${x} ${y}) rotate(${rot})" d="M0 ${-r} C ${r * 0.9} ${-r * 0.4}, ${r * 0.9} ${r * 0.4}, 0 ${r} C ${-r * 0.9} ${r * 0.4}, ${-r * 0.9} ${-r * 0.4}, 0 ${-r} Z" fill="#2f9e57"/><path transform="translate(${x} ${y}) rotate(${rot})" d="M0 ${-r * 0.8} L0 ${r * 0.8}" stroke="#1f7a40" stroke-width="1.6" stroke-linecap="round"/>`
  const olive = (x, y) => `<circle cx="${x}" cy="${y}" r="6.2" fill="none" stroke="#2a201c" stroke-width="4.4"/>`
  const pep = (x, y, r) => `<g><circle cx="${x}" cy="${y}" r="${r}" fill="#c9302a"/><circle cx="${x}" cy="${y}" r="${r - 3.2}" fill="#e2453a"/>` +
    `<circle cx="${x - r * 0.32}" cy="${y - r * 0.34}" r="${r * 0.22}" fill="#f6836f" opacity=".8"/>` +
    [[0.3, 0.25], [-0.25, 0.35], [0.38, -0.18], [-0.05, -0.05]].map(([a, b]) => `<circle cx="${x + a * r}" cy="${y + b * r}" r="${r * 0.09}" fill="#a8231d" opacity=".75"/>`).join('') + `</g>`
  const pie = `
    <circle cx="${c}" cy="${c}" r="${R}" fill="url(#crust)"/>
    <circle cx="${c}" cy="${c}" r="${R - 1.5}" fill="none" stroke="#b9661f" stroke-width="3" opacity=".55"/>
    <circle cx="${c}" cy="${c}" r="${R - 13}" fill="#d94427"/>
    <path d="${scallop(c, c, R - 16.5, 18, 2.6)}" fill="url(#cheese)"/>
    ${[[-52, 18, 7], [-16, 50, 6], [22, -58, 6.5], [56, -12, 7], [-30, -66, 5], [64, 34, 5.5], [-70, -22, 5], [8, 72, 6]].map(([x, y, r]) => `<circle cx="${c + x}" cy="${c + y}" r="${r}" fill="#f5b638" opacity=".75"/>`).join('')}
    ${[[-58, -40], [40, 58], [-20, -78], [78, 20]].map(([x, y]) => `<circle cx="${c + x}" cy="${c + y}" r="3" fill="#fff4c9" opacity=".8"/>`).join('')}
    ${leaf(c - 62, c + 20, 9, 30)} ${leaf(c + 18, c - 66, 8.5, -60)} ${leaf(c + 64, c - 8, 9, 75)} ${leaf(c - 8, c + 66, 8.5, 140)}
    ${olive(c - 26, c - 70)} ${olive(c + 70, c + 30)} ${olive(c - 72, c - 8)} ${olive(c + 26, c + 70)}
    ${pep(c - 41, c - 41, 21)} ${pep(c + 41, c + 41, 21)}
  `
  // halves: upper-left keeps x+y < 2c, lower-right x+y > 2c
  // Melted cheese stretched across the cut: thick where it leaves each half, thin in the
  // middle, and sagging down the way a real pull does.
  const strand = (o, w, sag) => {
    const px = c + o / Math.SQRT2, py = c - o / Math.SQRT2          // point on the cut line
    const nx = 1 / Math.SQRT2, ny = 1 / Math.SQRT2                   // across the gap
    const tx = 1 / Math.SQRT2, ty = -1 / Math.SQRT2                  // along the cut
    const h = d + 4.5                                                // reach into each half
    const A = [px - nx * h, py - ny * h], B = [px + nx * h, py + ny * h]
    const M = [px, py + sag]                                          // sag straight down
    const at = (P, k) => [P[0] + tx * k, P[1] + ty * k]
    const a1 = at(A, w), a2 = at(A, -w), b1 = at(B, w), b2 = at(B, -w)
    const m1 = at(M, w * 0.3), m2 = at(M, -w * 0.3)
    const f = (P) => P.map((v) => v.toFixed(2)).join(' ')
    const body = `M${f(a1)} Q ${f(m1)} ${f(b1)} L ${f(b2)} Q ${f(m2)} ${f(a2)} Z`
    const hi = `M${f(at(A, w * 0.45))} Q ${f(at(M, w * 0.12))} ${f(at(B, w * 0.45))}`
    return `<path d="${body}" fill="#ffcf4f" stroke="#f0a92e" stroke-width="1.1" stroke-linejoin="round"/>` +
      `<path d="${hi}" stroke="#fff3c4" stroke-width="${(w * 0.35).toFixed(2)}" stroke-linecap="round" fill="none" opacity=".85"/>`
  }
  const strandsSVG = !strands ? '' : strand(-38, 4.2, 7) + strand(6, 3.4, 9) + strand(46, 3.0, 6)
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240" width="${size}" height="${size}">
  <defs>
    <radialGradient id="crust" cx="45%" cy="40%" r="62%"><stop offset="0" stop-color="#f7c46c"/><stop offset=".72" stop-color="#e99a3c"/><stop offset="1" stop-color="#c8701f"/></radialGradient>
    <radialGradient id="cheese" cx="40%" cy="36%" r="70%"><stop offset="0" stop-color="#ffe9a6"/><stop offset=".55" stop-color="#ffd05a"/><stop offset="1" stop-color="#f7b733"/></radialGradient>
    <clipPath id="ul"><path d="M0 0 H240 L0 240 Z"/></clipPath>
    <clipPath id="lr"><path d="M240 0 V240 H0 Z"/></clipPath>
  </defs>
  <g transform="translate(${-d} ${-d})"><g clip-path="url(#ul)">${pie}</g></g>
  <g transform="translate(${d} ${d})"><g clip-path="url(#lr)">${pie}</g></g>
  ${strandsSVG}
</svg>`
}
function scallop(cx, cy, r, n, amp) {
  let s = ''
  for (let i = 0; i <= 240; i++) {
    const a = (i / 240) * Math.PI * 2
    const rr = r + amp * Math.sin(a * n) + amp * 0.5 * Math.sin(a * 7 + 1)
    s += (i ? 'L' : 'M') + (cx + Math.cos(a) * rr).toFixed(2) + ' ' + (cy + Math.sin(a) * rr).toFixed(2)
  }
  return s + 'Z'
}
