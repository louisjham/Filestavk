import { useState, useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { OctopusIcon } from "@/components/icons/OctopusIcon"
import { Sparkles, RefreshCw, Heart, Shield, Globe, Compass } from "lucide-react"
import { useAuth } from "@/lib/auth"
import { usePracticeProfile } from "@/hooks/usePracticeProfile"

interface AffirmationPayload {

  date: string
  greeting: string
  subtitle: string
  affirmation: {
    id: string
    category: string
    headline: string
    affirmation: string
    tentacle_tip: string
  }
  total_affirmations: number
}

export function KimbelDailyGreeting() {
  const { user } = useAuth()
  const { isDemo, firmName } = usePracticeProfile()
  const isAssistant = user?.role === "assistant"


  const { data: initialData, isLoading } = useQuery<AffirmationPayload>({
    queryKey: ["kimbel-daily-affirmation"],
    queryFn: () => api.affirmations.getDaily(),
    staleTime: 1000 * 60 * 60, // 1 hour
  })

  const [activeAffirmation, setActiveAffirmation] = useState<AffirmationPayload | null>(null)
  const [isShuffling, setIsShuffling] = useState(false)

  useEffect(() => {
    if (initialData && !activeAffirmation) {
      setActiveAffirmation(initialData)
    }
  }, [initialData, activeAffirmation])

  const handleShuffle = async () => {
    setIsShuffling(true)
    try {
      const fresh = await api.affirmations.getRandom()
      setActiveAffirmation(fresh)
    } catch (err) {
      console.error("Failed to fetch random affirmation", err)
    } finally {
      setIsShuffling(false)
    }
  }

  const current = activeAffirmation || initialData
  const aff = current?.affirmation

  const categoryBadgeLabel: Record<string, string> = {
    cephalopod_wit: "Cephalopod Wisdom",
    legal_defense: "Courtroom Armor",
    fresh_start: "Fresh Horizon",
  }

  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-950 via-slate-900 to-cyan-950/40 border border-cyan-500/25 p-6 shadow-lg shadow-cyan-950/20 transition-all duration-300">
      {/* Subtle ocean decorative glow */}
      <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-cyan-500/10 blur-3xl" />
      <div className="pointer-events-none absolute -left-12 -bottom-12 h-40 w-40 rounded-full bg-indigo-500/10 blur-2xl" />

      <div className="relative z-10 flex flex-col md:flex-row md:items-start justify-between gap-6">
        {/* Left: Avatar & Main Greeting */}
        <div className="flex items-start gap-4">
          <div className="relative flex-shrink-0">
            <div className="h-14 w-14 rounded-2xl bg-gradient-to-tr from-cyan-950 to-slate-900 border border-cyan-400/40 flex items-center justify-center shadow-inner group">
              <OctopusIcon size={32} className="text-cyan-400 drop-shadow-[0_0_8px_rgba(34,211,238,0.4)] transition-transform duration-300 group-hover:scale-110" />
            </div>
            <div className="absolute -bottom-1 -right-1 h-5 w-5 rounded-full bg-cyan-500 border-2 border-slate-950 flex items-center justify-center">
              <Heart className="h-2.5 w-2.5 text-slate-950 fill-slate-950" />
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-xl md:text-2xl font-bold tracking-tight text-white">
                {isAssistant ? "Good morning, Assistant" : (current?.greeting || "Good morning, Kimbel")}
              </h1>
              {aff?.category && (
                <Badge variant="outline" className="text-[10px] uppercase tracking-wider border-cyan-500/40 text-cyan-300 bg-cyan-950/50">
                  <Sparkles className="h-3 w-3 mr-1 text-cyan-400 inline" />
                  {categoryBadgeLabel[aff.category] || "Hemocyanin Resilience"}
                </Badge>
              )}
            </div>

            <p className="text-xs text-cyan-300/80 font-medium flex items-center gap-1.5">
              <Compass className="h-3 w-3 text-cyan-400" />
              {isAssistant ? "Scoped Defense Assistant Command" : `Corpus Christi • Nueces County Defense Command • ${firmName}`}
            </p>

          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2 self-start md:self-auto">
          <Button
            size="sm"
            variant="outline"
            onClick={handleShuffle}
            disabled={isShuffling || isLoading}
            className="text-xs gap-1.5 border-cyan-500/30 text-cyan-300 hover:bg-cyan-950/60 hover:text-cyan-100 hover:border-cyan-400/50 transition-colors"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isShuffling ? "animate-spin text-cyan-400" : ""}`} />
            Another Tentacle
          </Button>
        </div>
      </div>

      {/* Center: Curated Cephalopod Affirmation Banner */}
      {!isAssistant && aff && (
        <div className="mt-5 pt-4 border-t border-cyan-500/15">
          <div className="rounded-xl bg-slate-950/60 border border-cyan-500/20 p-4 backdrop-blur-xs transition-all duration-200">
            <div className="flex items-start gap-3">
              <div className="h-7 w-7 rounded-lg bg-cyan-950/80 border border-cyan-500/30 flex items-center justify-center shrink-0 mt-0.5">
                <Shield className="h-3.5 w-3.5 text-cyan-400" />
              </div>

              <div className="space-y-1.5 flex-1">
                <h3 className="text-sm font-semibold text-cyan-200 flex items-center gap-2">
                  <span>{aff.headline}</span>
                </h3>

                <p className="text-xs sm:text-sm text-slate-300 leading-relaxed font-normal">
                  {aff.affirmation}
                </p>

                {aff.tentacle_tip && (
                  <p className="text-xs text-cyan-400/90 italic pt-1 border-t border-cyan-500/10 flex items-center gap-1.5">
                    <span className="font-semibold not-italic text-cyan-300">Tentacle Tip:</span> {aff.tentacle_tip}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
