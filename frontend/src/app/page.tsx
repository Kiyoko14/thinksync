"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    router.push("/dashboard");
  }, [router]);
      description:
        'Bank-level security with encryption and compliance standards',
    },
    {
      icon: '⚡',
      title: 'Lightning Fast',
      description:
        'High-performance infrastructure built for speed and reliability',
    },
    {
      icon: '🔌',
      title: 'Easy Integration',
      description:
        'Seamlessly integrate with your existing tools and workflows',
    },
  ];

  return (
    <div className="min-h-screen bg-white dark:bg-black">
      {/* Hero Section */}
      <section className="relative overflow-hidden px-6 sm:px-8 lg:px-16 py-20 sm:py-32 max-w-7xl mx-auto">
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute w-96 h-96 bg-blue-400/20 rounded-full blur-3xl filter -top-40 -right-40"></div>
          <div className="absolute w-96 h-96 bg-purple-400/20 rounded-full blur-3xl filter -bottom-40 -left-40"></div>
        </div>

        <div className="relative z-10">
          <div className="text-center mb-12">
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold mb-6 bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
              AI DevOps Platform
            </h1>
            <p className="text-xl sm:text-2xl text-gray-600 dark:text-gray-400 max-w-3xl mx-auto mb-8">
              Automate your infrastructure with intelligent agents. Deploy, monitor, and scale with confidence.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                href="/register"
                className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white px-8 py-3 rounded-lg font-semibold transition-all transform hover:scale-105 inline-block"
              >
                Get Started Free
              </Link>
              <Link
                href="/login"
                className="bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 text-gray-900 dark:text-white px-8 py-3 rounded-lg font-semibold hover:bg-gray-50 dark:hover:bg-zinc-800 transition-colors inline-block"
              >
                Sign In
              </Link>
            </div>
          </div>

          {/* Preview Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-16">
            <div className="bg-gradient-to-br from-blue-50 to-purple-50 dark:from-zinc-900 dark:to-zinc-800 rounded-lg p-8 border border-blue-200 dark:border-zinc-700">
              <div className="text-4xl mb-4">📊</div>
              <h3 className="text-xl font-semibold mb-2">Dashboard</h3>
              <p className="text-gray-600 dark:text-gray-400">
                Real-time insights into your infrastructure performance
              </p>
            </div>
            <div className="bg-gradient-to-br from-purple-50 to-pink-50 dark:from-zinc-900 dark:to-zinc-800 rounded-lg p-8 border border-purple-200 dark:border-zinc-700">
              <div className="text-4xl mb-4">🤖</div>
              <h3 className="text-xl font-semibold mb-2">AI Agents</h3>
              <p className="text-gray-600 dark:text-gray-400">
                Intelligent automation for your DevOps workflows
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="bg-gray-50 dark:bg-zinc-950 py-20 sm:py-32 px-6 sm:px-8 lg:px-16">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl sm:text-5xl font-bold mb-6">
              Powerful Features
            </h2>
            <p className="text-xl text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
              Everything you need to manage your infrastructure efficiently
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <div
                key={index}
                className="bg-white dark:bg-zinc-900 rounded-lg p-8 border border-gray-200 dark:border-zinc-800 hover:shadow-lg dark:hover:shadow-gray-900/50 transition-all"
              >
                <div className="text-4xl mb-4">{feature.icon}</div>
                <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
                <p className="text-gray-600 dark:text-gray-400">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="px-6 sm:px-8 lg:px-16 py-20 sm:py-32 max-w-7xl mx-auto">
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-12 sm:p-16 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-6">
            Ready to Transform Your DevOps?
          </h2>
          <p className="text-lg text-blue-100 mb-8 max-w-2xl mx-auto">
            Join thousands of teams using ThinkSync to automate their infrastructure
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/register"
              className="bg-white text-blue-600 hover:bg-blue-50 px-8 py-3 rounded-lg font-semibold transition-colors inline-block"
            >
              Start Free Trial
            </Link>
            <Link
              href="#"
              className="bg-blue-500 hover:bg-blue-400 text-white px-8 py-3 rounded-lg font-semibold transition-colors inline-block"
            >
              View Pricing
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
