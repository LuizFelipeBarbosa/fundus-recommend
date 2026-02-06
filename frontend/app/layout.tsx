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
          href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900;1,400;1,500;1,600;1,700&family=Source+Serif+4:ital,opsz,wght@0,8..60,300;0,8..60,400;0,8..60,500;0,8..60,600;0,8..60,700;1,8..60,400;1,8..60,500&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="font-body noise-bg">
        <Navbar />
        <main className="mx-auto max-w-[1200px] px-6 pb-16">{children}</main>

        {/* Footer */}
        <footer className="border-t-2 border-ink mt-8">
          <div className="mx-auto max-w-[1200px] px-6 py-8">
            <div className="flex items-center justify-between">
              <p className="font-sans text-xs uppercase tracking-[0.2em] text-ink-muted">
                Powered by Fundus &middot; Humboldt-Universit&auml;t zu Berlin
              </p>
              <p className="font-sans text-xs text-ink-muted">
                AI-curated news intelligence
              </p>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
