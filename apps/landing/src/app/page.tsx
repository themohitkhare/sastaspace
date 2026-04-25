import { BrandMark } from "@/components/BrandMark";
import { Chip, type ChipVariant } from "@/components/Chip";
import { PresencePill } from "@/components/PresencePill";
import styles from "./landing.module.css";

type Project = {
  slug: string;
  title: string;
  blurb: string;
  status: ChipVariant;
  tags: string[];
};

const PROJECTS: Project[] = [
  {
    slug: "notes.sastaspace.com",
    title: "Notes",
    blurb:
      "Plain-text notes for people who type faster than they think. Keyboard-first, live-synced, zero ceremony.",
    status: "live",
    tags: ["next", "spacetimedb"],
  },
  {
    slug: "feed.sastaspace.com",
    title: "Feed",
    blurb:
      "A reader for the RSS corner of the web. Small, quiet, chronological. No algorithm, no logins you don't need.",
    status: "open source",
    tags: ["go", "sqlite"],
  },
  {
    slug: "pipes.sastaspace.com",
    title: "Pipes",
    blurb:
      "A visual builder for small data jobs. Drag boxes, connect them, watch rows flow through. Runs on your laptop too.",
    status: "wip",
    tags: ["react", "spark"],
  },
  {
    slug: "echo.sastaspace.com",
    title: "Echo",
    blurb:
      "Turn any URL into a podcast feed. Paste a link, get an audio episode, subscribe in your app of choice.",
    status: "live",
    tags: ["go", "tts"],
  },
  {
    slug: "scratch.sastaspace.com",
    title: "Scratch",
    blurb:
      "A whiteboard for one person. Infinite canvas, nothing to save, gone when you close the tab.",
    status: "paused",
    tags: ["canvas", "svg"],
  },
  {
    slug: "lab.sastaspace.com",
    title: "The Lab Log",
    blurb:
      "A firehose of tiny updates from the workshop. New experiments, half-finished thoughts, things that broke today.",
    status: "live",
    tags: ["rss", "markdown"],
  },
];

export default function HomePage() {
  return (
    <div className={styles.wrap}>
      <nav className={styles.nav} aria-label="Primary">
        <div className={styles.brand} aria-label="sastaspace">
          <BrandMark className={styles.brandMark} />
          <span>
            sastaspace
            <span className={styles.brandDot} aria-hidden="true" />
          </span>
        </div>
        <ul className={styles.navList}>
          <li>
            <PresencePill />
          </li>
          <li><a href="#lab">the lab</a></li>
          <li><a href="#projects">projects</a></li>
          <li><a href="#notes">notes</a></li>
          <li><a href="#about">about</a></li>
        </ul>
      </nav>

      <header className={styles.hero}>
        <div className={styles.heroSub}>~/mohit · sastaspace.com</div>
        <h1>
          A <span className={styles.heroAccent}>sasta</span> lab for the things I want to build.
        </h1>
        <p className={styles.heroLede}>
          This is my workshop on the open internet. I make the small things I want to exist —
          tools, toys, half-built experiments — and put them somewhere anyone can use them. Cheap
          to build. Cheap to run. Open to share.
        </p>
        <div className={styles.ctaRow}>
          <a href="#projects" className={`${styles.btn} ${styles.btnPrimary}`}>
            see the lab →
          </a>
          <a href="#about" className={`${styles.btn} ${styles.btnGhost}`}>
            about the idea
          </a>
        </div>
      </header>

      <section className={styles.section} id="lab">
        <div className={styles.eyebrow}>the idea</div>
        <h2>Not a portfolio. A lab.</h2>
        <p className={styles.lede}>
          Portfolios edit for wins. Labs show the whole bench. Sastaspace runs on three rules — the
          ones that make it possible to keep shipping small things without turning each one into a
          startup.
        </p>
        <div className={styles.principles} role="list">
          <div className={styles.principle} role="listitem">
            <div className={styles.principleNum}>01 / sasta</div>
            <h3>Cheap to build.</h3>
            <p>
              Boring tools. Shared infrastructure. New projects cost closer to zero than they do to
              a weekend brunch. The bill stays small so the imagination stays loud.
            </p>
          </div>
          <div className={styles.principle} role="listitem">
            <div className={styles.principleNum}>02 / shipped</div>
            <h3>One command to live.</h3>
            <p>
              Every experiment gets its own subdomain and goes from an idea to a working URL in the
              time it takes to name it. If it doesn't ship, it doesn't count.
            </p>
          </div>
          <div className={styles.principle} role="listitem">
            <div className={styles.principleNum}>03 / shared</div>
            <h3>Open by default.</h3>
            <p>
              Open URL, open source, open to being copied, forked, or improved on. The lab is on
              the internet so other people can find it — including me, six months from now.
            </p>
          </div>
        </div>
      </section>

      <section className={styles.section} id="projects">
        <div className={styles.projectsHeader}>
          <div>
            <div className={styles.eyebrow}>projects</div>
            <h2>What's on the bench.</h2>
          </div>
          <div className={styles.projectsCount}>six on display · more in the drawer</div>
        </div>
        <div className={styles.grid}>
          {PROJECTS.map((p) => (
            <a key={p.slug} className={styles.card} href={`https://${p.slug}`}>
              <div className={styles.cardSlug}>{p.slug}</div>
              <h3>{p.title}</h3>
              <p>{p.blurb}</p>
              <div className={styles.cardMeta}>
                <Chip variant={p.status} />
                <div className={styles.tags}>
                  {p.tags.map((t) => (
                    <span key={t} className={styles.tag}>{t}</span>
                  ))}
                </div>
              </div>
            </a>
          ))}
        </div>
      </section>

      <section className={styles.section} id="notes">
        <div className={styles.eyebrow}>workshop notes</div>
        <h2>Thinking out loud.</h2>
        <p className={styles.lede} style={{ marginBottom: 28 }}>
          Short posts on what I'm making, why a thing is built a certain way, and the mistakes I'd
          rather you not repeat. Written for me six months from now.
        </p>
        <ul className={styles.notesList}>
          <li>
            <span className={styles.notesDate}>· coming soon</span>
            <span className={styles.notesTitle}>
              <a href="#">Why everything here shares one database.</a>
            </span>
          </li>
          <li>
            <span className={styles.notesDate}>· coming soon</span>
            <span className={styles.notesTitle}>
              <a href="#">A subdomain is the cheapest deployable unit I know.</a>
            </span>
          </li>
          <li>
            <span className={styles.notesDate}>· coming soon</span>
            <span className={styles.notesTitle}>
              <a href="#">How to keep a side project from becoming a second job.</a>
            </span>
          </li>
        </ul>
      </section>

      <section className={styles.section} id="about">
        <div className={styles.about}>
          <div className={styles.aboutLeft}>
            <div className={styles.eyebrow}>about</div>
            <h2>Hi — I'm Mohit.</h2>
          </div>
          <div className={styles.aboutRight}>
            <p>
              I'm a software engineer in Bengaluru. I spend my days on the unglamorous end of
              software — making slow things fast, fragile things dependable, complicated things
              small. I like boring tools that age well.
            </p>
            <p>
              Sastaspace is the other half. It's where I build what I want to build — without
              asking anyone for a roadmap — and put it on the internet for whoever might want it.
              Some things here will get polished. Some will stay half-built forever. All of them
              are out in the open.
            </p>
            <p>
              If any of this is interesting, the best way to follow along is to bookmark{" "}
              <a href="#notes">the notes</a>, or grab the <a href="#">RSS feed</a>. I'm also on{" "}
              <a href="#">GitHub</a> and <a href="#">LinkedIn</a>.
            </p>
            <div className={styles.cardCompact}>
              <div className={styles.cardCompactLabel}>the lab, in one line</div>
              <dl>
                <div className={styles.drow}>
                  <dt>Run by</dt>
                  <dd>one person</dd>
                </div>
                <div className={styles.drow}>
                  <dt>Budget</dt>
                  <dd>sasta — close to ₹0</dd>
                </div>
                <div className={styles.drow}>
                  <dt>Roadmap</dt>
                  <dd>none on purpose</dd>
                </div>
                <div className={styles.drow}>
                  <dt>Default state</dt>
                  <dd>open to the public</dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      </section>

      <footer className={styles.foot}>
        <div className={styles.footRow}>
          <div className={styles.footSig}>
            Built <strong>sasta</strong>. Shared openly.
            <br />© Mohit Khare, 2026.
          </div>
          <div className={styles.footLinks}>
            <a href="#">github</a>
            <a href="#">linkedin</a>
            <a href="#">rss</a>
            <a href="mailto:hi@sastaspace.com">email</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
