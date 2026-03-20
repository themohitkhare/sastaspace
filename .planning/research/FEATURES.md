# Feature Research

**Domain:** AI website redesign tool with lead-generation frontend
**Researched:** 2026-03-21
**Confidence:** MEDIUM-HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete or broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Single URL input with clear CTA | Every AI demo tool starts with one input. v0.dev, ChatGPT, Midjourney all have a single prompt field front-and-center. Users will bounce if they can't figure out what to do in 3 seconds. | LOW | Large input field, prominent "Redesign" button. No login gate. |
| Real-time progress feedback (not a spinner) | 30-60 seconds is an eternity with a loading spinner. NNGroup research confirms: determinate progress indicators are mandatory for waits over 10 seconds. Indeterminate spinners at this duration cause abandonment. | MEDIUM | Use SSE (Server-Sent Events) from FastAPI to stream named steps: "Crawling site...", "Analyzing design...", "Generating redesign...". Show a progress bar with percentage AND text status. |
| Full-page redesign preview | The entire point of the tool. Users came to see their site redesigned. Showing it in a clean, full-width iframe or embedded view is non-negotiable. | LOW | Iframe with the redesigned HTML. Must render cleanly at multiple viewport sizes. |
| Mobile responsive layout | Over 50% of web traffic is mobile. A web design tool that isn't responsive undermines its own credibility. | MEDIUM | The landing page AND the redesign preview must work on mobile. Preview can use a "desktop preview" toggle on small screens. |
| Professional visual design quality | This site IS the portfolio. If the landing page looks cheap, nobody will trust the redesign output or hire the owner. Users judge design skill by the tool's own appearance. | HIGH | Must look like a high-end agency site. Generous whitespace, modern typography, polished micro-interactions. This is the hardest "feature" -- it's pure craft. |
| Clear contact/hire CTA | Users who are impressed need an obvious path to hire. If they have to hunt for contact info, the lead is lost. | LOW | Persistent but non-intrusive CTA. Appears contextually after viewing the redesign result. |
| Fast initial page load | Landing page must load in under 2 seconds. Users arriving from social media or search have zero patience. A slow-loading design tool is an oxymoron. | LOW | Next.js SSR handles this. Keep hero section lightweight. No heavy animations blocking first paint. |

### Differentiators (Competitive Advantage)

Features that create the "wow moment" and set SastaSpace apart from generic agency sites.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Before/after interactive slider | A draggable slider comparing a screenshot of the original site vs. the AI redesign is the single most powerful visual proof element. Agency sites like Tenet and Nice Branding use static before/after screenshots -- an interactive slider is significantly more engaging. This is the "wow moment." | MEDIUM | Use a before/after slider component (many open-source React options). Capture original screenshot during crawl (Playwright already does this). Show redesign screenshot alongside. |
| Animated step-by-step progress with visual previews | Instead of a plain progress bar, show the actual crawl screenshot appearing, then "dissolve" or "morph" into the redesign. Midjourney popularized the concept of watching AI work in real-time. Seeing the transformation happen is dramatically more engaging than waiting for a final result. | HIGH | Could show: (1) original site screenshot fading in during crawl, (2) skeleton/wireframe appearing during analysis, (3) final redesign rendering. Even a simplified version (screenshot -> loading animation -> result) beats a plain progress bar. |
| Contextual "hire me" CTA on the result page | Instead of a generic contact page, the CTA appears right below the redesign with copy like "Want this built for real? Let's talk." The emotional peak is when users see their site redesigned -- that's when conversion intent is highest. | LOW | Position the CTA immediately after the redesign preview. Use benefit-driven copy tied to what they just experienced. |
| Social proof / portfolio examples | Show 3-5 previous redesign examples on the landing page so users see quality before committing to the 30-60 second wait. Reduces bounce from users unsure if the tool is worth trying. | LOW | Static examples with before/after thumbnails. Can be curated from best outputs. |
| SEO-optimized landing page with meta tags | Organic traffic is free leads. A Next.js SSR page with proper meta tags, Open Graph images, and structured data will rank for "free website redesign" and similar queries. | LOW | Next.js handles SSR natively. Add meta tags, OG image (screenshot of a redesign), and JSON-LD. |
| Shareable result URLs | Each redesign gets a unique URL users can share. This creates viral distribution -- "look what AI did to my site." Every share is free marketing. | MEDIUM | Already partially exists (FastAPI serves at `localhost:8080/{subdomain}/`). Need to ensure public URLs via Cloudflare tunnel are clean and shareable. Add OG meta tags to result pages. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but actively hurt the lead-gen business model or add unjustified complexity.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| User accounts / login | "Let users save their redesigns" | Adds auth complexity, database needs, GDPR concerns. Kills the frictionless experience. Every login wall reduces conversion. The business model is lead capture, not user retention. | Shareable URLs serve the same purpose. No account needed. |
| Side-by-side comparison view | "Show old and new next to each other" | Halves the visual impact of the redesign on smaller screens. The redesign should dominate the viewport for maximum wow factor. Side-by-side looks cramped on mobile. | Before/after slider (one view, interactive) or a toggle button between original and redesign. Full-width redesign as the default view. |
| Multiple redesign variations | "Give users 3 options to choose from" | Triples API cost and wait time (90-180 seconds). Creates decision paralysis. Users are not paying customers -- they don't need choice, they need to be impressed once. | Single high-quality redesign. The goal is "wow" not "which one." |
| Download/export redesign HTML | "Let users download the code" | Gives away the product for free. If users can self-serve the HTML, they have no reason to hire the owner. Undermines the entire lead-gen model. | Show the redesign visually only. The CTA is "hire me to build this for real" -- the redesign is a teaser, not a deliverable. |
| Real-time chat / chatbot | "Add a chat widget for instant communication" | Requires being online to respond. Creates expectation of instant replies. A solo consultant can't staff a chat widget 24/7. Unanswered chats are worse than no chat at all. | Async contact form with "I'll respond within 24 hours" expectation setting. |
| Redesign history / gallery of all submissions | "Show a public gallery of all redesigns" | Quality is inconsistent -- bad examples hurt credibility. Privacy concerns (users might not want their site publicly listed). Storage/maintenance overhead. | Curated portfolio of 5-10 best examples, manually selected. |
| Rate limiting with CAPTCHA | "Prevent abuse" | CAPTCHAs reduce conversion. Most abuse is theoretical for a tool this niche. | Simple IP-based rate limiting on the backend (3 redesigns per IP per day). No user-facing friction. |
| Analytics dashboard | "Track how many redesigns, conversion rates" | Over-engineering for MVP. Can be added later. | Use Plausible or simple server-side logging. No dashboard UI needed at launch. |

## Feature Dependencies

```
[URL Input Form]
    +--requires--> [FastAPI /redesign endpoint]
                       +--requires--> [SSE progress streaming]
                       +--requires--> [Redesign preview page]
                                          +--enhances--> [Before/after slider]
                                          +--enhances--> [Shareable result URLs]
                                          +--requires--> [Contact form CTA]

[Landing page hero]
    +--enhances--> [Portfolio examples]
    +--enhances--> [SEO meta tags]

[Contact form CTA]
    +--requires--> [Form submission backend (email/store)]

[Before/after slider]
    +--requires--> [Original site screenshot (from Playwright crawl)]
    +--requires--> [Redesign screenshot (from rendered HTML)]
```

### Dependency Notes

- **Redesign preview requires FastAPI endpoint:** The frontend can't show results without a backend route that accepts URLs and returns redesigned HTML.
- **SSE progress streaming requires backend support:** FastAPI must emit named events during the crawl/redesign pipeline. This is a backend change, not just frontend.
- **Before/after slider requires screenshots:** Playwright already captures original screenshots during crawl. Need to also capture a screenshot of the rendered redesign HTML for the "after" comparison.
- **Contact form requires delivery mechanism:** Form submissions must go somewhere -- email via SMTP/SendGrid, or a local SQLite/JSON store. Without delivery, leads are lost.
- **Shareable URLs require public routing:** Cloudflare tunnel must route `sastaspace.com/{subdomain}` to the FastAPI preview server cleanly.

## MVP Definition

### Launch With (v1)

Minimum viable product -- what's needed to generate the first lead.

- [ ] **Landing page with URL input** -- the entry point. Without this, nothing else matters.
- [ ] **FastAPI /redesign endpoint with SSE progress** -- the engine. Must stream status updates during the 30-60 second process.
- [ ] **Step-by-step progress UI** -- shows named stages ("Crawling your site...", "Analyzing design...", "Generating redesign...") with a progress bar. Prevents abandonment during the wait.
- [ ] **Full-page redesign preview** -- the payoff. Clean iframe rendering of the AI-generated HTML.
- [ ] **Contact form with "hire me" CTA** -- the conversion point. Name, email, brief message. Appears on the result page. Submissions delivered via email or stored locally.
- [ ] **Mobile responsive** -- too much traffic is mobile to skip this at launch.
- [ ] **3-5 curated portfolio examples on landing page** -- social proof before the user commits to waiting. Can be generated from existing CLI tool.

### Add After Validation (v1.x)

Features to add once the core flow is working and generating leads.

- [ ] **Before/after interactive slider** -- add when original screenshots are reliably captured. Major wow-factor upgrade.
- [ ] **Shareable result URLs with OG meta tags** -- add when routing through Cloudflare tunnel is stable. Enables viral sharing.
- [ ] **Animated progress visualization** -- replace text-based steps with visual transitions (screenshot morphing). Add when the basic progress UI is proven.
- [ ] **SEO optimization** -- meta tags, Open Graph images, JSON-LD structured data. Add once the page design is stable to avoid rework.
- [ ] **IP-based rate limiting** -- add if abuse becomes a real problem, not before.

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **Testimonials from actual clients** -- need real clients first.
- [ ] **Blog / content marketing** -- SEO play for long-term organic traffic. Only worth the effort after validating lead quality.
- [ ] **Multiple page redesign** -- redesign an entire site, not just the homepage. Major complexity increase for unclear value.
- [ ] **Custom style preferences** -- let users choose color scheme, style direction before redesign. Adds friction to the core flow.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| URL input + submit | HIGH | LOW | P1 |
| SSE progress feedback | HIGH | MEDIUM | P1 |
| Redesign preview (iframe) | HIGH | LOW | P1 |
| Contact form CTA | HIGH | LOW | P1 |
| Professional landing page design | HIGH | HIGH | P1 |
| Mobile responsive | HIGH | MEDIUM | P1 |
| Portfolio examples | MEDIUM | LOW | P1 |
| Before/after slider | HIGH | MEDIUM | P2 |
| Shareable result URLs | MEDIUM | MEDIUM | P2 |
| SEO meta tags / OG images | MEDIUM | LOW | P2 |
| Animated progress visualization | MEDIUM | HIGH | P2 |
| Rate limiting | LOW | LOW | P3 |
| Blog / content section | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | v0.dev | Galileo AI (Google Stitch) | Typical Agency Site | SastaSpace Approach |
|---------|--------|---------------------------|--------------------|--------------------|
| Input method | Text prompt | Text prompt | N/A (portfolio only) | URL input -- zero creative effort from user |
| Wait time | ~5-15 seconds | ~10-20 seconds | N/A | ~30-60 seconds (longer, needs better progress UX) |
| Progress feedback | Streaming code generation | Loading with preview | N/A | Named steps + progress bar via SSE |
| Output format | Editable React code | Figma mockup | Static screenshots | Full rendered HTML preview in browser |
| "Wow moment" | Seeing code generate live | Polished mockup from text | Portfolio quality | Seeing YOUR OWN site redesigned |
| Lead capture | N/A (product is the business) | N/A (product is the business) | Contact form, buried on separate page | Contextual CTA at moment of peak engagement |
| Personalization | Generic (user provides prompt) | Generic (user provides prompt) | None | Deeply personal -- it's the user's own website |
| Social proof | Vercel brand, community | Google brand | Client logos, testimonials | Curated before/after portfolio examples |
| Mobile experience | Full app | Full app | Usually responsive | Responsive landing + mobile preview toggle |

### Key Competitive Insight

SastaSpace's unfair advantage is **personalization without effort**. v0.dev and Galileo require users to describe what they want. SastaSpace requires only a URL -- the AI does everything. Seeing your own website redesigned is inherently more engaging than seeing a generic mockup. This "it's about YOU" factor is the core differentiator and should be emphasized in all copy and UX decisions.

## Progress UX Deep Dive

The 30-60 second wait is SastaSpace's biggest UX risk. Research-backed recommendations:

**Must do:**
- Determinate progress bar with percentage (NNGroup: mandatory for 10+ second waits)
- Named step labels that update ("Crawling your site...", "Analyzing layout...", "Redesigning with AI...")
- Estimated time remaining ("About 30 seconds left")

**Should do:**
- Show the original site screenshot appearing during crawl phase (proves the tool is working on THEIR site)
- Smooth progress pacing -- don't let the bar sit at 80% for 20 seconds (NNGroup: uneven pacing feels deceptive)
- Allow users to keep scrolling the landing page while redesign runs (don't block the whole UI)

**Avoid:**
- Indeterminate spinners (causes abandonment at 30+ seconds)
- Fake progress that doesn't map to real steps (users notice)
- Blocking the entire page during processing (let them browse portfolio examples while waiting)

## Contact Form Conversion Deep Dive

Research-backed recommendations for the lead-gen contact form:

**Form fields (keep minimal):**
- Name (required)
- Email (required)
- Message / "Tell me about your project" (optional, textarea)
- Do NOT require phone number (reduces conversion by up to 52%)

**Placement and timing:**
- Primary CTA on the redesign result page, immediately below the preview
- Secondary CTA in the landing page footer
- Copy should reference what they just saw: "Like what you see? Let's build the real thing."

**Post-submission:**
- Immediate confirmation message ("Thanks! I'll be in touch within 24 hours")
- Auto-send email notification to the owner
- No redirect to a separate "thank you" page -- keep them on the result page

**What NOT to do:**
- Multi-step form (overkill for 3 fields)
- Calendar booking widget (requires calendar integration, adds friction)
- Live chat (can't staff it solo)

## Sources

- [NNGroup: Progress Indicators Make a Slow System Less Insufferable](https://www.nngroup.com/articles/progress-indicators/)
- [NNGroup: Status Trackers and Progress Updates: 16 Design Guidelines](https://www.nngroup.com/articles/status-tracker-progress-update/)
- [Smashing Magazine: Best Practices For Animated Progress Indicators](https://www.smashingmagazine.com/2016/12/best-practices-for-animated-progress-indicators/)
- [Smart Interface Design Patterns: Designing Better Loading and Progress UX](https://smart-interface-design-patterns.com/articles/designing-better-loading-progress-ux/)
- [Unbounce: 20 Lead Generation Form Examples with Best Practices](https://unbounce.com/conversion-rate-optimization/optimize-lead-gen-forms/)
- [VWO: 18 Lead Generation Forms: Examples and Best Practices](https://vwo.com/blog/lead-generation-forms/)
- [Venture Harbour: 15 Best Contact Form Design Examples (2026)](https://ventureharbour.com/15-contact-form-examples-help-design-ultimate-contact-page/)
- [Prosper Marketing: Contact Form Best Practices for 2025](https://www.prospermarketingsolutions.com/blogs-contact-form-best-practices-for-2025/)
- [SaaSFrame: 10 SaaS Landing Page Trends for 2026](https://www.saasframe.io/blog/10-saas-landing-page-trends-for-2026-with-real-examples)
- [Orizon: 10 Favourite Landing Page Designs in Fall 2025](https://www.orizon.co/blog/our-10-favourite-landing-page-designs-in-fall-2025-and-why-they-convert)
- [Elfsight: Before and After Image Slider Widget](https://elfsight.com/before-and-after-slider-widget/)
- [Framer: Before-After Slider Component](https://www.framer.com/marketplace/components/before-and-after/)
- [v0.dev landing page and docs](https://v0.app)
- [UXPilot: Galileo AI Complete Guide 2026](https://uxpilot.ai/galileo-ai)

---
*Feature research for: AI website redesign tool with lead-generation frontend*
*Researched: 2026-03-21*
