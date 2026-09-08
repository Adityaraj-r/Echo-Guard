export default function GlassCard({ children, className = "" }) {
  return (
    <section className={`rounded-lg border border-white/10 bg-white/[0.07] p-4 shadow-card backdrop-blur-xl md:p-5 ${className}`}>
      {children}
    </section>
  );
}
