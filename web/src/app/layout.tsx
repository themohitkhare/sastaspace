import type { Metadata } from "next";
import { Instrument_Serif, Space_Grotesk } from "next/font/google";
import "./globals.css";

const instrumentSerif = Instrument_Serif({
  weight: "400",
  style: ["normal", "italic"],
  subsets: ["latin"],
  variable: "--font-heading",
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

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
      <body
        className={`${instrumentSerif.variable} ${spaceGrotesk.variable} font-sans antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
