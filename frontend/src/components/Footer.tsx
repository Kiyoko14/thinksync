import Link from "next/link";
import { Github, Mail } from "lucide-react";

export default function Footer() {
  return (
    <footer className="relative overflow-hidden border-t border-slate-800/90 bg-slate-950/95">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_10%_20%,rgba(34,211,238,0.15),transparent_35%),radial-gradient(circle_at_85%_10%,rgba(37,99,235,0.18),transparent_45%)]" />

      <div className="relative mx-auto max-w-7xl px-6 py-14">
        <div className="mb-10 rounded-2xl border border-cyan-400/25 bg-gradient-to-r from-cyan-500/10 via-slate-900/70 to-blue-500/10 p-6 sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-cyan-200">Stay in control</p>
          <div className="mt-3 flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
            <p className="max-w-2xl text-sm text-slate-200 sm:text-base">
              ThinkSync unifies deployments, servers, and AI-assisted operations in one dependable workspace.
            </p>
            <Link
              href="/login"
              className="inline-flex items-center justify-center rounded-xl bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300"
            >
              Launch Dashboard
            </Link>
          </div>
        </div>

        <div className="grid gap-8 md:grid-cols-3">
          <div>
            <div className="mb-4 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 text-sm font-bold text-white shadow-lg shadow-cyan-500/20">
                TS
              </div>
              <p className="text-lg font-semibold text-white">ThinkSync</p>
            </div>
            <p className="max-w-sm text-sm leading-6 text-slate-300">
              AI DevOps platform for managing servers, deployments, databases, and infrastructure automation.
            </p>
            <div className="mt-5 flex flex-wrap gap-2 text-xs text-slate-300">
              <span className="rounded-full border border-slate-700 bg-slate-900/80 px-3 py-1">Secure Sessions</span>
              <span className="rounded-full border border-slate-700 bg-slate-900/80 px-3 py-1">Audit Friendly</span>
              <span className="rounded-full border border-slate-700 bg-slate-900/80 px-3 py-1">AI Workflows</span>
            </div>
          </div>

          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.14em] text-cyan-200">Legal</p>
            <ul className="mt-4 space-y-2 text-sm text-slate-300">
              <li>
                <Link href="/privacy" className="transition hover:text-cyan-200">
                  Privacy Policy
                </Link>
              </li>
              <li>
                <Link href="/refund" className="transition hover:text-cyan-200">
                  Refund Policy
                </Link>
              </li>
              <li>
                <Link href="/terms" className="transition hover:text-cyan-200">
                  Terms of Service
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.14em] text-cyan-200">Contact</p>
            <div className="mt-4 space-y-3 text-sm text-slate-300">
              <a
                href="mailto:support@thinksync.art"
                className="flex items-center gap-2 transition hover:text-cyan-200"
              >
                <Mail className="h-4 w-4" />
                support@thinksync.art
              </a>
              <a
                href="https://github.com/Kiyoko14/thinksync"
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2 transition hover:text-cyan-200"
              >
                <Github className="h-4 w-4" />
                GitHub
              </a>
            </div>
          </div>
        </div>

        <div className="mt-10 flex flex-col gap-3 border-t border-slate-800 pt-6 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
          <p>© 2026 ThinkSync. All rights reserved.</p>
          <p>Built for modern platform teams.</p>
        </div>
      </div>
    </footer>
  );
}
