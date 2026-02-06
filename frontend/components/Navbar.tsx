"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import SearchBar from "./SearchBar";

const navLinks = [
  { href: "/", label: "Home" },
  { href: "/search", label: "Search" },
  { href: "/recommendations", label: "Recommendations" },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="sticky top-0 z-50 border-b border-gray-200 bg-white shadow-sm">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-6 px-4">
        <Link href="/" className="text-xl font-bold text-blue-600 whitespace-nowrap">
          Fundus News
        </Link>

        <div className="hidden flex-1 sm:block">
          <SearchBar compact />
        </div>

        <div className="flex items-center gap-1">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                pathname === link.href
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              }`}
            >
              {link.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
