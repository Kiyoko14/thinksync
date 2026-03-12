"use client";

import Link from "next/link";
import { useState } from "react";

export default function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <nav className="bg-white border-b">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        
        <Link href="/" className="font-bold text-xl">
          ThinkSync
        </Link>

        <div className="hidden md:flex gap-6">
          <Link href="/dashboard">Dashboard</Link>
          <Link href="/dashboard/servers">Servers</Link>
          <Link href="/dashboard/databases">Databases</Link>
        </div>

        <button
          className="md:hidden"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        >
          ☰
        </button>
      </div>

      {mobileMenuOpen && (
        <div className="md:hidden px-4 pb-4 flex flex-col gap-3">
          <Link href="/dashboard">Dashboard</Link>
          <Link href="/dashboard/servers">Servers</Link>
        </div>
      )}
    </nav>
  );
}
