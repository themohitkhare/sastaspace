# SastaSpace / Mohit Khare — Brand Guide

> One visual system, two surfaces. `sastaspace.com` is the lab. `mohitkhare.com` (or the About page) is the person. Same type, same palette, same voice.

**Owner:** Mohit Khare · Software Engineer 2, Demandbase
**Last updated:** 2026-04-23
**Version:** 1.0

---

## 1. Positioning

### What SastaSpace is
A lab. A personal workshop on the open internet where Mohit builds the things he wants to build — and puts them up where anyone can use them. Each project lives on its own subdomain, shares one database, one auth system, one design language. No pitch deck, no roadmap, no product strategy. Just things made, shipped, and shared.

### The core idea
"Sasta" (सस्ता) means *cheap* or *affordable* in Hindi. That word is the whole ethos:

- **Cheap to build.** Tiny budget, boring tools, shared infrastructure. A new project should cost closer to ₹0 than ₹0.
- **Cheap to ship.** One command, one subdomain, live on the internet.
- **Cheap to share.** Everything is open by default — open URL, open source, open to feedback.

Sasta isn't about low quality. It's the constraint that makes a lab possible at all. Expensive projects never ship; sasta projects do. The bar stays high because nothing here needs to earn its keep — it just has to be interesting enough to make.

**The positioning in one line:** *A sasta lab for the things I want to build.*

### Why it works for a mixed audience
- **Recruiters** see a builder — not a talker — with a long tail of things actually shipped.
- **Peers** get the bilingual in-joke, the scrappy-but-sharp vibe, and a place to poke at working projects.
- **Clients** see someone who ships end-to-end, from idea to URL, without ceremony.
- **Curious visitors** land on something strange-named, find working apps, stay for the lab feeling.

---

## 2. Voice & tone

### Voice attributes
Confident without boasting. Technical without jargon. Hinglish-aware without pandering. Dry humor, never self-deprecating to the point of undermining the work.

### Tone sliders
- Funny ••••◦ (willing to be dry, never zany)
- Formal ••◦◦◦ (conversational, not corporate)
- Hype ◦◦◦◦◦ (zero. the metrics do the hype.)
- Technical ••••◦ (comfortable dropping Spark, RLS, pgvector without explaining)

### Do
- Talk about the *thing*, not the builder. "This turns X into Y." not "I'm proud to announce."
- Use Hinglish when it adds meaning, not for flavor. `जो बनाना है, बनाओ` means something. "Yaar check it out" doesn't.
- Write like a maker inviting you into a workshop. Short sentences. Concrete nouns. First-person when it helps, never as the main event.
- Let the working thing be the argument. Every project card links to a live URL, not a screenshot.

### Don't
- Don't say "passionate about." Don't say "results-driven." (The resume already sins here; the brand shouldn't.)
- Don't turn the lab into a portfolio of wins. No metrics on the brand pages — the receipts live on the resume.
- Don't apologize for the name. "Sasta" is the strategy, not the disclaimer.
- Don't use emojis in body copy. Allowed sparingly in tags/labels if ever.
- Don't use stock-photo-developer clichés (hoodie, rain-on-window, glowing terminal).

### Taglines (pick by context)

| Context | Tagline |
|---|---|
| Primary (site hero) | A sasta lab for the things I want to build. |
| Hindi counterpart | जो बनाना है, बनाओ. *(build what you want to build)* |
| Short form (social bio) | My lab. Shipped sasta. Shared openly. |
| Sub-line / elaboration | Small projects, built cheap, out in the open. |
| Alternative | Built sasta. Shared openly. No roadmap. |

---

## 3. Logo system

Three marks, one family. All live in this folder as SVGs.

### 3.1 Primary wordmark — `logo-sastaspace.svg`
`sastaspace` set in Inter Medium, letterspacing -0.02em, all lowercase. The terminal period `.` is always in sasta orange (`#c05621`). Use on light surfaces.

### 3.2 Compact mark — `logo-mark.svg`
A rounded square in ink (`#1a1917`) with an inset price-tag outline in sasta orange and the bilingual monogram "स/S" in paper white. Minimum size 16×16px. Clear space on all sides = ½ the mark's height.

### 3.3 Monogram — `logo-monogram.svg`
Standalone "स/S" glyph pair. Use where the mark is redundant — favicon, avatar, sticker, footer.

### Personal mark (Mohit)
Same system. Wordmark is `mohit khare` in the same Inter Medium setting; compact mark is the same rounded square but with "MK" in place of "स/S". Visual sibling, not twin.

### Rules
- Never re-typeset the wordmark. Use the SVG.
- Never put the wordmark on a busy photograph. Use a paper or ink panel.
- Never color-shift the sasta orange. It is the brand. Hex it exactly: `#c05621`.
- Minimum clear space around the wordmark: the height of the lowercase "s".

---

## 4. Color system

One palette. Five colors. Two functional, three supporting.

| Role | Name | Hex | Use |
|---|---|---|---|
| Primary text / ink | Ink | `#1a1917` | Body text, dark surfaces, logo fill |
| Primary accent | Sasta | `#c05621` | Links, CTAs, price-tag highlights, the terminal period in the wordmark |
| Deeper accent | Rust | `#8a3d14` | Hover states, pressed buttons, secondary emphasis |
| Surface / paper | Paper | `#f5f1e8` | Page backgrounds, cards on ink |
| Muted neutral | Dust | `#a8a196` | Metadata, disabled, borders on paper |

### Contrast pairs (verified WCAG AA body text)
- Ink on Paper — 15.9:1 ✓ AAA
- Paper on Ink — 15.9:1 ✓ AAA
- Sasta on Paper — 5.3:1 ✓ AA for body, AAA for large
- Paper on Sasta — 3.9:1 ✓ AA large only (use for buttons/badges, not body)
- Dust on Paper — 3.0:1 · metadata only, never body

### Gradients, shadows, glows
None. Ever. Flat surfaces only. The only "depth" cue allowed is a 0.5px border in Dust at 40% alpha.

---

## 5. Typography

Three families. No more.

### Display & body — Inter
- Variable, open source, bundles Devanagari companion via Google Fonts.
- Weights used: 400 (regular), 500 (medium). Nothing heavier.
- Headings: 500, letter-spacing `-0.015em`, sentence case only.
- Body: 400, 16px, line-height 1.7.

### Mono — JetBrains Mono
- Weights used: 400, 500.
- For: metrics, subdomain slugs, code, stat cards, price-tag labels.
- Tracking slightly looser: `letter-spacing: 0.04em` on uppercase labels.

### Devanagari — IBM Plex Sans Devanagari
- Weights used: 400, 500.
- For: the Hindi tagline, any Devanagari word appearing inline.
- Pairs tightly with Inter — matching x-height and stroke weight.

### Type specimens

```
Heading 1  48/1.1/500  -0.02em   Expensive engineering at sasta prices.
Heading 2  32/1.15/500 -0.015em  The project bank.
Heading 3  20/1.3/500  -0.01em   Keystone AI
Body       16/1.7/400  0         Built cheap. Built well. Pick both.
Label      12/1/500    0.06em    runtime · throughput · cloud bill
Mono stat  18/1/500    0         −94%   8×   −80%   $75K
Devanagari 16/1.5/500  0         कम दाम, ज़्यादा काम
```

---

## 6. Visual vocabulary

Recurring shapes that tie the system together. Use these instead of inventing new motifs.

1. **Status chips** — small rounded rectangles in ink or sasta, mono text, one label per chip. Used for project state, not for metrics. Allowed values: `live`, `wip`, `paused`, `archived`, `open source`. This is the signature element.
2. **Price tags** — rounded-rectangle SVG outline with a single corner "notch." Used for project labels, call-outs, and the mark itself. The tag shape is the brand's spirit animal: lightweight, honest, pinned to things in a bazaar.
3. **Terminal prompts** — `~/mohit` or `sastaspace.com —` in mono, Dust color, top-of-section anchors. Quiet reminder that this is a dev-first lab.
4. **Bilingual stacking** — Devanagari line stacked tight under a Latin line, Dust-colored, smaller. Never compete in size.
5. **Handwritten "workshop marks"** (optional) — when a project is clearly experimental, allowed: a single hand-drawn arrow or circled word in sasta orange, overlapping a card corner. Use sparingly; one per page maximum.

---

## 7. Layout principles

- **One-column first.** The landing page and every project page starts as a single 680–720px content column on desktop. Side decoration is off-limits.
- **Generous vertical rhythm.** Sections separated by ≥64px on desktop, ≥40px on mobile.
- **Borders over shadows.** Cards are 0.5px Dust borders on Paper. Never shadows.
- **Mono gets left margin.** Any mono run (stat, slug, label) aligns flush-left to the content column. Never center mono text.

---

## 8. Voice examples — from bad to brand

| Occasion | Avoid | Use |
|---|---|---|
| Hero line | "Welcome to my portfolio of side projects." | A sasta lab for the things I want to build. |
| About | "I'm passionate about building scalable systems." | This is my workshop. I make things I want to exist, and I put them somewhere you can use them. |
| Why "lab" | "A curated collection of case studies." | Not a portfolio. A lab. Some of it works. Some of it's half-built. All of it's here. |
| Project teaser | "An exciting AI-powered tool for developers." | Talks to your repo. Answers in plain English. Runs local. |
| Empty state | "No projects yet!" | The workshop's quiet today. Come back soon. |
| 404 | "Page not found." | यहाँ कुछ नहीं है. Nothing here. Try the homepage. |
| Footer | "© 2026 All rights reserved." | Built sasta. Shared openly. © Mohit Khare, 2026. |

---

## 9. What the system is NOT

Documenting these up front so the brand doesn't drift.

- **Not a startup.** SastaSpace is a lab, not a company. No "we." No "our team." No "mission statement" fluff. One person making things.
- **Not a portfolio.** Portfolios edit for wins; labs show the whole bench. Broken prototypes and work-in-progress are allowed — even encouraged — as long as they're labelled honestly.
- **Not a resume.** Specific metrics, job titles, and promotion ladders belong on the resume. The lab is about ideas and working URLs, not numbers.
- **Not a template site.** Linear-clone / Vercel-clone / "dark mode with a gradient" is explicitly off-brand. The warmth of paper and the terracotta orange are the opposite of that aesthetic.
- **Not ironic.** The humor is dry, not performatively edgy. Sasta is a real design constraint, not a joke.
- **Not monolingual.** Removing the Devanagari removes half the idea. Keep the bilingual motif even on English-only pages.

---

## 10. Roll-out checklist

When applying the system to a new project under `<name>.sastaspace.com`:

- [ ] Project uses Inter + JetBrains Mono + IBM Plex Sans Devanagari (imported once from Google Fonts in the shared layout).
- [ ] Color tokens imported from `brand/tokens.css` (ink, sasta, rust, paper, dust).
- [ ] Page starts with the terminal-prompt anchor: `<project>.sastaspace.com —`.
- [ ] Hero headline uses the sentence-case, `-0.015em` treatment.
- [ ] A status chip (`live`, `wip`, `paused`, `archived`, `open source`) — not a metric.
- [ ] Footer: `Built sasta. Shared openly. © Mohit Khare, 2026.` + link back to `sastaspace.com`.
- [ ] Accessibility: all text hits WCAG AA; sasta orange used for emphasis, not for body copy.
- [ ] No gradients, shadows, glows. Kill them in code review.

---

## 11. File index

- `BRAND_GUIDE.md` — this document
- `landing-mockup.html` — the `sastaspace.com` homepage applied
- `logo-sastaspace.svg` — primary wordmark
- `logo-mark.svg` — compact mark (rounded square + bilingual monogram)
- `logo-monogram.svg` — standalone "स/S" glyph
- `logo-mohit-khare.svg` — personal wordmark
- `logo-mk-mark.svg` — personal compact mark
- `bio.md` — short / medium / long bios + tagline variants
- `tokens.css` — CSS custom properties to import into every project
