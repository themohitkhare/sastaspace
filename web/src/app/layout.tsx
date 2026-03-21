import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_BASE_URL || "https://sastaspace.com"
  ),
  title: "SastaSpace - AI Website Redesigner",
  description: "See your website redesigned by AI in 60 seconds",
  openGraph: {
    title: "SastaSpace - AI Website Redesigner",
    description:
      "See your website redesigned by AI in 60 seconds. Get a free AI-powered redesign of any website.",
    type: "website",
    siteName: "SastaSpace",
    locale: "en_US",
    // OG image is auto-detected from opengraph-image.tsx by Next.js App Router
  },
  twitter: {
    card: "summary_large_image",
    title: "SastaSpace - AI Website Redesigner",
    description: "See your website redesigned by AI in 60 seconds.",
    // Twitter image is auto-detected from opengraph-image.tsx by Next.js App Router
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} antialiased`}>
        {children}
      </body>
    </html>
  );
}
