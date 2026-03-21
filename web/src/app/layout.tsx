import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  metadataBase: new URL("https://sastaspace.com"),
  title: "SastaSpace - AI Website Redesigner",
  description: "See your website redesigned by AI in 60 seconds",
  openGraph: {
    title: "SastaSpace - AI Website Redesigner",
    description:
      "See your website redesigned by AI in 60 seconds. Get a free AI-powered redesign of any website.",
    type: "website",
    siteName: "SastaSpace",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "SastaSpace - AI Website Redesigner",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "SastaSpace - AI Website Redesigner",
    description: "See your website redesigned by AI in 60 seconds.",
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
