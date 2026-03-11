import Link from "next/link";
import Footer from "../../components/Footer";

export default function RefundPage() {
  return (
    <div className="min-h-screen bg-[#020712] text-slate-100">
      <div className="mx-auto max-w-4xl px-6 py-14 sm:py-20">
        <Link href="/" className="text-sm text-cyan-200 hover:text-cyan-100">
          Back to Home
        </Link>
        <h1 className="mt-5 text-4xl font-semibold text-white">Refund Policy</h1>
        <p className="mt-3 text-sm text-slate-400">Last updated: March 11, 2026</p>

        <div className="mt-10 space-y-8 rounded-2xl border border-slate-800 bg-slate-900/70 p-6 sm:p-8">
          <section>
            <h2 className="text-xl font-semibold text-white">Refund Eligibility</h2>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              Refund requests are evaluated for first-time subscriptions and billing errors. Usage-heavy or abusive activity may not be eligible.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white">Refund Request Process</h2>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              Submit a request to support@thinksync.art with your account email, invoice details, and reason for refund. We review requests within 5 business days.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white">Subscription Cancellation</h2>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              You can cancel your subscription any time from your billing settings. Cancellation stops future renewals but does not automatically trigger a refund.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white">Payment Provider Notice (Paddle)</h2>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              Payments are processed by Paddle as Merchant of Record. Some refund rights may be governed by Paddle policies and local consumer law.
            </p>
          </section>
        </div>
      </div>
      <Footer />
    </div>
  );
}
