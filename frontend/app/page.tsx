import Link from "next/link";
import {
  Bot,
  Server,
  Rocket,
  Database,
  Activity,
  MessageSquare,
  Check,
  ArrowRight,
} from "lucide-react";
import Footer from "../components/Footer";

const features = [
  {
    icon: Bot,
    title: "AI DevOps Assistant",
    description: "Run infrastructure workflows through AI-guided automation and context-aware suggestions.",
  },
  {
    icon: Server,
    title: "Server Management",
    description: "Manage fleets, SSH access, and environment state across all your production systems.",
  },
  {
    icon: Rocket,
    title: "One-Click Deployments",
    description: "Ship updates faster with repeatable deployment pipelines and clear rollout visibility.",
  },
  {
    icon: Database,
    title: "Database Provisioning",
    description: "Create and configure databases for apps with secure credentials and lifecycle controls.",
  },
  {
    icon: Activity,
    title: "Real-time Monitoring",
    description: "Track service health, uptime, and deployment status with low-latency telemetry insights.",
  },
  {
    icon: MessageSquare,
    title: "AI Chat for Infrastructure",
    description: "Collaborate with your infrastructure agent using natural language and auditable actions.",
  },
];

const steps = [
  {
    title: "Connect your infrastructure",
    description: "Add servers and environments in minutes with secure access and configuration checks.",
  },
  {
    title: "Automate with AI workflows",
    description: "Trigger deployments, diagnostics, and maintenance tasks from one intelligent control panel.",
  },
  {
    title: "Monitor and iterate",
    description: "Observe changes in real time, reduce incidents, and improve delivery speed continuously.",
  },
];

const testimonials = [
  {
    quote: "ThinkSync gave our team one place to manage infra, deploy code, and automate repetitive ops.",
    name: "Lena Park",
    role: "Engineering Manager, Driftlane",
  },
  {
    quote: "The AI assistant catches risky actions early and saves us hours every week on operations.",
    name: "Rafael Costa",
    role: "Platform Lead, Orbitbase",
  },
  {
    quote: "We replaced scattered scripts with a reliable DevOps workspace that scales with our product.",
    name: "Nina Shah",
    role: "CTO, HelioStack",
  },
];

const plans = [
  {
    name: "Free",
    price: "$0",
    frequency: "/month",
    description: "For solo builders and early prototypes.",
    features: ["1 team member", "Up to 2 servers", "Basic monitoring", "Community support"],
    cta: "Start Free",
    href: "/login",
    featured: false,
  },
  {
    name: "Pro",
    price: "$39",
    frequency: "/month",
    description: "For teams running production workloads.",
    features: ["Unlimited team members", "Unlimited servers", "Priority AI workflows", "Advanced monitoring"],
    cta: "Upgrade to Pro",
    href: "/login",
    featured: true,
  },
];

export default function Home() {
  return (
    <div className="min-h-screen bg-[#020712] text-slate-100">
      <div className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(circle_at_20%_10%,rgba(6,182,212,0.25),transparent_30%),radial-gradient(circle_at_80%_0%,rgba(14,116,144,0.28),transparent_40%),radial-gradient(circle_at_50%_80%,rgba(15,23,42,0.9),transparent_65%)]" />

      <main>
        <section className="mx-auto max-w-7xl px-6 pb-20 pt-12 sm:pb-28 sm:pt-16">
          <div className="rounded-full border border-cyan-400/30 bg-cyan-400/10 px-4 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-cyan-200 w-fit">
            ThinkSync Platform
          </div>
          <h1 className="mt-6 max-w-4xl text-4xl font-semibold leading-tight text-white sm:text-6xl">
            AI-Powered DevOps for Modern Teams
          </h1>
          <p className="mt-6 max-w-2xl text-base text-slate-300 sm:text-lg">
            ThinkSync helps teams manage servers, run reliable deployments, provision databases, and automate infrastructure workflows with AI-driven precision.
          </p>
          <div className="mt-10 flex flex-col gap-4 sm:flex-row">
            <Link
              href="/login"
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-6 py-3 text-sm font-semibold text-white transition hover:from-cyan-400 hover:to-blue-500"
            >
              Start Free
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/dashboard"
              className="inline-flex items-center justify-center rounded-xl border border-slate-700 bg-slate-900/60 px-6 py-3 text-sm font-semibold text-slate-100 transition hover:border-cyan-300/40 hover:bg-slate-800"
            >
              View Dashboard
            </Link>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-6 py-12 sm:py-16">
          <div className="mb-10">
            <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/80">Features</p>
            <h2 className="mt-2 text-3xl font-semibold text-white">Everything you need to run DevOps at scale</h2>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <article
                  key={feature.title}
                  className="rounded-2xl border border-slate-800/80 bg-slate-900/65 p-6 transition duration-300 hover:-translate-y-1 hover:border-cyan-400/35"
                >
                  <div className="mb-5 inline-flex rounded-xl border border-cyan-400/30 bg-cyan-400/10 p-2">
                    <Icon className="h-5 w-5 text-cyan-200" />
                  </div>
                  <h3 className="text-lg font-semibold text-white">{feature.title}</h3>
                  <p className="mt-3 text-sm text-slate-300">{feature.description}</p>
                </article>
              );
            })}
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-6 py-14 sm:py-20">
          <div className="mb-10">
            <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/80">How It Works</p>
            <h2 className="mt-2 text-3xl font-semibold text-white">From setup to shipping in three steps</h2>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {steps.map((step, index) => (
              <article key={step.title} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-cyan-300">Step {index + 1}</p>
                <h3 className="mt-3 text-lg font-semibold text-white">{step.title}</h3>
                <p className="mt-3 text-sm text-slate-300">{step.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-6 py-14 sm:py-20">
          <div className="mb-10">
            <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/80">Testimonials</p>
            <h2 className="mt-2 text-3xl font-semibold text-white">Trusted by modern engineering teams</h2>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {testimonials.map((item) => (
              <article key={item.name} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
                <p className="text-sm text-slate-200">&ldquo;{item.quote}&rdquo;</p>
                <p className="mt-6 font-semibold text-white">{item.name}</p>
                <p className="text-sm text-slate-400">{item.role}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-6 pb-20 pt-12 sm:pb-24">
          <div className="mb-10">
            <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/80">Pricing</p>
            <h2 className="mt-2 text-3xl font-semibold text-white">Simple plans for every stage</h2>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {plans.map((plan) => (
              <article
                key={plan.name}
                className={`rounded-2xl border p-6 sm:p-8 ${
                  plan.featured
                    ? "border-cyan-400/40 bg-gradient-to-b from-cyan-500/10 to-slate-900/80"
                    : "border-slate-800 bg-slate-900/65"
                }`}
              >
                <p className="text-sm font-semibold uppercase tracking-[0.14em] text-cyan-200">{plan.name}</p>
                <div className="mt-3 flex items-end gap-2">
                  <p className="text-4xl font-semibold text-white">{plan.price}</p>
                  <p className="pb-1 text-sm text-slate-400">{plan.frequency}</p>
                </div>
                <p className="mt-3 text-sm text-slate-300">{plan.description}</p>
                <ul className="mt-6 space-y-3">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-center gap-2 text-sm text-slate-200">
                      <Check className="h-4 w-4 text-cyan-300" />
                      {feature}
                    </li>
                  ))}
                </ul>
                <Link
                  href={plan.href}
                  className={`mt-8 inline-flex w-full items-center justify-center rounded-xl px-5 py-3 text-sm font-semibold transition ${
                    plan.featured
                      ? "bg-cyan-500 text-slate-950 hover:bg-cyan-400"
                      : "border border-slate-700 bg-slate-900 text-slate-100 hover:border-cyan-300/40"
                  }`}
                >
                  {plan.cta}
                </Link>
              </article>
            ))}
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
