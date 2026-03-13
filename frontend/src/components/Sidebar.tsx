"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Bot,
  Database,
  GitBranch,
  KeyRound,
  LayoutDashboard,
  Rocket,
  ScrollText,
  Server,
  Settings,
} from "lucide-react";

const menuItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/servers", label: "Servers", icon: Server },
  { href: "/dashboard/deployments", label: "Deployments", icon: Rocket },
  { href: "/dashboard/databases", label: "Databases", icon: Database },
  { href: "/dashboard/pipelines", label: "Pipelines", icon: GitBranch },
  { href: "/dashboard/monitor", label: "Monitor", icon: Activity },
  { href: "/dashboard/logs", label: "Logs", icon: ScrollText },
  { href: "/dashboard/secrets", label: "Secrets", icon: KeyRound },
  { href: "/dashboard/agents", label: "Agents", icon: Bot },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden lg:block w-64 border-r border-slate-800 bg-slate-950/90 py-6">
      <div className="px-6 mb-8">
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-[0.18em]">
          Workspace
        </h2>
      </div>

      <nav className="space-y-1 px-3">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const active =
            pathname === item.href ||
            (item.href !== "/dashboard" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm transition ${
                active
                  ? "bg-gradient-to-r from-cyan-500/20 to-blue-600/30 text-white font-semibold"
                  : "text-slate-300 hover:bg-slate-800 hover:text-white"
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="px-6 mt-8 pt-6 border-t border-slate-800">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
          <p className="font-semibold text-slate-100 text-sm mb-1">Environment Safety</p>
          <p className="text-xs text-slate-400">
            Every AI action validates server state before execution.
          </p>
        </div>
      </div>
    </aside>
  );
}
