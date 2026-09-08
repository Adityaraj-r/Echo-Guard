import { Activity, History, Mic, Moon, ShieldCheck, UploadCloud, Waves } from "lucide-react";

const navItems = [
  { id: "upload", label: "Upload", icon: UploadCloud },
  { id: "record", label: "Record", icon: Mic },
  { id: "analysis", label: "Analysis", icon: Waves },
  { id: "history", label: "History", icon: History },
];

export default function DashboardLayout({ activeSection, setActiveSection, children, status = "Ready" }) {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="fixed inset-0 -z-10 bg-[radial-gradient(circle_at_top_left,rgba(20,184,166,0.18),transparent_34%),linear-gradient(135deg,#070b12_0%,#111827_48%,#020617_100%)]" />
      <div className="flex min-h-screen">
        <aside className="hidden w-72 shrink-0 border-r border-white/10 bg-slate-950/70 p-5 backdrop-blur-xl lg:block">
          <Brand />
          <nav className="mt-10 space-y-2">
            {navItems.map((item) => (
              <NavButton key={item.id} item={item} active={activeSection === item.id} onClick={() => setActiveSection(item.id)} />
            ))}
          </nav>
        </aside>

        <section className="min-w-0 flex-1 pb-24 lg:pb-0">
          <header className="sticky top-0 z-20 border-b border-white/10 bg-slate-950/75 px-4 py-4 backdrop-blur-xl md:px-8">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-cyan-200">AI Deepfake Audio Detection</p>
                <h1 className="mt-2 text-2xl font-semibold text-white md:text-4xl">EchoGuard Forensic Console</h1>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Status icon={Activity} label="Pipeline" value={status} />
                <Status icon={Moon} label="Theme" value="Dark" />
              </div>
            </div>
          </header>
          {children}
        </section>
      </div>

      <nav className="fixed bottom-4 left-4 right-4 z-30 grid grid-cols-4 gap-2 rounded-lg border border-white/10 bg-slate-950/90 p-2 shadow-card backdrop-blur-xl lg:hidden">
        {navItems.map((item) => (
          <NavButton key={item.id} item={item} active={activeSection === item.id} compact onClick={() => setActiveSection(item.id)} />
        ))}
      </nav>
    </main>
  );
}

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div className="grid h-11 w-11 place-items-center rounded-lg border border-cyan-200/20 bg-cyan-300/10 text-cyan-200">
        <ShieldCheck size={24} />
      </div>
      <div>
        <p className="text-lg font-semibold text-white">EchoGuard</p>
        <p className="text-sm text-slate-400">Audio threat intelligence</p>
      </div>
    </div>
  );
}

function NavButton({ item, active, compact = false, onClick }) {
  const Icon = item.icon;
  return (
    <button className={`nav-item ${active ? "nav-item-active" : ""} ${compact ? "justify-center px-2" : ""}`} onClick={onClick} title={item.label}>
      <Icon size={18} />
      {!compact && <span>{item.label}</span>}
    </button>
  );
}

function Status({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.06] px-3 py-2">
      <Icon size={16} className="text-cyan-200" />
      <span className="text-sm text-slate-400">{label}</span>
      <span className="text-sm font-semibold text-slate-50">{value}</span>
    </div>
  );
}
