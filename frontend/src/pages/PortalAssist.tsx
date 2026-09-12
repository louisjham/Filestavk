import { useState, useEffect, useRef } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Globe,
  Search,
  ShieldAlert,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ExternalLink,
  Clock,
  FileText,
  User,
  Scale,
  RefreshCw,
  Plus,
} from "lucide-react"
import { formatDate, formatDateTime } from "@/lib/utils"

export function PortalAssist() {
  const [activeTab, setActiveTab] = useState<"raw_paste" | "headed_browser">("raw_paste")
  
  // Raw Paste State
  const [rawText, setRawText] = useState("")
  const [parsedData, setParsedData] = useState<any>(null)
  const [isParsing, setIsParsing] = useState(false)
  const [isCommitting, setIsCommitting] = useState(false)
  const [commitSuccess, setCommitSuccess] = useState<any>(null)

  // Headed Browser State
  const [searchType, setSearchType] = useState<"case_number" | "name">("case_number")
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedCaseId, setSelectedCaseId] = useState<number | undefined>(undefined)
  const [selectedClientId, setSelectedClientId] = useState<number | undefined>(undefined)

  // Active lookup job state
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const [jobStatus, setJobStatus] = useState<any>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isResuming, setIsResuming] = useState(false)
  const pollIntervalRef = useRef<any>(null)

  // Fetch cases and clients for quick-fill
  const { data: cases } = useQuery({
    queryKey: ["cases"],
    queryFn: () => api.cases.list(),
  })

  const { data: clients } = useQuery({
    queryKey: ["clients"],
    queryFn: () => api.clients.list(),
  })

  const { data: auditLogs, refetch: refetchAuditLogs } = useQuery({
    queryKey: ["portal-audit-logs"],
    queryFn: () => api.portal.getAuditLogs(),
    refetchInterval: 10000,
  })

  // Handle Raw Text Parse
  const handleParseRawText = async () => {
    if (!rawText.trim()) return
    setIsParsing(true)
    setCommitSuccess(null)
    try {
      const res = await api.portal.parseRawText(rawText)
      setParsedData(res.parsed_data)
    } catch (err: any) {
      alert(err.message || "Failed to parse raw Odyssey text.")
    } finally {
      setIsParsing(false)
    }
  }

  // Handle Raw Text Commit
  const handleCommitRawCase = async () => {
    if (!parsedData) return
    setIsCommitting(true)
    try {
      const res = await api.portal.commitRawCase({
        case_number: parsedData.case_number,
        client_name: parsedData.client_name,
        court: parsedData.court,
        judge: parsedData.judge,
        charge_description: parsedData.charge_description,
        file_date: parsedData.file_date,
        offense_date: parsedData.offense_date,
        has_appointment_order: parsedData.has_appointment_order,
        appointment_order_date: parsedData.appointment_order_date,
        appointment_status: parsedData.appointment_status,
        disposition_type: parsedData.disposition_type,
        disposition_date: parsedData.disposition_date,
        bond_amount: parsedData.bond_amount,
        bond_type: parsedData.bond_type,
        events: parsedData.events || [],
        auto_create_voucher: true,
      })
      setCommitSuccess(res)
      refetchAuditLogs()
    } catch (err: any) {
      alert(err.message || "Failed to commit case to database.")
    } finally {
      setIsCommitting(false)
    }
  }

  // Handle case prefill
  const handleCaseSelect = (caseIdStr: string) => {
    if (!caseIdStr) {
      setSelectedCaseId(undefined)
      return
    }
    const cId = Number(caseIdStr)
    setSelectedCaseId(cId)
    const found = cases?.find((c: any) => c.id === cId)
    if (found?.case_number) {
      setSearchType("case_number")
      setSearchQuery(found.case_number)
      if (found.client_id) setSelectedClientId(found.client_id)
    }
  }

  // Handle client prefill
  const handleClientSelect = (clientIdStr: string) => {
    if (!clientIdStr) {
      setSelectedClientId(undefined)
      return
    }
    const clId = Number(clientIdStr)
    setSelectedClientId(clId)
    const found = clients?.find((cl: any) => cl.id === clId)
    if (found?.name) {
      setSearchType("name")
      // Convert "John Doe" to "Doe, John"
      const parts = found.name.trim().split(" ")
      if (parts.length >= 2) {
        const last = parts[parts.length - 1]
        const first = parts.slice(0, parts.length - 1).join(" ")
        setSearchQuery(`${last}, ${first}`)
      } else {
        setSearchQuery(found.name)
      }
    }
  }

  // Start Lookup
  const handleStartLookup = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!searchQuery.trim()) return

    setIsSubmitting(true)
    setJobStatus(null)

    try {
      const res = await api.portal.lookup({
        search_type: searchType,
        search_query: searchQuery.trim(),
        case_id: selectedCaseId,
        client_id: selectedClientId,
      })

      setActiveJobId(res.job_id)
      setJobStatus({
        status: "LAUNCHING_BROWSER",
        message: "Launching Chromium browser on your screen...",
      })
    } catch (err: any) {
      alert(err.message || "Failed to initiate portal lookup")
    } finally {
      setIsSubmitting(false)
    }
  }

  // Resume lookup once human completes CAPTCHA
  const handleResumeLookup = async () => {
    if (!activeJobId) return
    setIsResuming(true)
    try {
      await api.portal.resumeJob(activeJobId)
      setJobStatus((prev: any) => ({
        ...prev,
        status: "SEARCHING",
        message: "Human passed control! Vanishing browser and auto-filling search query...",
      }))
    } catch (err: any) {
      console.error("Resume error:", err)
    } finally {
      setIsResuming(false)
    }
  }

  // Cancel Job
  const handleCancelLookup = async () => {
    if (!activeJobId) return
    try {
      await api.portal.cancelJob(activeJobId)
      setJobStatus((prev: any) => ({ ...prev, status: "CANCELLED", message: "Cancelled by user" }))
    } catch (err: any) {
      console.error(err)
    }
  }

  // Polling loop for active job
  useEffect(() => {
    if (!activeJobId) return

    const checkJob = async () => {
      try {
        const job = await api.portal.getJob(activeJobId)
        setJobStatus(job)

        if (job.status === "DONE" || job.status === "ERROR" || job.status === "CANCELLED") {
          clearInterval(pollIntervalRef.current)
          refetchAuditLogs()
        }
      } catch (e) {
        console.error("Job poll error:", e)
      }
    }

    checkJob()
    pollIntervalRef.current = setInterval(checkJob, 1500)

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
    }
  }, [activeJobId, refetchAuditLogs])

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <Globe className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Nueces County Odyssey Public Portal Assist
          </h1>
        </div>
        <p className="text-sm text-muted-foreground mt-1">
          Automated Smart Search lookup on Tyler Technologies Public Portal (
          <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
            portal-txnueces.tylertech.cloud/Portal
          </code>
          ) with human-in-the-loop CAPTCHA bypass.
        </p>
      </div>

      {/* Top Mode Switcher */}
      <div className="flex items-center gap-3 border-b border-border pb-3">
        <Button
          variant={activeTab === "raw_paste" ? "default" : "outline"}
          onClick={() => setActiveTab("raw_paste")}
          className="text-xs gap-1.5 h-9 font-semibold"
        >
          <FileText className="h-4 w-4 text-cyan-400" />
          ⚡ Select All &amp; Paste (Instant Ingestion)
        </Button>
        <Button
          variant={activeTab === "headed_browser" ? "default" : "outline"}
          onClick={() => setActiveTab("headed_browser")}
          className="text-xs gap-1.5 h-9"
        >
          <Globe className="h-4 w-4" />
          🌐 Headed Browser Automation
        </Button>
      </div>

      {activeTab === "raw_paste" ? (
        /* RAW PASTE MODE */
        <div className="space-y-6">
          <Card className="border-cyan-500/40 bg-card">
            <CardHeader className="pb-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="space-y-1">
                  <CardTitle className="text-base flex items-center gap-2">
                    <FileText className="h-4 w-4 text-cyan-400" />
                    Instant Case Ingestion from Tyler Odyssey Webpage
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Open any case details on <code className="text-cyan-300">portal-txnueces.tylertech.cloud</code>, press <kbd className="px-1.5 py-0.5 rounded bg-muted border font-mono">Ctrl+A</kbd> &rarr; <kbd className="px-1.5 py-0.5 rounded bg-muted border font-mono">Ctrl+C</kbd>, and paste below.
                  </CardDescription>
                </div>
                <Button
                  asChild
                  size="sm"
                  variant="outline"
                  className="text-xs h-8 gap-1 border-cyan-500/30 text-cyan-300 hover:bg-cyan-950/40"
                >
                  <a
                    href="https://portal-txnueces.tylertech.cloud/Portal/Home/Dashboard/29"
                    target="_blank"
                    rel="noreferrer"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    Open Odyssey Portal
                  </a>
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <textarea
                className="w-full h-44 p-3 font-mono text-xs rounded-md bg-background border border-border focus:border-cyan-400 focus:outline-hidden"
                placeholder="Paste raw text here... Example:
Case Number: 2024-CR-1042-D
The State of Texas vs. Marcus Hernandez
Judicial Officer: Jack Pulcher
Court: 105th District Court
Charge: POSS CS PG 1/1-B <1G (State Jail Felony)
Events:
03/20/2024 ORDER APPOINTING COUNSEL
08/20/2024 ORDER OF DISMISSAL"
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
              />

              <div className="flex items-center justify-between">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setRawText("")
                    setParsedData(null)
                    setCommitSuccess(null)
                  }}
                  className="text-xs text-muted-foreground"
                >
                  Clear Text
                </Button>

                <Button
                  type="button"
                  onClick={handleParseRawText}
                  disabled={!rawText.trim() || isParsing}
                  className="bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-xs gap-1.5"
                >
                  {isParsing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
                  Extract Case &amp; Appointment Order
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Parsed Preview Card */}
          {parsedData && (
            <Card className="border-cyan-500/50 bg-gradient-to-b from-card to-cyan-950/10">
              <CardHeader className="pb-3 border-b border-border">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <CardTitle className="text-base flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                      Extracted Odyssey Case Summary: <span className="font-mono text-primary">{parsedData.case_number}</span>
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Verified fields extracted from Tyler Odyssey page dump. Ready to insert into database.
                    </CardDescription>
                  </div>
                  <Badge variant={parsedData.ready_for_voucher ? "default" : "secondary"}>
                    {parsedData.ready_for_voucher ? "Ready to Bill" : "Active Docket"}
                  </Badge>
                </div>
              </CardHeader>

              <CardContent className="p-4 space-y-4 text-xs">
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="p-3 rounded-lg bg-secondary/50 border border-border">
                    <span className="text-muted-foreground text-[11px] block">Defendant / Client</span>
                    <span className="font-bold text-foreground text-sm">{parsedData.client_name}</span>
                  </div>

                  <div className="p-3 rounded-lg bg-secondary/50 border border-border">
                    <span className="text-muted-foreground text-[11px] block">Court &amp; Presiding Judge</span>
                    <span className="font-bold text-foreground">{parsedData.court}</span>
                    <span className="text-[11px] text-muted-foreground block">{parsedData.judge}</span>
                  </div>

                  <div className="p-3 rounded-lg bg-secondary/50 border border-border">
                    <span className="text-muted-foreground text-[11px] block">Charge &amp; Level</span>
                    <span className="font-bold text-foreground">{parsedData.charge_description}</span>
                    {parsedData.offense_date && (
                      <span className="text-[11px] text-muted-foreground block">Offense: {parsedData.offense_date}</span>
                    )}
                  </div>
                </div>

                {/* Appointment Order & Disposition Strip */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className={`p-3 rounded-lg border flex items-start gap-2.5 ${
                    parsedData.has_appointment_order
                      ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                      : "bg-amber-500/10 border-amber-500/40 text-amber-300"
                  }`}>
                    {parsedData.has_appointment_order ? (
                      <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
                    ) : (
                      <AlertCircle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
                    )}
                    <div className="space-y-0.5">
                      <span className="font-bold text-foreground block">
                        {parsedData.has_appointment_order ? "Order Appointing Counsel Verified" : "⚠️ Missing Order Appointing Counsel"}
                      </span>
                      <p className="text-[11px] text-muted-foreground">
                        {parsedData.has_appointment_order
                          ? `Recorded on docket ${parsedData.appointment_order_date || ""}. Voucher coordinator will accept.`
                          : "No appointment order found in event log. Contact court coordinator to add to docket."}
                      </p>
                    </div>
                  </div>

                  <div className="p-3 rounded-lg border border-border bg-secondary/30 flex items-start gap-2.5">
                    <Scale className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                    <div className="space-y-0.5">
                      <span className="font-bold text-foreground block">
                        Disposition: {parsedData.disposition_type}
                      </span>
                      <p className="text-[11px] text-muted-foreground">
                        {parsedData.disposition_date ? `Disposed on ${parsedData.disposition_date}` : "Case active / pending trial"}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Extracted Events */}
                {parsedData.events && parsedData.events.length > 0 && (
                  <div className="space-y-2">
                    <span className="font-semibold text-foreground uppercase tracking-wider text-[11px]">
                      Register of Actions / Events ({parsedData.events.length})
                    </span>
                    <div className="max-h-36 overflow-y-auto space-y-1 p-2 rounded bg-background border border-border">
                      {parsedData.events.map((ev: any, idx: number) => (
                        <div key={idx} className="flex items-center justify-between text-[11px] py-0.5 border-b border-border/40 last:border-0">
                          <span className="font-medium text-foreground">{ev.title}</span>
                          <span className="font-mono text-muted-foreground">{ev.date}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Commit Action */}
                <div className="pt-2 flex items-center justify-between">
                  <span className="text-muted-foreground text-[11px]">
                    Estimated CJA Voucher: <strong className="text-emerald-400">${parsedData.estimated_voucher_amount.toLocaleString("en-US", { minimumFractionDigits: 2 })}</strong>
                  </span>

                  <Button
                    onClick={handleCommitRawCase}
                    disabled={isCommitting || commitSuccess}
                    className="bg-primary hover:bg-primary/90 text-primary-foreground font-semibold text-xs gap-1.5"
                  >
                    {isCommitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
                    {commitSuccess ? "✓ Saved to Database!" : "Save Case & Create Draft Voucher"}
                  </Button>
                </div>

                {commitSuccess && (
                  <div className="p-3 rounded-lg bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                      <span>{commitSuccess.message}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button asChild size="sm" variant="outline" className="h-7 text-xs">
                        <Link to={`/cases/${commitSuccess.case_id}`}>View Case</Link>
                      </Button>
                      <Button asChild size="sm" className="h-7 text-xs bg-emerald-600 hover:bg-emerald-500 text-white">
                        <Link to="/vouchers">Open Voucher Radar</Link>
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      ) : (
        /* HEADED BROWSER MODE */
        <div className="space-y-6">
          <Card className="border-amber-500/30 bg-amber-500/10 text-amber-200">
            <CardContent className="flex items-start gap-3 p-4">
              <ShieldAlert className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
              <div className="text-xs space-y-1">
                <p className="font-semibold text-amber-300">
                  Interactive Assisted Automation Mode
                </p>
                <p className="text-amber-200/90 leading-relaxed">
                  When you launch a lookup, a Chromium browser window opens on your screen.
                  Please complete the visual CAPTCHA puzzle at <code className="text-amber-100">Dashboard/29</code>.
                  Once solved, Filestavk automatically fills the search term, verifies human checkbox, extracts the court record,
                  and permanently writes it to your database.
                </p>
              </div>
            </CardContent>
          </Card>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Col: Query Setup */}
        <div className="lg:col-span-5 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Search className="h-4 w-4 text-primary" />
                Initiate Smart Search
              </CardTitle>
              <CardDescription>
                Search Nueces County court records by Case Number or Party Name.
              </CardDescription>
            </CardHeader>
            <form onSubmit={handleStartLookup}>
              <CardContent className="space-y-4">
                {/* Search Type Selector */}
                <div className="space-y-2">
                  <Label>Search Type</Label>
                  <div className="grid grid-cols-2 gap-2">
                    <Button
                      type="button"
                      variant={searchType === "case_number" ? "default" : "outline"}
                      className="text-xs h-9"
                      onClick={() => {
                        setSearchType("case_number")
                        setSearchQuery("")
                      }}
                    >
                      <Scale className="h-3.5 w-3.5 mr-1.5" />
                      Case Number
                    </Button>
                    <Button
                      type="button"
                      variant={searchType === "name" ? "default" : "outline"}
                      className="text-xs h-9"
                      onClick={() => {
                        setSearchType("name")
                        setSearchQuery("")
                      }}
                    >
                      <User className="h-3.5 w-3.5 mr-1.5" />
                      Party Name
                    </Button>
                  </div>
                </div>

                {/* Quick Link from DB Case */}
                {cases && cases.length > 0 && (
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">
                      Auto-fill from existing Case (Optional)
                    </Label>
                    <select
                      className="w-full h-9 rounded-md border border-input bg-transparent px-3 py-1 text-xs shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                      value={selectedCaseId ?? ""}
                      onChange={(e) => handleCaseSelect(e.target.value)}
                    >
                      <option value="" className="bg-card text-foreground">
                        Select a case...
                      </option>
                      {cases.map((c: any) => (
                        <option key={c.id} value={c.id} className="bg-card text-foreground">
                          {c.case_number} — {c.court}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {/* Quick Link from DB Client */}
                {clients && clients.length > 0 && (
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">
                      Auto-fill from existing Client (Optional)
                    </Label>
                    <select
                      className="w-full h-9 rounded-md border border-input bg-transparent px-3 py-1 text-xs shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                      value={selectedClientId ?? ""}
                      onChange={(e) => handleClientSelect(e.target.value)}
                    >
                      <option value="" className="bg-card text-foreground">
                        Select a client...
                      </option>
                      {clients.map((cl: any) => (
                        <option key={cl.id} value={cl.id} className="bg-card text-foreground">
                          {cl.name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {/* Search Input Field */}
                <div className="space-y-2">
                  <Label htmlFor="searchQuery">
                    {searchType === "case_number" ? "Case Number" : "Party Name (Last, First Middle)"}
                  </Label>
                  <Input
                    id="searchQuery"
                    placeholder={
                      searchType === "case_number"
                        ? "e.g. 2024-CR-0001, CR-2023-001"
                        : "e.g. Smith, John or Doe, Jane"
                    }
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    required
                  />
                  <p className="text-[11px] text-muted-foreground">
                    {searchType === "case_number"
                      ? "Enter exact docket number as formatted by Nueces District/County Clerk."
                      : "Tyler Odyssey Smart Search requires: Last, First Middle format."}
                  </p>
                </div>
              </CardContent>

              <CardFooter>
                <Button
                  type="submit"
                  className="w-full"
                  disabled={isSubmitting || (jobStatus && ["LAUNCHING_BROWSER", "WAITING_FOR_HUMAN_CAPTCHA", "SEARCHING", "EXTRACTING"].includes(jobStatus.status))}
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Starting Lookup...
                    </>
                  ) : (
                    <>
                      <Globe className="mr-2 h-4 w-4" />
                      Start Portal Lookup
                    </>
                  )}
                </Button>
              </CardFooter>
            </form>
          </Card>
        </div>

        {/* Right Col: Live Progress & Results */}
        <div className="lg:col-span-7 space-y-6">
          {/* Active Job Stepper Card */}
          {jobStatus ? (
            <Card className="border-primary/40 bg-card">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base flex items-center gap-2">
                    <RefreshCw className={`h-4 w-4 text-primary ${["LAUNCHING_BROWSER", "WAITING_FOR_HUMAN_CAPTCHA", "SEARCHING", "EXTRACTING"].includes(jobStatus.status) ? "animate-spin" : ""}`} />
                    Live Assist Progress
                  </CardTitle>
                  <Badge
                    variant={
                      jobStatus.status === "DONE"
                        ? "success"
                        : jobStatus.status === "ERROR"
                        ? "destructive"
                        : jobStatus.status === "CANCELLED"
                        ? "muted"
                        : "info"
                    }
                  >
                    {jobStatus.status}
                  </Badge>
                </div>
                <CardDescription>
                  Query: <span className="font-semibold text-foreground">{jobStatus.search_query}</span> ({jobStatus.search_type})
                </CardDescription>
              </CardHeader>

              <CardContent className="space-y-4">
                {/* Live Message Box */}
                <div
                  className={`p-3.5 rounded-lg border text-sm font-medium ${
                    jobStatus.status === "WAITING_FOR_HUMAN_CAPTCHA"
                      ? "bg-blue-500/15 border-blue-500/40 text-blue-300 animate-pulse"
                      : jobStatus.status === "DONE"
                      ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-300"
                      : jobStatus.status === "ERROR"
                      ? "bg-red-500/15 border-red-500/40 text-red-300"
                      : "bg-muted border-border text-foreground"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {jobStatus.status === "DONE" && <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />}
                    {jobStatus.status === "ERROR" && <AlertCircle className="h-5 w-5 text-red-400 shrink-0" />}
                    {["LAUNCHING_BROWSER", "SEARCHING", "EXTRACTING"].includes(jobStatus.status) && (
                      <Loader2 className="h-5 w-5 text-primary animate-spin shrink-0" />
                    )}
                    {jobStatus.status === "WAITING_FOR_HUMAN_CAPTCHA" && (
                      <span className="text-lg mr-1">🧩</span>
                    )}
                    <span>{jobStatus.message}</span>
                  </div>
                </div>

                {/* Hand-off / Resume Action Banner */}
                {jobStatus.status === "WAITING_FOR_HUMAN_CAPTCHA" && (
                  <div className="p-4 rounded-lg bg-primary/10 border border-primary/30 space-y-3 shadow-inner">
                    <div className="space-y-1">
                      <h4 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                        <CheckCircle2 className="h-4 w-4 text-primary" />
                        Ready on the Search Page?
                      </h4>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        Once you finish the CAPTCHA puzzle and reach the Smart Search page in the browser window, click below. Filestavk will minimize the browser, enter <strong>"{jobStatus.search_query}"</strong>, check "I am human", and pull the record automatically!
                      </p>
                    </div>
                    <Button
                      type="button"
                      size="sm"
                      className="w-full bg-primary hover:bg-primary/90 text-primary-foreground font-semibold shadow-md gap-2"
                      onClick={handleResumeLookup}
                      disabled={isResuming}
                    >
                      {isResuming ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Passing Control to Filestavk...
                        </>
                      ) : (
                        <>
                          <Search className="h-4 w-4" />
                          I'm on the Search Page — Fill & Submit Now
                        </>
                      )}
                    </Button>
                  </div>
                )}

                {/* Visual Step Progress */}
                <div className="space-y-2 pt-2 border-t border-border/60">
                  <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Pipeline Steps
                  </div>

                  <div className="space-y-2 text-xs">
                    <div className="flex items-center gap-2">
                      <div className={`h-2 w-2 rounded-full ${["LAUNCHING_BROWSER", "WAITING_FOR_HUMAN_CAPTCHA", "SEARCHING", "EXTRACTING", "DONE"].includes(jobStatus.status) ? "bg-emerald-400" : "bg-muted"}`} />
                      <span className={jobStatus.status === "LAUNCHING_BROWSER" ? "font-bold text-primary" : "text-muted-foreground"}>
                        1. Launch Headed Chromium to Portal
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <div className={`h-2 w-2 rounded-full ${["WAITING_FOR_HUMAN_CAPTCHA", "SEARCHING", "EXTRACTING", "DONE"].includes(jobStatus.status) ? "bg-emerald-400" : "bg-muted"}`} />
                      <span className={jobStatus.status === "WAITING_FOR_HUMAN_CAPTCHA" ? "font-bold text-blue-400" : "text-muted-foreground"}>
                        2. Solve CAPTCHA Challenge on Screen
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <div className={`h-2 w-2 rounded-full ${["SEARCHING", "EXTRACTING", "DONE"].includes(jobStatus.status) ? "bg-emerald-400" : "bg-muted"}`} />
                      <span className={jobStatus.status === "SEARCHING" ? "font-bold text-primary" : "text-muted-foreground"}>
                        3. Fill Smart Search & Submit Form
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <div className={`h-2 w-2 rounded-full ${["EXTRACTING", "DONE"].includes(jobStatus.status) ? "bg-emerald-400" : "bg-muted"}`} />
                      <span className={jobStatus.status === "EXTRACTING" ? "font-bold text-primary" : "text-muted-foreground"}>
                        4. Extract Record, Charges, & Register of Actions
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <div className={`h-2 w-2 rounded-full ${jobStatus.status === "DONE" ? "bg-emerald-400" : "bg-muted"}`} />
                      <span className={jobStatus.status === "DONE" ? "font-bold text-emerald-400" : "text-muted-foreground"}>
                        5. Persist Indestructible Raw Document & Case Rows
                      </span>
                    </div>
                  </div>
                </div>

                {/* Successful Result Actions */}
                {jobStatus.status === "DONE" && (
                  <div className="pt-3 border-t border-border flex flex-wrap gap-2">
                    {jobStatus.case_id && (
                      <Button asChild size="sm" variant="default" className="gap-1.5">
                        <Link to={`/cases/${jobStatus.case_id}`}>
                          <Scale className="h-3.5 w-3.5" />
                          View Case Record
                        </Link>
                      </Button>
                    )}
                    {jobStatus.document_id && (
                      <Button asChild size="sm" variant="outline" className="gap-1.5">
                        <Link to="/documents">
                          <FileText className="h-3.5 w-3.5" />
                          View Ingested Document
                        </Link>
                      </Button>
                    )}
                  </div>
                )}
              </CardContent>

                {["LAUNCHING_BROWSER", "WAITING_FOR_HUMAN_CAPTCHA", "SEARCHING"].includes(jobStatus.status) && (
                <CardFooter className="pt-0">
                  <Button variant="destructive" size="sm" onClick={handleCancelLookup} className="w-full text-xs">
                    Cancel Lookup
                  </Button>
                </CardFooter>
              )}
            </Card>
          ) : (
            <Card className="border-dashed bg-muted/20">
              <CardContent className="p-8 text-center space-y-2 text-muted-foreground">
                <Globe className="h-10 w-10 mx-auto text-muted-foreground/40" />
                <h4 className="font-medium text-foreground text-sm">No Active Portal Session</h4>
                <p className="text-xs max-w-sm mx-auto">
                  Select a Case Number or Party Name on the left and click <strong>Start Portal Lookup</strong> to launch an assisted session.
                </p>
              </CardContent>
            </Card>
          )}

          {/* Audit Logs Table */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  Recent Portal Audit Logs
                </CardTitle>
                <Button variant="ghost" size="sm" onClick={() => refetchAuditLogs()} className="h-7 text-xs">
                  Refresh
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {auditLogs && auditLogs.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-border text-left text-muted-foreground">
                        <th className="py-2 pr-4 font-medium">Time</th>
                        <th className="py-2 pr-4 font-medium">Target / Query</th>
                        <th className="py-2 pr-4 font-medium">Type</th>
                        <th className="py-2 font-medium">Outcome</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/50">
                      {auditLogs.map((log: any) => (
                        <tr key={log.id}>
                          <td className="py-2.5 pr-4 text-muted-foreground whitespace-nowrap">
                            {formatDateTime(log.performed_at)}
                          </td>
                          <td className="py-2.5 pr-4 font-medium text-foreground">
                            {log.client_name || "—"}
                          </td>
                          <td className="py-2.5 pr-4 text-muted-foreground">
                            <span className="capitalize">{log.action || "lookup"}</span>
                          </td>
                          <td className="py-2.5">
                            <Badge variant={log.outcome === "SUCCESS" ? "success" : "destructive"}>
                              {log.outcome}
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-xs text-muted-foreground py-4 text-center">
                  No portal lookup history recorded yet.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
        </div>
      )}
    </div>
  )
}
