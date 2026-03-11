import Link from "next/link";
import Footer from "@/components/Footer";

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-[#020712] text-slate-100">
      <div className="mx-auto max-w-4xl px-6 py-14 sm:py-20">
        <Link href="/" className="text-sm text-cyan-200 hover:text-cyan-100">
          Back to Home
        </Link>
        <h1 className="mt-5 text-4xl font-semibold text-white">Privacy Policy</h1>
        <p className="mt-3 text-sm text-slate-400">Last updated: March 11, 2026</p>

        <div className="mt-10 space-y-8 rounded-2xl border border-slate-800 bg-slate-900/70 p-6 sm:p-8">
          <section>
            <h2 className="text-xl font-semibold text-white">Data Collection</h2>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              ThinkSync collects account details, workspace metadata, infrastructure configuration inputs, and usage logs required to provide AI-powered DevOps services.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white">AI Request Logging</h2>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              We log AI prompts and responses for reliability, abuse prevention, and model quality improvement. Sensitive values should be masked where possible before submission.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white">Cookies</h2>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              We use essential cookies for authentication and session continuity. Additional cookies may be used for performance and product analytics.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white">Analytics</h2>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              Aggregated analytics are collected to understand feature usage, improve product quality, and monitor service performance.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white">Third-Party Services</h2>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              ThinkSync may use trusted third-party providers for hosting, payments, authentication, and analytics. These providers process data only as required for service delivery.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white">Security Practices</h2>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              We apply access controls, encrypted transport, and operational safeguards to protect user data. No security measure can guarantee absolute protection.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white">Contact</h2>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              Privacy-related requests can be sent to support@thinksync.art.
            </p>
          </section>
        </div>
      </div>
      <Footer />
    </div>
  );
}
