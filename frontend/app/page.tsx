"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import Link from "next/link";

const features = [
  {
    icon: "🔒",
    title: "Secure Infrastructure",
    description:
      "Bank-level security with encryption and compliance standards",
  },
  {
    icon: "⚡",
    title: "Lightning Fast",
    description:
      "High-performance infrastructure built for speed and reliability",
  },
  {
    icon: "🔌",
    title: "Easy Integration",
    description:
      "Seamlessly integrate with your existing tools and workflows",
  },
];

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    router.push("/dashboard");
  }, [router]);

  return (
    <div className="min-h-screen bg-white dark:bg-black">
      <section className="px-6 py-20 max-w-7xl mx-auto">
        <h1 className="text-5xl font-bold mb-6">
          ThinkSync AI DevOps Platform
        </h1>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 mt-16">
          {features.map((feature, index) => (
            <div key={index} className="border rounded-lg p-6">
              <div className="text-3xl mb-4">{feature.icon}</div>
              <h3 className="text-xl font-semibold mb-2">
                {feature.title}
              </h3>
              <p>{feature.description}</p>
            </div>
          ))}
        </div>

        <div className="mt-10">
          <Link href="/login" className="text-blue-600">
            Sign In
          </Link>
        </div>
      </section>
    </div>
  );
}
