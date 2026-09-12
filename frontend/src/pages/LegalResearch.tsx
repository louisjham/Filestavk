import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  BookOpen,
  Scale,
  Phone,
  Building2,
  ExternalLink,
  Search,
  FileText,
  Shield,
  Clock,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
} from "lucide-react"

export function LegalResearch() {
  const [activeTab, setActiveTab] = useState<"directory" | "statutes" | "caselaw">("directory")
  const [courtTypeFilter, setCourtTypeFilter] = useState<string>("")
  const [statuteSearch, setStatuteSearch] = useState("")
  const [caselawQuery, setCaselawQuery] = useState("Michael Morton Act discovery")
  const [caselawCourt, setCaselawCourt] = useState("texapp-13")
  const [copiedPhone, setCopiedPhone] = useState<string | null>(null)

  // 1. Directory Query
  const { data: directoryData, isLoading: directoryLoading } = useQuery({
    queryKey: ["nueces-directory", courtTypeFilter],
    queryFn: () => api.research.getDirectory(courtTypeFilter || undefined),
  })

  // 2. Statutes Query
  const { data: statutesData, isLoading: statutesLoading } = useQuery({
    queryKey: ["texas-statutes", statuteSearch],
    queryFn: () => api.research.getStatutes(statuteSearch || undefined),
  })

  // 3. CourtListener Case Law Query
  const { data: caselawData, isLoading: caselawLoading, refetch: refetchCaselaw } = useQuery({
    queryKey: ["courtlistener-search", caselawQuery, caselawCourt],
    queryFn: () => api.research.searchCourtListener(caselawQuery, caselawCourt),
    enabled: caselawQuery.length >= 3,
  })

  const handleCopyPhone = (phone: string, id: string) => {
    navigator.clipboard.writeText(phone)
    setCopiedPhone(id)
    setTimeout(() => setCopiedPhone(null), 2000)
  }

  const courts = directoryData?.courts || []
  const statutes = statutesData?.statutes || []
  const caselawResults = caselawData?.results || []

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-cyan-950/40 to-slate-900 border border-cyan-500/20 p-6 rounded-xl shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-cyan-950/80 border border-cyan-500/40 flex items-center justify-center shrink-0">
                <BookOpen className="h-5 w-5 text-cyan-400" />
              </div>
              <div>
                <h1 className="text-xl font-bold tracking-tight text-foreground">
                  Nueces County Courts &amp; Texas Criminal Legal Research
                </h1>
                <p className="text-xs text-cyan-300/80 font-medium">
                  Courthouse Directory &bull; Michael Morton Act 39.14 &bull; Art. 17.151 Bail Caps &bull; Free CourtListener Case Law
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              asChild
              size="sm"
              variant="outline"
              className="text-xs gap-1.5 border-cyan-500/30 text-cyan-300 hover:bg-cyan-950/40"
            >
              <a
                href="https://statutes.capitol.texas.gov/"
                target="_blank"
                rel="noreferrer"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                Texas Statutes Online
              </a>
            </Button>
            <Button
              asChild
              size="sm"
              className="text-xs gap-1.5 bg-cyan-600 hover:bg-cyan-500 text-white font-medium"
            >
              <a
                href="https://www.courtlistener.com/"
                target="_blank"
                rel="noreferrer"
              >
                <Scale className="h-3.5 w-3.5" />
                CourtListener (Free Law Project)
              </a>
            </Button>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-3 border-b border-border pb-3">
        <Button
          variant={activeTab === "directory" ? "default" : "outline"}
          onClick={() => setActiveTab("directory")}
          className="text-xs gap-1.5 h-9 font-semibold"
        >
          <Building2 className="h-4 w-4 text-cyan-400" />
          Nueces County Court Directory (8 District + 5 CCL)
        </Button>

        <Button
          variant={activeTab === "statutes" ? "default" : "outline"}
          onClick={() => setActiveTab("statutes")}
          className="text-xs gap-1.5 h-9"
        >
          <Shield className="h-4 w-4 text-emerald-400" />
          Texas Criminal Statutes (Morton Act &bull; 17.151 Bail &bull; Penal Code)
        </Button>

        <Button
          variant={activeTab === "caselaw" ? "default" : "outline"}
          onClick={() => setActiveTab("caselaw")}
          className="text-xs gap-1.5 h-9"
        >
          <Scale className="h-4 w-4 text-purple-400" />
          Free Case Law Search (13th COA Corpus Christi &amp; CCA)
        </Button>
      </div>

      {/* TAB 1: NUECES COURT DIRECTORY */}
      {activeTab === "directory" && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant={courtTypeFilter === "" ? "default" : "outline"}
                className="text-xs h-8"
                onClick={() => setCourtTypeFilter("")}
              >
                All ({courts.length})
              </Button>
              <Button
                size="sm"
                variant={courtTypeFilter === "DISTRICT_COURT" ? "default" : "outline"}
                className="text-xs h-8"
                onClick={() => setCourtTypeFilter("DISTRICT_COURT")}
              >
                District Courts (Felony)
              </Button>
              <Button
                size="sm"
                variant={courtTypeFilter === "COUNTY_COURT_AT_LAW" ? "default" : "outline"}
                className="text-xs h-8"
                onClick={() => setCourtTypeFilter("COUNTY_COURT_AT_LAW")}
              >
                County Courts at Law (Misdemeanor)
              </Button>
              <Button
                size="sm"
                variant={courtTypeFilter === "OFFICIAL" ? "default" : "outline"}
                className="text-xs h-8"
                onClick={() => setCourtTypeFilter("OFFICIAL")}
              >
                Clerks &amp; Auditor
              </Button>
            </div>

            <span className="text-xs text-muted-foreground">
              Courthouse: 901 Leopard St, Corpus Christi, TX 78401
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {courts.map((c: any, idx: number) => {
              const isCopied = copiedPhone === `phone-${idx}`
              return (
                <Card key={idx} className="border-border/80 hover:border-cyan-500/40 transition-colors bg-card">
                  <CardHeader className="pb-2.5">
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-0.5">
                        <CardTitle className="text-sm font-bold text-foreground">
                          {c.name}
                        </CardTitle>
                        <div className="text-xs text-cyan-400 font-medium">{c.judge}</div>
                      </div>
                      <Badge
                        variant={c.type === "DISTRICT_COURT" ? "default" : c.type === "COUNTY_COURT_AT_LAW" ? "secondary" : "outline"}
                        className="text-[10px] px-1.5 py-0"
                      >
                        {c.type === "DISTRICT_COURT" ? "District" : c.type === "COUNTY_COURT_AT_LAW" ? "CCL" : "Official"}
                      </Badge>
                    </div>
                    <CardDescription className="text-[11px]">
                      {c.jurisdiction} &bull; {c.courtroom}
                    </CardDescription>
                  </CardHeader>

                  <CardContent className="space-y-2.5 text-xs pt-0">
                    <div className="p-2 rounded bg-secondary/40 border border-border flex items-center justify-between">
                      <div className="space-y-0.5">
                        <span className="text-[10px] text-muted-foreground block">{c.coordinator}</span>
                        <span className="font-mono font-bold text-foreground">{c.phone}</span>
                      </div>
                      <button
                        onClick={() => handleCopyPhone(c.phone, `phone-${idx}`)}
                        className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                        title="Copy phone number"
                      >
                        {isCopied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                      </button>
                    </div>

                    <p className="text-[11px] text-muted-foreground leading-relaxed">
                      {c.notes}
                    </p>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </div>
      )}

      {/* TAB 2: TEXAS STATUTES CORPUS */}
      {activeTab === "statutes" && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="relative w-full sm:w-80">
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search Morton Act, 17.151 bail, drug laws..."
                value={statuteSearch}
                onChange={(e) => setStatuteSearch(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 text-xs rounded-md bg-background border border-border focus:border-cyan-400 focus:outline-hidden"
              />
            </div>
            <span className="text-xs text-muted-foreground">
              Showing {statutes.length} core Texas criminal procedure &amp; penal codes
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {statutes.map((s: any, idx: number) => (
              <Card key={idx} className="border-border/80 bg-card hover:border-emerald-500/40 transition-colors">
                <CardHeader className="pb-2.5">
                  <div className="flex items-start justify-between gap-2">
                    <div className="space-y-0.5">
                      <Badge variant="outline" className="text-[10px] text-emerald-400 border-emerald-500/30 bg-emerald-950/40 mb-1">
                        {s.code}
                      </Badge>
                      <CardTitle className="text-sm font-bold text-foreground">
                        {s.title}
                      </CardTitle>
                    </div>
                    <Button asChild size="sm" variant="ghost" className="h-7 text-xs text-primary gap-1">
                      <a href={s.full_text_url} target="_blank" rel="noreferrer">
                        Read Statute <ExternalLink className="h-3 w-3" />
                      </a>
                    </Button>
                  </div>
                  <CardDescription className="text-[11px]">
                    Category: {s.category}
                  </CardDescription>
                </CardHeader>

                <CardContent className="space-y-3 text-xs pt-0">
                  <p className="text-muted-foreground leading-relaxed text-[11px]">
                    {s.summary}
                  </p>

                  <div className="space-y-1 bg-secondary/30 p-2.5 rounded border border-border">
                    <span className="text-[10px] font-bold text-foreground uppercase tracking-wider block">
                      Core Defense Elements:
                    </span>
                    <ul className="space-y-1 text-[11px] text-muted-foreground list-disc list-inside">
                      {s.key_elements.map((el: string, elIdx: number) => (
                        <li key={elIdx}>{el}</li>
                      ))}
                    </ul>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: FREE COURTLISTENER CASE LAW */}
      {activeTab === "caselaw" && (
        <div className="space-y-4">
          <Card className="border-cyan-500/30">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Scale className="h-4 w-4 text-purple-400" />
                Query Free Law Project / CourtListener API
              </CardTitle>
              <CardDescription className="text-xs">
                Search authoritative appellate decisions from the 13th Court of Appeals (Corpus Christi - Edinburg) and the Texas Court of Criminal Appeals.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
                <div className="sm:col-span-8">
                  <input
                    type="text"
                    placeholder="e.g. 'Michael Morton Act' or 'Article 17.151 bail delay'"
                    value={caselawQuery}
                    onChange={(e) => setCaselawQuery(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-md bg-background border border-border focus:border-cyan-400 focus:outline-hidden"
                  />
                </div>
                <div className="sm:col-span-4 flex gap-2">
                  <select
                    value={caselawCourt}
                    onChange={(e) => setCaselawCourt(e.target.value)}
                    className="w-full text-xs rounded-md bg-background border border-border px-2 py-1.5 focus:outline-hidden"
                  >
                    <option value="texapp-13">13th COA (Corpus Christi)</option>
                    <option value="texcrimapp">Texas Court of Criminal Appeals</option>
                    <option value="ca5">5th Circuit (Federal)</option>
                  </select>
                  <Button
                    size="sm"
                    onClick={() => refetchCaselaw()}
                    disabled={caselawLoading}
                    className="bg-purple-600 hover:bg-purple-500 text-white text-xs shrink-0"
                  >
                    Search
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Results */}
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>Results for <strong>"{caselawQuery}"</strong> ({caselawResults.length} decisions)</span>
              <span className="text-[11px]">{caselawData?.source}</span>
            </div>

            {caselawResults.map((r: any, idx: number) => (
              <Card key={idx} className="border-border/80 bg-card hover:border-purple-500/40 transition-colors">
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="space-y-0.5">
                      <CardTitle className="text-sm font-bold text-foreground">
                        {r.case_name}
                      </CardTitle>
                      <div className="text-xs text-purple-400 font-mono">
                        {r.court} &bull; {r.date_filed}
                      </div>
                    </div>
                    {r.absolute_url && (
                      <Button asChild size="sm" variant="outline" className="h-7 text-xs gap-1">
                        <a href={r.absolute_url} target="_blank" rel="noreferrer">
                          Full Opinion <ExternalLink className="h-3 w-3" />
                        </a>
                      </Button>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="pt-0 text-xs">
                  <p
                    className="text-muted-foreground leading-relaxed text-[11px]"
                    dangerouslySetInnerHTML={{ __html: r.snippet }}
                  />
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
