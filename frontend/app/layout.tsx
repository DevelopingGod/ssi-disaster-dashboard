import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Natural-Disaster.io — Global Crisis Intelligence",
  description:
    "AI-powered real-time disaster intelligence platform. Live humanitarian signals, AI narrative context, geospatial monitoring.",
  openGraph: {
    title: "Natural-Disaster.io — Global Crisis Intelligence",
    description:
      "Natural-language disaster queries over live GDACS and ReliefWeb feeds. AI-interpreted humanitarian intelligence on a live map.",
    url: "https://natural-disaster.io",
    siteName: "Natural-Disaster.io",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Natural-Disaster.io — Global Crisis Intelligence",
    description:
      "Natural-language disaster queries over live GDACS and ReliefWeb feeds. AI-interpreted humanitarian intelligence on a live map.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <head>
        {/* Runs before React hydrates — applies saved theme without flash */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('disaster-theme');if(t==='light')document.documentElement.classList.add('light');}catch(e){}})()`,
          }}
        />
      </head>
      <body className="min-h-full flex flex-col">
        <Navbar />
        {children}
      </body>
    </html>
  );
}
