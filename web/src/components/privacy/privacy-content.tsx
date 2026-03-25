"use client";

import Link from "next/link";
import { m } from "motion/react";
import { ArrowLeft } from "lucide-react";
import { FlickeringGrid } from "@/components/backgrounds/flickering-grid";
import { NavHeader } from "@/components/ui/nav-header";
import { Footer } from "@/components/landing/footer";

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mb-10">
      <h2 className="font-heading text-xl text-foreground mb-3">{title}</h2>
      <div className="text-sm text-muted-foreground leading-relaxed space-y-3">
        {children}
      </div>
    </section>
  );
}

export function PrivacyContent() {
  return (
    <main className="relative min-h-screen bg-background overflow-hidden">
      <FlickeringGrid className="absolute inset-0 z-0 opacity-40" />
      <div className="relative z-10">
        <NavHeader />
      </div>
      <div className="relative z-10 w-full max-w-3xl mx-auto px-6 sm:px-8 lg:px-12 pb-24 pt-8">
        <m.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
        >
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-12"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to home
          </Link>
        </m.div>

        <m.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.05, ease: "easeOut" }}
          className="mb-12"
        >
          <h1 className="font-heading text-[clamp(2rem,5vw,3.5rem)] leading-[1.1] text-foreground">
            Privacy Policy
          </h1>
          <p className="text-muted-foreground mt-4">
            Last updated: March 25, 2026
          </p>
        </m.div>

        <m.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.15, ease: "easeOut" }}
          className="border border-border rounded-xl p-8 backdrop-blur-sm bg-card/90"
        >
          <Section title="Overview">
            <p>
              SastaSpace is an AI-powered website redesigner. We believe in
              minimal data collection and transparent practices. You do not need
              an account to use our service — there are no personal accounts,
              passwords, or profiles stored.
            </p>
          </Section>

          <Section title="What data we collect">
            <p>When you use SastaSpace, we may collect the following:</p>
            <ul className="list-disc pl-5 space-y-2">
              <li>
                <span className="text-foreground font-medium">
                  Website URL
                </span>{" "}
                — the URL you submit for redesign. This is used to crawl the
                page content and generate an AI-powered redesign.
              </li>
              <li>
                <span className="text-foreground font-medium">IP address</span>{" "}
                — used solely for rate limiting to prevent abuse. We do not store
                IP addresses long-term or use them for tracking.
              </li>
              <li>
                <span className="text-foreground font-medium">
                  Contact form information
                </span>{" "}
                — if you choose to submit the contact form, we collect your
                name, email address, and message. This information is used only
                to respond to your inquiry.
              </li>
            </ul>
          </Section>

          <Section title="How we use your data">
            <ul className="list-disc pl-5 space-y-2">
              <li>
                To generate AI-powered redesigns of the website URL you provide.
              </li>
              <li>
                To respond to contact form submissions via email.
              </li>
              <li>
                To enforce rate limits and prevent abuse of the service.
              </li>
            </ul>
          </Section>

          <Section title="Generated redesigns">
            <p>
              When you submit a URL, the resulting AI-generated redesign is saved
              as a static HTML file and made publicly accessible at a subdomain
              (e.g., <code className="text-foreground bg-muted px-1.5 py-0.5 rounded text-xs">sastaspace.com/your-domain</code>).
              These redesigns are publicly viewable by anyone with the link.
            </p>
          </Section>

          <Section title="Cookies and tracking">
            <p>
              SastaSpace does not use analytics cookies or tracking scripts. The
              only cookie-like technology on the site is{" "}
              <span className="text-foreground font-medium">
                Cloudflare Turnstile
              </span>
              , which may set cookies when enabled to verify that form
              submissions come from real users rather than bots. Turnstile is
              only active on the contact form.
            </p>
            <p>
              We also store a theme preference (light/dark mode) in your
              browser&apos;s local storage. This is not a cookie and is never
              sent to our servers.
            </p>
          </Section>

          <Section title="Third-party services">
            <ul className="list-disc pl-5 space-y-2">
              <li>
                <span className="text-foreground font-medium">
                  Cloudflare
                </span>{" "}
                — DNS, CDN, and Turnstile bot protection.
              </li>
              <li>
                <span className="text-foreground font-medium">Resend</span> —
                email delivery for contact form submissions.
              </li>
              <li>
                <span className="text-foreground font-medium">Anthropic</span>{" "}
                — AI model provider (Claude) for generating website redesigns.
                Crawled page content is sent to the AI model for processing.
              </li>
            </ul>
          </Section>

          <Section title="Data retention">
            <p>
              Generated redesigns are stored indefinitely unless removed.
              Contact form submissions are retained only as long as needed to
              respond to your inquiry. Rate-limiting data is held in memory and
              discarded when the server restarts.
            </p>
          </Section>

          <Section title="Your rights">
            <p>
              You may request removal of a generated redesign or any data
              associated with your contact form submission at any time by
              emailing us.
            </p>
          </Section>

          <Section title="Contact">
            <p>
              If you have questions about this privacy policy or your data,
              reach out at{" "}
              <a
                href="mailto:hello@sastaspace.com"
                className="text-accent hover:text-accent/80 underline underline-offset-2 transition-colors"
              >
                hello@sastaspace.com
              </a>
              .
            </p>
          </Section>
        </m.div>
      </div>
      <Footer />
    </main>
  );
}
