import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Bot, Database, LayoutDashboard, Rocket, Server, Settings } from 'lucide-react';

export default function Sidebar() {
  const pathname = usePathname();

  const isActive = (path: string) => pathname.startsWith(path);

  const menuItems = [
    { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { href: '/dashboard/servers', label: 'Servers', icon: Server },
    { href: '/dashboard/chats', label: 'Chats', icon: Bot },
    { href: '/dashboard/deployments', label: 'Deployments', icon: Rocket },
    { href: '/dashboard/databases', label: 'Databases', icon: Database },
    { href: '/dashboard/settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="hidden lg:block w-64 border-r border-slate-800 bg-slate-950/90 py-6">
      <div className="px-6 mb-8">
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-[0.18em]">
          Workspace
        </h2>
      </div>

      <nav className="space-y-2 px-3">
        {menuItems.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                isActive(item.href)
                  ? 'bg-gradient-to-r from-cyan-500/20 to-blue-600/25 text-white font-semibold'
                  : 'text-slate-300 hover:bg-slate-800'
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="px-6 mt-12 pt-6 border-t border-slate-800">
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
          <h3 className="font-semibold text-slate-100 mb-2">
            Need Help?
          </h3>
          <p className="text-sm text-slate-400 mb-3">
            Check onboarding docs for deployment and server guides.
          </p>
          <button className="w-full bg-cyan-500 hover:bg-cyan-400 text-slate-950 py-2 rounded-lg transition-colors font-medium text-sm">
            View Docs
          </button>
        </div>
      </div>
    </aside>
  );
}
