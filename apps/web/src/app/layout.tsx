// meta: root layout. Fonts per DESIGN.md typography: Inter (all UI),
// JetBrains Mono (evidence quotes + rule ids). Mounts the U1 app shell
// (fixed left sidebar, expanded only) and the tooltip provider; the main
// panel renders the active surface. Desktop 1440 only for v1.
import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppSidebar } from "@/components/shell/app-sidebar";
import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });
const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Shiboleth",
  description: "Marketing compliance monitoring",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${jetbrainsMono.variable} antialiased`}>
        <TooltipProvider>
          <div className="flex min-h-screen">
            <AppSidebar />
            <div className="min-w-0 flex-1">{children}</div>
          </div>
        </TooltipProvider>
      </body>
    </html>
  );
}
