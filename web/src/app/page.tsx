"use client";

import { HeroSection } from "@/components/landing/hero-section";
import { HowItWorks } from "@/components/landing/how-it-works";

export default function Home() {
  return (
    <main>
      <HeroSection onSubmit={(url) => console.log("Submit:", url)} />
      <section className="py-12 px-4">
        <HowItWorks />
      </section>
    </main>
  );
}
