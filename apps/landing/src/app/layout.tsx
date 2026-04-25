import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-jetbrains",
  display: "swap",
});

export const metadata: Metadata = {
  title: "sastaspace — a sasta lab for the things I want to build",
  description:
    "A workshop on the open internet. Cheap to build. Cheap to ship. Open to share. Mohit Khare's personal lab.",
  metadataBase: new URL("https://sastaspace.com"),
  openGraph: {
    title: "sastaspace",
    description: "A sasta lab for the things I want to build.",
    url: "https://sastaspace.com",
    siteName: "sastaspace",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "sastaspace",
    description: "A sasta lab for the things I want to build.",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrains.variable}`}>
      <body>{children}</body>
    </html>
  );
}
