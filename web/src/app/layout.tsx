import type { Metadata, Viewport } from "next";
import { Instrument_Serif, Space_Grotesk } from "next/font/google";
import { MotionProvider } from "@/components/providers/motion-provider";
import { ThemeToggle } from "@/components/ui/theme-toggle";
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

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
};

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
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Prevent flash of wrong theme by applying .dark before first paint */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem("sastaspace-theme");if(t==="dark"||(t!=="light"&&matchMedia("(prefers-color-scheme:dark)").matches))document.documentElement.classList.add("dark")}catch(e){}})()`,
          }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "WebApplication",
              name: "SastaSpace",
              description: "AI Website Redesigner",
              applicationCategory: "DesignApplication",
              operatingSystem: "All",
              offers: {
                "@type": "Offer",
                price: "0",
                priceCurrency: "USD",
              },
              url: "https://sastaspace.com",
            }),
          }}
        />
      </head>
      <body
        className={`${instrumentSerif.variable} ${spaceGrotesk.variable} font-sans antialiased`}
      >
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:bg-background focus:px-4 focus:py-2 focus:rounded-md focus:ring-2 focus:ring-ring"
        >
          Skip to content
        </a>
        <div className="fixed top-4 right-4 z-50">
          <ThemeToggle />
        </div>
        <MotionProvider>{children}</MotionProvider>
      </body>
    </html>
  );
}
