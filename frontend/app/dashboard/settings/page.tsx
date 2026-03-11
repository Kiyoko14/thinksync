"use client";

import { useRouter } from "next/navigation";
import { KeyRound, Mail, Trash2, LogOut } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

export default function SettingsPage() {
  const router = useRouter();
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
    router.replace("/login");
  };

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-800 bg-slate-900/75 p-6 sm:p-8">
        <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Account Settings</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">Profile and Security</h1>
        <p className="mt-3 max-w-2xl text-sm text-slate-300">
          Manage your account details, session access, and account lifecycle actions.
        </p>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
          <div className="mb-4 inline-flex rounded-lg border border-cyan-400/30 bg-cyan-500/10 p-2">
            <Mail className="h-4 w-4 text-cyan-200" />
          </div>
          <h2 className="text-lg font-semibold text-white">Account Email</h2>
          <p className="mt-2 text-sm text-slate-400">This email is used for login and billing communication.</p>
          <div className="mt-4 rounded-xl border border-slate-700 bg-slate-800/80 px-4 py-3 text-sm text-slate-200">
            {user?.email ?? "No email available"}
          </div>
        </article>

        <article className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
          <div className="mb-4 inline-flex rounded-lg border border-cyan-400/30 bg-cyan-500/10 p-2">
            <KeyRound className="h-4 w-4 text-cyan-200" />
          </div>
          <h2 className="text-lg font-semibold text-white">Change Password</h2>
          <p className="mt-2 text-sm text-slate-400">
            Password management will be available in a dedicated identity settings flow.
          </p>
          <button
            type="button"
            className="mt-4 rounded-xl border border-slate-700 px-4 py-2 text-sm font-medium text-slate-200 transition hover:border-cyan-300/40 hover:bg-slate-800"
          >
            Change Password (Coming Soon)
          </button>
        </article>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
          <div className="mb-4 inline-flex rounded-lg border border-emerald-400/30 bg-emerald-500/10 p-2">
            <LogOut className="h-4 w-4 text-emerald-200" />
          </div>
          <h2 className="text-lg font-semibold text-white">Session</h2>
          <p className="mt-2 text-sm text-slate-400">Sign out from this device at any time.</p>
          <button
            type="button"
            onClick={handleLogout}
            className="mt-4 rounded-xl border border-slate-700 px-4 py-2 text-sm font-medium text-slate-200 transition hover:border-emerald-300/40 hover:bg-slate-800"
          >
            Logout
          </button>
        </article>

        <article className="rounded-2xl border border-rose-500/30 bg-rose-500/5 p-6">
          <div className="mb-4 inline-flex rounded-lg border border-rose-400/40 bg-rose-500/10 p-2">
            <Trash2 className="h-4 w-4 text-rose-200" />
          </div>
          <h2 className="text-lg font-semibold text-white">Delete Account</h2>
          <p className="mt-2 text-sm text-slate-300">
            Account deletion is permanent and will remove access to ThinkSync workspaces and data.
          </p>
          <button
            type="button"
            className="mt-4 rounded-xl border border-rose-400/40 px-4 py-2 text-sm font-medium text-rose-100 transition hover:bg-rose-500/10"
          >
            Delete Account (Placeholder)
          </button>
        </article>
      </section>
    </div>
  );
}
