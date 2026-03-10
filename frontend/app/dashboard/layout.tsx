"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { apiClient, User } from "@/lib/api";

type MenuItem = {
  name: string;
  href: string;
};

const menuItems: MenuItem[] = [
  { name: "Overview", href: "/dashboard" },
  { name: "Servers", href: "/dashboard/servers" },
  { name: "Chats", href: "/dashboard/chats" },
  { name: "Deployments", href: "/dashboard/deployments" },
  { name: "Databases", href: "/dashboard/databases" },
];

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    const bootstrap = async () => {
      try {
        const session = await apiClient.getSession();
        setUser(session);
      } catch {
        router.push("/login");
      } finally {
        setLoading(false);
      }
    };

    bootstrap();
  }, [router]);

  const handleLogout = async () => {
    localStorage.removeItem("authToken");
    router.push("/login");
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#070b12] text-slate-100">
        ThinkSync yuklanmoqda...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#070b12] text-slate-100">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_top,_rgba(37,99,235,0.20),_transparent_45%),radial-gradient(circle_at_90%_20%,_rgba(14,165,233,0.18),_transparent_35%)]" />

      <aside
        className={`fixed inset-y-0 left-0 z-40 w-72 border-r border-slate-800 bg-slate-900/95 px-5 py-6 backdrop-blur transition-transform duration-200 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        } lg:translate-x-0`}
      >
        <div className="mb-8 flex items-center justify-between">
          <Link href="/dashboard" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-cyan-500 text-sm font-bold">
              TS
            </div>
            <div>
              <p className="text-sm uppercase tracking-[0.2em] text-slate-400">Platform</p>
              <p className="text-lg font-semibold">ThinkSync</p>
            </div>
          </Link>
          <button className="text-slate-400 lg:hidden" onClick={() => setSidebarOpen(false)}>
            ✕
          </button>
        </div>

        <nav className="space-y-1">
          {menuItems.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`block rounded-xl px-4 py-3 text-sm transition ${
                  active
                    ? "bg-gradient-to-r from-blue-600/30 to-cyan-500/20 text-white"
                    : "text-slate-300 hover:bg-slate-800 hover:text-white"
                }`}
                onClick={() => setSidebarOpen(false)}
              >
                {item.name}
              </Link>
            );
          })}
        </nav>

        <div className="mt-8 rounded-xl border border-slate-800 bg-slate-800/70 p-4 text-xs text-slate-300">
          <p className="font-semibold text-slate-100">Server-state himoyasi yoqilgan</p>
          <p className="mt-2">Agent har buyruqdan oldin filesystem holatini tekshiradi.</p>
        </div>
      </aside>

      <div className="relative lg:pl-72">
        <header className="sticky top-0 z-30 border-b border-slate-800 bg-slate-950/85 backdrop-blur">
          <div className="flex items-center justify-between px-5 py-4 sm:px-8">
            <div className="flex items-center gap-3">
              <button className="text-slate-300 lg:hidden" onClick={() => setSidebarOpen(true)}>
                ☰
              </button>
              <p className="text-sm text-slate-400">AI DevOps Dashboard</p>
            </div>
            <div className="flex items-center gap-3">
              <p className="hidden text-sm text-slate-300 sm:block">{user?.email}</p>
              <button
                onClick={handleLogout}
                className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-200 transition hover:border-slate-500 hover:bg-slate-800"
              >
                Logout
              </button>
            </div>
          </div>
        </header>

        <main className="relative px-5 py-6 sm:px-8 sm:py-8">{children}</main>
      </div>

      {sidebarOpen && (
        <button
          aria-label="Close sidebar"
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
}
