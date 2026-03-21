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
    title: "Your redesign is ready -- SastaSpace",
    description: `${domain} has been redesigned by AI`,
    openGraph: {
      title: `${domain} redesigned by AI -- SastaSpace`,
      description: `See how AI redesigned ${domain}. Get your free website redesign at SastaSpace.`,
      images: ["/og-image.png"],
    },
    twitter: {
      card: "summary_large_image",
      title: `${domain} redesigned by AI -- SastaSpace`,
      description: `See how AI redesigned ${domain}. Get your free website redesign at SastaSpace.`,
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
