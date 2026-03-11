import Link from "next/link";
import { Github, Mail } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t border-slate-800/90 bg-slate-950/90">
      <div className="mx-auto max-w-7xl px-6 py-12">
        <div className="grid gap-8 md:grid-cols-3">
          <div>
            <div className="mb-4 flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 text-sm font-bold text-white">
                TS
              </div>
              <p className="text-lg font-semibold text-white">ThinkSync</p>
            </div>
            <p className="max-w-sm text-sm text-slate-400">
              AI DevOps platform for managing servers, deployments, databases, and infrastructure automation.
            </p>
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

        <div className="mt-10 border-t border-slate-800 pt-6 text-sm text-slate-500">
          © 2026 ThinkSync. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
