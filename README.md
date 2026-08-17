# Raajbhog

A cinematic, scroll-driven website for a fictional fine-dining Indian restaurant set opposite Main Gate, IIT Kharagpur.

**Khaana nahi. Daawat.**

## What it is

A single-page site built as plain HTML, CSS, and vanilla JavaScript. No frameworks, no build step, no dependencies. Open `index.html` through any static server and it runs.

## Features

- **Scroll-scrubbed hero film.** An AI-generated shot of a dum biryani handi being unsealed, driven frame by frame by the scroll position: forward as you scroll down, backward as you scroll up. The video is fetched as a Blob behind a progress ring, and every seek is gated so they never overlap.
- **Static hero fallback.** Phones, reduced-motion users, slow connections, and `file://` previews get a fully designed still hero instead. The page is complete and beautiful even if the video never loads.
- **Auto-scrolling signature rail.** The house favourites drift past continuously and pause on hover.
- **Full menu, 28 dishes.** Filterable by course, grouped under gold course labels, with a spotlight banner for the house speciality.
- **Working cart.** Add from anywhere, quantity chips stay in sync across the page, dish photos fly into the cart button, and the order confirms with a sealed-handi animation. State persists in `localStorage`.
- **Interactive campus delivery map.** Pick your hall and a gold route draws itself from Main Gate with a delivery time.
- **Motion throughout.** 3D pointer tilt with glare on cards, magnetic buttons, word-by-word masked headline reveals, scroll parallax, animated counters, and self-drawing SVG. All of it honours `prefers-reduced-motion`.

## Running it locally

```bash
npx -y http-server . -p 8317 -c-1
```

Then open <http://localhost:8317>.

A plain double-click on `index.html` also works, but browsers block `fetch` on `file://` URLs, so you will see the static hero rather than the scrubbing film.

## Structure

```
index.html          the entire site: markup, styles, and script
assets/
  hero-scrub.mp4    the scroll-driven hero film
  hero-poster.jpg   first frame, shown while the film loads
  hero-ending.jpg   final frame, reused as a design image
  img/              menu photography
```

## A note on the content

Raajbhog is a fictional restaurant, created as a design piece. The address and hall names reference the real IIT Kharagpur campus, but the business, its menu, and its prices are invented. The hero film is AI generated.
