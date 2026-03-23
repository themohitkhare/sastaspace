import type { Metadata } from "next";
import { ResultView } from "@/components/result/result-view";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ subdomain: string }>;
}): Promise<Metadata> {
  const { subdomain } = await params;
  const domain = subdomain.replace(/-/g, ".");
  const baseUrl =
    process.env.NEXT_PUBLIC_BASE_URL || "https://sastaspace.com";
  return {
    title: `${domain} — Redesigned by SastaSpace`,
    description: `See the AI-powered redesign of ${domain}`,
    alternates: {
      canonical: `${baseUrl}/${subdomain}`,
    },
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
  searchParams,
}: {
  params: Promise<{ subdomain: string }>;
  searchParams: Promise<{ tier?: string }>;
}) {
  const { subdomain } = await params;
  const { tier } = await searchParams;
  return <ResultView subdomain={subdomain} tier={tier} />;
}
