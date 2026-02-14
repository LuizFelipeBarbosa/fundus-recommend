import type { Metadata } from "next";
import Navbar from "@/components/Navbar";
import "./globals.css";

export const metadata: Metadata = {
  title: "Nexus | AI-Curated News",
  description: "AI-curated news intelligence, delivered with editorial precision",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500;1,600&family=Manrope:wght@400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="font-body noise-bg">
        <Navbar />
        <main className="relative z-10 mx-auto max-w-[1320px] px-4 pb-14 sm:px-6 lg:px-8">{children}</main>

        {/* Footer */}
        <footer className="mt-8 border-t border-rule">
          <div className="mx-auto max-w-[1320px] px-4 py-7 sm:px-6 lg:px-8">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <p className="font-sans text-[10px] uppercase tracking-[0.22em] text-ink-muted">
                Powered by Fundus &middot; Humboldt-Universit&auml;t zu Berlin
              </p>
              <p className="font-sans text-[11px] text-ink-muted/85">
                AI-curated news intelligence
              </p>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
