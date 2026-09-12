import { Link, useLocation } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { useAuth } from "@/lib/auth.tsx"
import { api } from "@/lib/api"
import {
  LayoutDashboard,
  DollarSign,
  Users,
  Scale,
  FileText,
  Download,
  Search,
  BarChart2,
  Settings,
  Globe,
  Lock,
  ClipboardList,
  FileSpreadsheet,
  BookOpen,
} from "lucide-react"
import { OctopusIcon } from "@/components/icons/OctopusIcon"
import { cn } from "@/lib/utils.ts"

const attorneyNavItems = [
  { to: "/",                 icon: LayoutDashboard, label: "Morning Briefing" },
  { to: "/spreadsheet",      icon: FileSpreadsheet, label: "Master Spreadsheet" },
  { to: "/vouchers",         icon: DollarSign,      label: "Voucher Radar", isVoucher: true },
  { to: "/cases",            icon: Scale,           label: "Cases & Dockets" },
  { to: "/clients",          icon: Users,           label: "Clients" },
  { to: "/documents",        icon: FileText,        label: "Documents" },
  { to: "/ingestion/portal", icon: Globe,           label: "Nueces Portal Assist" },
  { to: "/research",         icon: BookOpen,        label: "Courts & Research" },
  { to: "/ingestion",        icon: Download,        label: "Ingestion Hub" },
  { to: "/search",           icon: Search,          label: "Search & Notes" },
  { to: "/analytics",        icon: BarChart2,       label: "Practice Analytics" },
  { to: "/settings",         icon: Settings,        label: "Attorney Credentials" },
]

const assistantNavItems = [
  { to: "/",                 icon: ClipboardList,   label: "Delegated Work Queue" },
  { to: "/spreadsheet",      icon: FileSpreadsheet, label: "Master Spreadsheet" },
  { to: "/vouchers",         icon: DollarSign,      label: "Voucher Radar", isVoucher: true },
  { to: "/cases",            icon: Scale,           label: "Cases & Dockets" },
  { to: "/ingestion/portal", icon: Globe,           label: "Nueces Portal Assist" },
  { to: "/research",         icon: BookOpen,        label: "Courts & Research" },
  { to: "/ingestion",        icon: Download,        label: "Ingestion Hub" },
  { to: "/search",           icon: Search,          label: "Search & Notes" },
]

export function Sidebar() {
  const { user } = useAuth()
  const location = useLocation()

  const isAssistant = user?.role === "assistant"
  const activeNavItems = isAssistant ? assistantNavItems : attorneyNavItems

  const { data: stats } = useQuery({
    queryKey: ["voucher-stats"],
    queryFn: () => api.vouchers.stats(),
    refetchInterval: 15000,
  })

  return (
    <aside className="flex h-screen w-60 flex-col border-r border-sidebar-border bg-sidebar shrink-0">
      {/* Brand Header */}
      <div className="flex h-14 items-center gap-2.5 border-b border-sidebar-border px-4 bg-sidebar/50">
        <div className="h-8 w-8 rounded-lg bg-cyan-950/40 border border-cyan-500/30 flex items-center justify-center shrink-0">
          <OctopusIcon size={20} className="text-cyan-400" />
        </div>
        <div>
          <span className="text-sm font-bold text-sidebar-foreground tracking-tight block leading-none">
            Hemocyanin Law
          </span>
          <span className="text-[10px] text-cyan-400/90 font-medium">
            {isAssistant ? "Assistant Workspace" : "Filestavk &bull; Corpus Christi"}
          </span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-1">
        {activeNavItems.map(({ to, icon: Icon, label, isVoucher }: any) => {
          const active =
            to === "/" ? location.pathname === "/" : location.pathname.startsWith(to)
          return (
            <Link
              key={to}
              to={to}
              className={cn(
                "flex items-center justify-between rounded-md px-3 py-2 text-xs transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground font-semibold shadow-xs"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
              )}
            >
              <div className="flex items-center gap-2.5">
                <Icon className={`h-4 w-4 shrink-0 ${isVoucher ? "text-emerald-400" : ""}`} />
                <span>{label}</span>
              </div>
              {isVoucher && ((stats?.returned_count ?? 0) + (stats?.missing_appointment_orders_count ?? 0)) > 0 ? (
                <span className="px-1.5 py-0.2 rounded-full bg-red-500 text-white text-[10px] font-bold animate-pulse">
                  {(stats.returned_count ?? 0) + (stats.missing_appointment_orders_count ?? 0)}
                </span>
              ) : null}
            </Link>
          )
        })}
      </nav>

      {/* Footer Practice Badge */}
      <div className="border-t border-sidebar-border px-4 py-3 text-[11px] text-sidebar-foreground/60 space-y-1">
        {!isAssistant ? (
          <>
            <div className="flex items-center justify-between text-[11px]">
              <span className="font-semibold text-sidebar-foreground/90">Kimbel Brandon, Esq.</span>
              <span className="text-[10px] text-cyan-400/80">#24098742</span>
            </div>
            <div className="text-[10px] text-sidebar-foreground/50">Nueces County &bull; Texas State Bar</div>
          </>
        ) : (
          <>
            <div className="flex items-center justify-between text-[11px]">
              <span className="font-semibold text-amber-300">Alex (Assistant)</span>
              <span className="text-[10px] text-muted-foreground flex items-center gap-0.5">
                <Lock className="h-2.5 w-2.5 text-amber-400" /> Scoped
              </span>
            </div>
            <div className="text-[10px] text-sidebar-foreground/50">Voucher &amp; Intake Delegation Queue</div>
          </>
        )}
      </div>
    </aside>
  )
}
