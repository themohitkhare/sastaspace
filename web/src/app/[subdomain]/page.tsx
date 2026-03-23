import type { Metadata } from "next";
import { ResultView } from "@/components/result/result-view";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ subdomain: string }>;
}): Promise<Metadata> {
  const { subdomain } = await params;
  const domain = subdomain.replace(/-/g, ".");
  return {
    title: `${domain} — Redesigned by SastaSpace`,
    description: `See the AI-powered redesign of ${domain}`,
    openGraph: {
      title: `${domain} — Redesigned by SastaSpace`,
      description: `See the stunning AI redesign of ${domain}. Get yours free at sastaspace.com`,
      images: [`/api/og?subdomain=${subdomain}`],
    },
    twitter: {
      card: "summary_large_image",
      title: `${domain} — Redesigned by SastaSpace`,
      images: [`/api/og?subdomain=${subdomain}`],
    },
  };
}

export default async function ResultPage({
  params,
}: {
  params: Promise<{ subdomain: string }>;
}) {
  const { subdomain } = await params;
  return <ResultView subdomain={subdomain} />;
}
