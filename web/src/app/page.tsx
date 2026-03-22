import type { Metadata } from "next";
import { AppFlow } from "@/components/app-flow";

export const metadata: Metadata = {
  title: "SastaSpace — Free AI Website Redesign",
  description:
    "Enter your domain URL and get a free, AI-powered redesign of your website in minutes. See what your site could look like with modern design.",
};

export default function Home() {
  return (
    <main>
      <AppFlow />
    </main>
  );
}
