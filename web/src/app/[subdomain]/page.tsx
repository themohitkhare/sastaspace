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
  };
}

export default async function ResultPage({
  params,
}: {
  params: Promise<{ subdomain: string }>;
}) {
  const { subdomain } = await params;
  return <ResultView subdomain={subdomain} isShareable />;
}
