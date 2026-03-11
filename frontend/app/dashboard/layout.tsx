"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import {
  Bell,
  Bot,
  ChevronRight,
  Database,
  LayoutDashboard,
  LogOut,
  Menu,
  Rocket,
  Server,
  Settings,
  X,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";

type MenuItem = {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
};

const menuItems: MenuItem[] = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Servers", href: "/dashboard/servers", icon: Server },
  { name: "Chats", href: "/dashboard/chats", icon: Bot },
  { name: "Deployments", href: "/dashboard/deployments", icon: Rocket },
  { name: "Databases", href: "/dashboard/databases", icon: Database },
  { name: "Settings", href: "/dashboard/settings", icon: Settings },
];

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, loading, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  const handleLogout = async () => {
    await logout();
    router.replace("/login");
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#030712] text-slate-100">
        Loading ThinkSync...
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#030712] text-slate-100">
        Checking session...
      </div>
    );
  }

  const pathParts = pathname.split("/").filter(Boolean);
  const pageTitle = pathParts[pathParts.length - 1] ?? "dashboard";

  return (
    <div className="min-h-screen bg-[#030712] text-slate-100">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_10%_10%,rgba(6,182,212,0.12),transparent_36%),radial-gradient(circle_at_90%_0%,rgba(14,165,233,0.12),transparent_38%)]" />

      <aside
        className={`fixed inset-y-0 left-0 z-40 w-72 border-r border-slate-800 bg-slate-950/95 px-5 py-6 backdrop-blur transition-transform duration-200 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        } lg:translate-x-0`}
      >
        <div className="mb-8 flex items-center justify-between">
          <Link href="/dashboard" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 text-sm font-bold">
              TS
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Platform</p>
              <p className="text-lg font-semibold">ThinkSync</p>
            </div>
          </Link>
          <button className="text-slate-400 lg:hidden" onClick={() => setSidebarOpen(false)}>
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="space-y-1">
          {menuItems.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 rounded-xl px-4 py-3 text-sm transition ${
                  active
                    ? "bg-gradient-to-r from-cyan-500/20 to-blue-600/30 text-white"
                    : "text-slate-300 hover:bg-slate-800 hover:text-white"
                }`}
                onClick={() => setSidebarOpen(false)}
              >
                <Icon className="h-4 w-4" />
                {item.name}
              </Link>
            );
          })}
        </nav>

        <div className="mt-8 rounded-xl border border-slate-800 bg-slate-900/80 p-4 text-xs text-slate-300">
          <p className="font-semibold text-slate-100">Environment Safety Enabled</p>
          <p className="mt-2">Every AI action validates server state before execution for safer operations.</p>
        </div>
      </aside>

      <div className="relative lg:pl-72">
        <header className="sticky top-0 z-30 border-b border-slate-800 bg-slate-950/90 backdrop-blur">
          <div className="flex items-center justify-between px-5 py-4 sm:px-8">
            <div className="flex items-center gap-3">
              <button className="text-slate-300 lg:hidden" onClick={() => setSidebarOpen(true)}>
                <Menu className="h-5 w-5" />
              </button>
              <div>
                <p className="text-xs uppercase tracking-[0.14em] text-slate-500">ThinkSync Workspace</p>
                <div className="mt-1 flex items-center gap-2 text-sm text-slate-300">
                  <span className="capitalize">{pageTitle}</span>
                  <ChevronRight className="h-3.5 w-3.5 text-slate-500" />
                  <span className="text-slate-400">Live</span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button className="rounded-lg border border-slate-700 p-2 text-slate-300 hover:border-cyan-300/40 hover:text-white">
                <Bell className="h-4 w-4" />
              </button>
              <p className="hidden text-sm text-slate-300 sm:block">{user?.email}</p>
              <button
                onClick={handleLogout}
                className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-200 transition hover:border-cyan-300/40 hover:bg-slate-800"
              >
                <LogOut className="h-4 w-4" />
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
