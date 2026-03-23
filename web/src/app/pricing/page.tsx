import type { Metadata } from "next";
import { PricingContent } from "@/components/pricing/pricing-content";

export const metadata: Metadata = {
  title: "Pricing -- SastaSpace",
  description:
    "Choose the right plan for your AI website redesign. Free preview, premium redesign, or full build package.",
};

export default function PricingPage() {
  return <PricingContent />;
}
