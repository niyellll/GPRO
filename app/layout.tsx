import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  metadataBase: new URL("https://gpro-niyellll.vercel.app"),
  title: "GPro — Pusat Kajian Strategis",
  description: "Global Pro-eksistensi: kajian strategis, policy brief, peta analitik, dan roadmap kebijakan berbasis data untuk keputusan yang dapat dijalankan.",
  openGraph: {
    type: "website",
    locale: "id_ID",
    title: "GPro — Global Pro-eksistensi",
    description: "Pusat kajian strategis untuk kebijakan, data, dan roadmap implementasi.",
    siteName: "Global Pro-eksistensi",
  },
  icons: { icon: "/logo.png", apple: "/logo.png" },
};
export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#F8FAFD" };

const themeScript = `try { const stored = localStorage.getItem("gpro-theme"); const dark = stored === "dark" || (!stored && matchMedia("(prefers-color-scheme: dark)").matches); document.documentElement.classList.toggle("dark", dark); } catch (e) {}`;

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="id" suppressHydrationWarning>
      <head><script dangerouslySetInnerHTML={{ __html: themeScript }} /></head>
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>{children}</body>
    </html>
  );
}
