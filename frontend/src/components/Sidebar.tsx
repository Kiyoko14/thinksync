import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function Sidebar() {
  const pathname = usePathname();

  const isActive = (path: string) => pathname.startsWith(path);

  const menuItems = [
    { href: '/dashboard', label: 'Dashboard', icon: '📊' },
    { href: '/servers', label: 'Servers', icon: '🖥️' },
    { href: '/agents', label: 'Agents', icon: '🤖' },
    { href: '/chats', label: 'Deployments', icon: '🚀' },
    { href: '/settings', label: 'Settings', icon: '⚙️' },
  ];

  return (
    <aside className="hidden lg:block w-64 bg-white dark:bg-zinc-950 border-r border-gray-200 dark:border-zinc-800 py-6">
      <div className="px-6 mb-8">
        <h2 className="text-sm font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
          Menu
        </h2>
      </div>

      <nav className="space-y-2 px-3">
        {menuItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
              isActive(item.href)
                ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 font-semibold'
                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-zinc-800'
            }`}
          >
            <span className="text-xl">{item.icon}</span>
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>

      <div className="px-6 mt-12 pt-6 border-t border-gray-200 dark:border-zinc-800">
        <div className="bg-blue-50 dark:bg-blue-900/10 rounded-lg p-4">
          <h3 className="font-semibold text-blue-900 dark:text-blue-300 mb-2">
            Need Help?
          </h3>
          <p className="text-sm text-blue-800 dark:text-blue-200 mb-3">
            Check our documentation for guides and tutorials.
          </p>
          <button className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg transition-colors font-medium text-sm">
            View Docs
          </button>
        </div>
      </div>
    </aside>
  );
}
