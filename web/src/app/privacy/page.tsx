import type { Metadata } from "next";
import { PrivacyContent } from "@/components/privacy/privacy-content";

export const metadata: Metadata = {
  title: "Privacy Policy — SastaSpace",
  description:
    "How SastaSpace handles your data. No accounts, no tracking cookies, just transparent data practices.",
};

export default function PrivacyPage() {
  return <PrivacyContent />;
}
