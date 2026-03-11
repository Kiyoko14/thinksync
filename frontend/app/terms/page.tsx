import Link from "next/link";
import Footer from "../../components/Footer";

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-[#020712] text-slate-100">
      <div className="mx-auto max-w-4xl px-6 py-14 sm:py-20">
        <Link href="/" className="text-sm text-cyan-200 hover:text-cyan-100">
          Back to Home
        </Link>
        <h1 className="mt-5 text-4xl font-semibold text-white">Terms of Service</h1>
        <p className="mt-3 text-sm text-slate-400">Last updated: March 11, 2026</p>

        <div className="mt-10 space-y-8 rounded-2xl border border-slate-800 bg-slate-900/70 p-6 sm:p-8">
          <section>
            <h2 className="text-xl font-semibold text-white">Acceptable Use</h2>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              You agree not to use ThinkSync for unlawful activity, unauthorized access, malware distribution, service abuse, or attempts to disrupt platform operations.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white">Account Responsibilities</h2>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              You are responsible for account security, credential management, and all activity under your organization workspace.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white">Service Availability Disclaimer</h2>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              ThinkSync is provided on an &ldquo;as is&rdquo; and &ldquo;as available&rdquo; basis. We may modify, suspend, or discontinue features without prior notice.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white">Limitation of Liability</h2>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              To the maximum extent permitted by law, ThinkSync is not liable for indirect, incidental, consequential, or punitive damages resulting from use of the service.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white">Governing Law</h2>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              These terms are governed by applicable laws of your service contract jurisdiction, unless local consumer protections require otherwise.
            </p>
          </section>
        </div>
      </div>
      <Footer />
    </div>
  );
}
