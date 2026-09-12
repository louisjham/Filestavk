import { useState } from "react"
import { useAuth } from "@/lib/auth.tsx"
import { useLocation, Link } from "react-router-dom"
import { LogOut, Sparkles, User, Lock, ArrowLeftRight, Check } from "lucide-react"
import { Button } from "@/components/ui/button"
import { OctopusIcon } from "@/components/icons/OctopusIcon"
import { PracticeOverviewModal } from "@/components/story/PracticeOverviewModal"

const routeTitles: Record<string, string> = {
  "/": "Practice Morning Briefing",
  "/clients": "Clients",
  "/cases": "Case Management & Dockets",
  "/documents": "Documents",
  "/ingestion": "Ingestion Hub",
  "/ingestion/portal": "Nueces Portal Assist",
  "/vouchers": "Voucher Command Center",
  "/spreadsheet": "Master Spreadsheet & Voucher Queue",
  "/research": "Courts & Legal Research",
  "/search": "Search & Notes",
  "/analytics": "Practice Analytics",
  "/settings": "Attorney Credentials",
}

export function Topbar() {
  const { user, switchRole, logout } = useAuth()
  const location = useLocation()
  const [showStoryModal, setShowStoryModal] = useState(false)
  const [switching, setSwitching] = useState(false)

  const isAssistant = user?.role === "assistant"

  let title = "Filestavk"
  for (const [path, label] of Object.entries(routeTitles)) {
    if (path === "/" ? location.pathname === "/" : location.pathname.startsWith(path)) {
      title = label
    }
  }

  const handleToggleRole = async () => {
    setSwitching(true)
    try {
      if (isAssistant) {
        await switchRole("attorney")
      } else {
        await switchRole("assistant")
      }
    } finally {
      setSwitching(false)
    }
  }

  return (
    <>
      <div className="h-13 border-b border-border bg-card flex items-center justify-between px-6 shrink-0 shadow-xs">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold text-foreground tracking-tight">{title}</h2>
          {isAssistant && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1 font-semibold">
              <Lock className="h-3 w-3" /> Assistant Mode (Vouchers &amp; Intake Only)
            </span>
          )}
        </div>

        <div className="flex items-center gap-2.5 sm:gap-3.5">
          {/* Space-Level Story Tour Button */}
          <Button
            size="sm"
            variant="outline"
            onClick={() => setShowStoryModal(true)}
            className="h-8 text-xs gap-1.5 border-cyan-500/30 text-cyan-300 bg-cyan-950/20 hover:bg-cyan-950/50 shadow-xs font-medium"
          >
            <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
            <span className="hidden sm:inline">Practice Story Tour</span>
          </Button>

          {/* 1-Click Persona Switcher for Demos */}
          <Button
            size="sm"
            variant="ghost"
            onClick={handleToggleRole}
            disabled={switching}
            title={isAssistant ? "Switch to Kimbel (Attorney View)" : "Switch to Assistant (Scoped View)"}
            className="h-8 text-xs gap-1.5 text-muted-foreground hover:text-foreground border border-border/60 bg-muted/20"
          >
            <ArrowLeftRight className="h-3.5 w-3.5" />
            <span className="text-[11px] font-medium hidden md:inline">
              {isAssistant ? "Switch: Attorney" : "Switch: Assistant"}
            </span>
          </Button>

          {/* User Profile Pill */}
          {!isAssistant ? (
            <Link
              to="/settings"
              className="flex items-center gap-2.5 px-3 py-1 rounded-full bg-secondary/60 hover:bg-secondary border border-border/80 transition-colors group"
            >
              <div className="h-6 w-6 rounded-full bg-cyan-950/40 border border-cyan-500/40 flex items-center justify-center shadow-xs">
                <OctopusIcon size={16} className="text-cyan-400 group-hover:scale-110 transition-transform" />
              </div>
              <div className="flex flex-col text-left leading-tight">
                <span className="text-xs font-semibold text-foreground group-hover:text-primary transition-colors">
                  Kimbel Brandon, Esq.
                </span>
                <span className="text-[9px] text-cyan-400/90 font-medium">
                  Hemocyanin Law
                </span>
              </div>
            </Link>
          ) : (
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30">
              <div className="h-6 w-6 rounded-full bg-amber-500/20 flex items-center justify-center text-amber-300 font-bold text-xs">
                A
              </div>
              <div className="flex flex-col text-left leading-tight">
                <span className="text-xs font-semibold text-foreground">
                  Alex (Assistant)
                </span>
                <span className="text-[9px] text-amber-300 font-medium">
                  Scoped Access
                </span>
              </div>
            </div>
          )}

          <Button variant="ghost" size="icon" onClick={logout} title="Sign out" className="h-8 w-8 text-muted-foreground hover:text-foreground">
            <LogOut className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Interactive Story Tour Modal */}
      <PracticeOverviewModal
        isOpen={showStoryModal}
        onClose={() => setShowStoryModal(false)}
      />
    </>
  )
}
