type BrandLogoProps = {
  compact?: boolean;
};

export default function BrandLogo({ compact = false }: BrandLogoProps) {
  return (
    <div className="flex items-center gap-3">
      <div className="relative h-10 w-10 shrink-0 overflow-hidden rounded-xl border border-cyan-300/35 bg-slate-900">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(34,211,238,0.45),transparent_45%),radial-gradient(circle_at_80%_80%,rgba(59,130,246,0.4),transparent_50%)]" />
        <svg viewBox="0 0 48 48" className="relative h-full w-full p-1.5 text-cyan-100" aria-hidden="true">
          <path d="M9 29c6-12 24-12 30 0" fill="none" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" />
          <circle cx="15" cy="20" r="3.2" fill="currentColor" />
          <circle cx="33" cy="20" r="3.2" fill="currentColor" />
          <path d="M15 31h18" fill="none" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" />
        </svg>
      </div>
      {!compact && (
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Platform</p>
          <p className="text-lg font-semibold text-white">ThinkSync</p>
        </div>
      )}
    </div>
  );
}