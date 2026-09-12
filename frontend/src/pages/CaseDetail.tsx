import { useState } from "react"
import { useParams, Link } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Scale,
  Calendar,
  FileText,
  DollarSign,
  Clock,
  Shield,
  CheckSquare,
  Square,
  Send,
  AlertTriangle,
  User,
  Activity,
  Plus,
  ArrowRight,
  CheckCircle2,
  FileCheck,
  Download,
  ExternalLink,
  Lock,
} from "lucide-react"
import { formatDate } from "@/lib/utils"
import { ClassificationBadge } from "@/components/shared/ClassificationBadge"

const LIFECYCLE_STAGES = [
  { id: "ARREST", label: "Arrest & Magistration", desc: "Booking & PC affidavit" },
  { id: "BOND", label: "Bail & Conditions", desc: "PR / Surety & Interlock" },
  { id: "INDICTMENT", label: "Grand Jury", desc: "True bill indictment" },
  { id: "DISCOVERY", label: "Morton Discovery", desc: "Art. 39.14 CCP compliance" },
  { id: "PRE_TRIAL", label: "Pre-Trial & 404(b)", desc: "Suppression & docket call" },
  { id: "TRIAL", label: "Plea / Trial", desc: "Plea agreement or jury" },
  { id: "DISPOSED", label: "Disposition / Vouchers", desc: "Voucher recovery clock" },
  { id: "PROBATION", label: "Probation / Supervision", desc: "Community supervision" },
]

export function CaseDetail() {
  const { id } = useParams()
  const caseId = Number(id)
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<"overview" | "morton" | "timeline" | "documents" | "vouchers">("overview")
  const [autoBuildNotice, setAutoBuildNotice] = useState<string | null>(null)

  // Fetch case data
  const { data: caseData, isLoading } = useQuery({
    queryKey: ["case", caseId],
    queryFn: () => api.cases.get(caseId),
    enabled: !isNaN(caseId),
  })

  // Fetch documents for this case
  const { data: documents } = useQuery({
    queryKey: ["case-documents", caseId],
    queryFn: () => api.documents.list({ case_id: String(caseId) }),
    enabled: !isNaN(caseId),
  })

  // Fetch vouchers for this case
  const { data: vouchers } = useQuery({
    queryKey: ["case-vouchers", caseId],
    queryFn: () => api.vouchers.list({ case_id: caseId }),
    enabled: !isNaN(caseId),
  })

  // Fetch timeline events for this case
  const { data: timelineEvents } = useQuery({
    queryKey: ["case-timeline", caseId],
    queryFn: () => api.cases.timeline(caseId),
    enabled: !isNaN(caseId),
  })

  // 1-Click Auto Reconstruct Voucher Mutation
  const autoBuildMutation = useMutation({
    mutationFn: () => api.vouchers.autoGenerate(caseId),
    onSuccess: (res: any) => {
      setAutoBuildNotice(`Draft Voucher #${res.voucher_number} ($${res.amount_requested.toFixed(2)}) auto-generated from case docket!`)
      queryClient.invalidateQueries({ queryKey: ["case", caseId] })
      queryClient.invalidateQueries({ queryKey: ["case-vouchers", caseId] })
      queryClient.invalidateQueries({ queryKey: ["vouchers"] })
      setTimeout(() => setAutoBuildNotice(null), 6000)
    },
  })

  // Update Case stage / Morton Checklist Mutation
  const updateCaseMutation = useMutation({
    mutationFn: (data: any) => api.cases.update(caseId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["case", caseId] })
    },
  })

  if (isLoading) {
    return <div className="p-8 text-center text-muted-foreground">Loading case details...</div>
  }

  if (!caseData) {
    return (
      <div className="p-8 text-center text-muted-foreground space-y-4">
        <p>Case not found.</p>
        <Button asChild variant="outline">
          <Link to="/cases">Back to Cases</Link>
        </Button>
      </div>
    )
  }

  // Parse Morton discovery checklist
  let mortonItems: Record<string, boolean> = {
    offense_report: false,
    dashcam_video: false,
    bodycam_video: false,
    dps_lab_report: false,
    call_911_audio: false,
    brady_notice: false,
    witness_statements: false,
  }
  try {
    if (caseData.morton_discovery_json) {
      mortonItems = { ...mortonItems, ...JSON.parse(caseData.morton_discovery_json) }
    }
  } catch {}

  const toggleMortonItem = (key: string) => {
    const updated = { ...mortonItems, [key]: !mortonItems[key] }
    updateCaseMutation.mutate({
      morton_discovery_json: JSON.stringify(updated),
    })
  }

  const currentStageIndex = LIFECYCLE_STAGES.findIndex(
    (s) => s.id === (caseData.stage || "DISCOVERY")
  )

  const mortonCompleteCount = Object.values(mortonItems).filter(Boolean).length
  const totalMortonCount = Object.keys(mortonItems).length
  const isMidStride = Boolean(caseData.has_appointment_acceptance && !caseData.has_appointment_order)

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Case Header Card */}
      <Card className="bg-card border-border">
        <CardContent className="p-6">
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold tracking-tight text-foreground font-mono">
                  {caseData.case_number || `Case #${caseData.id}`}
                </h1>
                <Badge variant={caseData.status === "OPEN" ? "info" : caseData.status === "DISPOSED" ? "warning" : "success"}>
                  {caseData.status}
                </Badge>
                {caseData.is_cja ? (
                  <Badge variant="purple">Appointed (CJA / Fair Defense Act)</Badge>
                ) : (
                  <Badge variant="teal">Retained Counsel</Badge>
                )}
                {caseData.in_custody && (
                  <Badge variant="destructive" className="bg-red-500/20 text-red-300 border-red-500/40 gap-1 flex items-center font-bold">
                    <Lock className="h-3 w-3" />
                    In Custody (Nueces County Jail)
                  </Badge>
                )}
                {isMidStride && (
                  <Badge variant="warning" className="bg-amber-500/20 text-amber-300 border-amber-500/40 gap-1 flex items-center font-semibold">
                    <AlertTriangle className="h-3 w-3" />
                    Mid-Stride Case (Verify Prior Order)
                  </Badge>
                )}
              </div>

              <div className="text-sm font-semibold text-foreground/90 pt-1">
                {caseData.charge_description || "Criminal Matter"}
              </div>

              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground pt-1">
                <span className="flex items-center gap-1 font-medium text-foreground">
                  <User className="h-3.5 w-3.5 text-primary" />
                  Client: {caseData.client?.name || "Client #" + caseData.client_id}
                </span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Scale className="h-3.5 w-3.5 text-primary" />
                  {caseData.court || "Nueces County Court"} {caseData.judge ? `(${caseData.judge})` : ""}
                </span>
                <span>•</span>
                <span>Opened: {formatDate(caseData.opened_date)}</span>
              </div>
            </div>

            {/* Top Right Action Button: 1-Click Voucher Builder */}
            {caseData.is_cja && (
              <div className="flex flex-col sm:flex-row items-end gap-2">
                <Button
                  onClick={() => autoBuildMutation.mutate()}
                  disabled={autoBuildMutation.isPending}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5 text-xs shadow-md"
                >
                  <DollarSign className="h-4 w-4" />
                  1-Click Auto-Build Voucher
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Statutory Appointment & Voucher Readiness Banner */}
      {caseData.is_cja && (
        <Card className={`border ${
          caseData.has_appointment_order && caseData.has_appointment_acceptance
            ? "bg-emerald-950/20 border-emerald-500/40 text-emerald-300"
            : isMidStride
            ? "bg-emerald-950/20 border-emerald-500/40 text-emerald-300"
            : caseData.has_appointment_order && !caseData.has_appointment_acceptance
            ? "bg-amber-950/25 border-amber-500/40 text-amber-300"
            : "bg-red-950/20 border-red-500/40 text-red-300"
        }`}>
          <CardContent className="p-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-1.5">
                <div className="flex items-center gap-2 font-semibold text-sm">
                  {caseData.has_appointment_order && caseData.has_appointment_acceptance ? (
                    <>
                      <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />
                      <span className="text-foreground font-bold">Art. 26.04 Appointment &amp; Stamped Acceptance Verified</span>
                      <Badge variant="success" className="text-[10px] bg-emerald-500/20 text-emerald-300 border-emerald-500/40">
                        Voucher Billable
                      </Badge>
                    </>
                  ) : isMidStride ? (
                    <>
                      <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />
                      <span className="text-foreground font-bold">Mid-Stride Case: Stamped Acceptance Filed (Ready to File)</span>
                      <Badge variant="warning" className="text-[10px] bg-amber-500/20 text-amber-300 border-amber-500/40">
                        Verify Prior Order
                      </Badge>
                      <Badge variant="success" className="text-[10px] bg-emerald-500/20 text-emerald-300 border-emerald-500/40">
                        Ready to Be Filed
                      </Badge>
                    </>
                  ) : caseData.has_appointment_order && !caseData.has_appointment_acceptance ? (
                    <>
                      <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0" />
                      <span className="text-foreground font-bold">Order Issued — Awaiting Stamped Acceptance of Appointment</span>
                      <Badge variant="warning" className="text-[10px] bg-amber-500/20 text-amber-300 border-amber-500/40">
                        Payment Blocked by Auditor
                      </Badge>
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="h-5 w-5 text-red-400 shrink-0" />
                      <span className="text-foreground font-bold">Missing Order Appointing Counsel</span>
                      <Badge variant="destructive" className="text-[10px] bg-red-500/20 text-red-300 border-red-500/40">
                        Not Appointed
                      </Badge>
                    </>
                  )}
                </div>

                <p className="text-xs text-muted-foreground leading-relaxed">
                  {caseData.has_appointment_order && caseData.has_appointment_acceptance
                    ? "Both the Magistrate Appointment Order and District Clerk file-stamped Acceptance (with client contact affirmation) are verified on docket. Prerequisite for Nueces County Auditor fee payment is satisfied."
                    : isMidStride
                    ? "Counsel's file-stamped Acceptance of Appointment is recorded on docket. This case was provisioned mid-stride without a prior Order of Appointment. Counsel may submit the voucher on Perfect Apps once appointment is confirmed on Odyssey."
                    : caseData.has_appointment_order && !caseData.has_appointment_acceptance
                    ? "Under Tex. Code Crim. Proc. art. 26.04(j)(1) & 26.05, counsel must file the signed Acceptance of Appointment affirming initial client contact date with District Clerk Anne Lorentzen. Nueces County Auditor blocks payment vouchers until file-stamped acceptance is recorded."
                    : "No formal Order of Appointment is recorded on docket. Ingest the magistrate appointment order to activate statutory CJA tracking."}
                </p>

                {/* Statutory Date Chips */}
                <div className="flex flex-wrap items-center gap-3 text-xs pt-1">
                  <div className="bg-card/60 px-2.5 py-1 rounded border border-border flex items-center gap-1.5">
                    <span className="text-muted-foreground text-[11px]">Appointment Order:</span>
                    <strong className="text-foreground font-mono">
                      {caseData.appointment_order_date ? formatDate(caseData.appointment_order_date) : caseData.has_appointment_order ? "Verified on Docket" : "Missing"}
                    </strong>
                  </div>

                  <div className="bg-card/60 px-2.5 py-1 rounded border border-border flex items-center gap-1.5">
                    <span className="text-muted-foreground text-[11px]">Client Contact (48h Rule):</span>
                    <strong className="text-foreground font-mono">
                      {caseData.client_contact_date ? formatDate(caseData.client_contact_date) : "Pending Affirmation"}
                    </strong>
                  </div>

                  <div className="bg-card/60 px-2.5 py-1 rounded border border-border flex items-center gap-1.5">
                    <span className="text-muted-foreground text-[11px]">District Clerk Acceptance:</span>
                    <strong className="text-foreground font-mono">
                      {caseData.acceptance_filed_date ? `Filed ${formatDate(caseData.acceptance_filed_date)}` : caseData.has_appointment_acceptance ? "Filed" : "Awaiting File Stamp"}
                    </strong>
                  </div>
                </div>
              </div>

              <div className="shrink-0 flex sm:flex-col items-end justify-center gap-2">
                {caseData.has_appointment_acceptance ? (
                  <Button
                    asChild
                    size="sm"
                    className="text-xs h-7 gap-1 bg-emerald-600 hover:bg-emerald-700 text-white"
                  >
                    <a
                      href="https://perfectapps.nuecescountytx.gov/PresentationServer/App.aspx/Play/vgAAggch?f=vgAAggch"
                      target="_blank"
                      rel="noreferrer"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                      Submit Voucher — Perfect Apps
                    </a>
                  </Button>
                ) : (
                  <Button asChild size="sm" variant="outline" className="text-xs h-7 gap-1">
                    <Link to={`/documents?case_id=${caseId}`}>
                      <FileText className="h-3.5 w-3.5" />
                      Upload Stamped Acceptance
                    </Link>
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Auto-build notice banner */}
      {autoBuildNotice && (
        <div className="p-3.5 bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 rounded-lg text-xs flex items-center justify-between animate-fadeIn">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
            <span>{autoBuildNotice}</span>
          </div>
          <Button asChild size="sm" variant="ghost" className="h-6 text-xs text-emerald-200 hover:text-white">
            <Link to="/vouchers">View Voucher Radar</Link>
          </Button>
        </div>
      )}

      {/* Texas Criminal Justice Lifecycle Progress Bar */}
      <Card className="border-border bg-card/60 overflow-hidden">
        <div className="p-4 border-b border-border bg-muted/20 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-semibold text-foreground uppercase tracking-wider">
            <Activity className="h-4 w-4 text-primary" />
            Texas Criminal Case Lifecycle Stage
          </div>
          <span className="text-xs text-muted-foreground">
            Current: <strong className="text-primary">{LIFECYCLE_STAGES[currentStageIndex >= 0 ? currentStageIndex : 3]?.label}</strong>
          </span>
        </div>
        <CardContent className="p-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
            {LIFECYCLE_STAGES.map((stage, idx) => {
              const isPast = idx < currentStageIndex
              const isCurrent = idx === currentStageIndex
              return (
                <button
                  key={stage.id}
                  onClick={() => updateCaseMutation.mutate({ stage: stage.id })}
                  className={`p-2.5 rounded-lg border text-left transition-all relative ${
                    isCurrent
                      ? "border-primary bg-primary/10 text-primary shadow-sm ring-1 ring-primary/50"
                      : isPast
                      ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-300 hover:border-emerald-500/60"
                      : "border-border bg-muted/10 text-muted-foreground hover:bg-muted/30"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] font-mono font-bold opacity-60">
                      0{idx + 1}
                    </span>
                    {isPast && <CheckCircle2 className="h-3 w-3 text-emerald-400" />}
                    {isCurrent && <span className="h-2 w-2 rounded-full bg-primary animate-ping" />}
                  </div>
                  <div className="text-[11px] font-bold leading-tight line-clamp-1">{stage.label}</div>
                  <div className="text-[9px] text-muted-foreground mt-0.5 line-clamp-1">{stage.desc}</div>
                </button>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Navigation Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-border pb-2">
        {[
          { id: "overview", label: "Case Overview & Bail" },
          { id: "morton", label: `Michael Morton Discovery (${mortonCompleteCount}/${totalMortonCount})` },
          { id: "timeline", label: "Case Timeline" },
          { id: "documents", label: `Case Documents (${documents?.length || 0})` },
          { id: "vouchers", label: `Voucher Status (${vouchers?.length || 0})` },
        ].map((tab) => (
          <Button
            key={tab.id}
            variant={activeTab === tab.id ? "default" : "ghost"}
            size="sm"
            className="text-xs h-8"
            onClick={() => setActiveTab(tab.id as any)}
          >
            {tab.label}
          </Button>
        ))}
      </div>

      {/* Tab 1: Case Overview & Bail Conditions */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Bail & Bond Conditions Card */}
          <Card className="lg:col-span-2">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Shield className="h-4 w-4 text-primary" />
                Bail &amp; Bond Release Conditions
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 p-3 bg-muted/30 rounded-lg">
                <div>
                  <span className="text-muted-foreground block text-[11px]">Bond Amount</span>
                  <span className="text-sm font-bold text-foreground">
                    {caseData.bond_amount ? `$${caseData.bond_amount.toLocaleString("en-US", { minimumFractionDigits: 2 })}` : "None Set"}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[11px]">Bond Type</span>
                  <span className="font-semibold text-foreground">{caseData.bond_type || "Surety"}</span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[11px]">Assigned Court</span>
                  <span className="text-foreground">{caseData.court}</span>
                </div>
              </div>

              <div>
                <span className="text-muted-foreground font-semibold block mb-1">
                  Court-Ordered Bond Conditions:
                </span>
                <p className="p-3 bg-card border border-border rounded-md text-foreground/90 leading-relaxed">
                  {caseData.bond_conditions || "Standard conditions of bond apply."}
                </p>
              </div>

              {caseData.notes && (
                <div>
                  <span className="text-muted-foreground font-semibold block mb-1">Attorney Case Notes:</span>
                  <p className="p-3 bg-muted/20 border border-border rounded-md text-foreground/80 leading-relaxed">
                    {caseData.notes}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Quick Client Profile Card */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <User className="h-4 w-4 text-primary" />
                Client Profile
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div>
                <span className="text-muted-foreground block text-[11px]">Full Legal Name</span>
                <span className="font-bold text-foreground text-sm">{caseData.client?.name}</span>
              </div>
              <div>
                <span className="text-muted-foreground block text-[11px]">Date of Birth</span>
                <span className="text-foreground">{caseData.client?.dob || "—"}</span>
              </div>
              <div>
                <span className="text-muted-foreground block text-[11px]">Phone</span>
                <span className="text-foreground font-mono">{caseData.client?.phone || "—"}</span>
              </div>
              <div>
                <span className="text-muted-foreground block text-[11px]">Residential Address</span>
                <span className="text-foreground">{caseData.client?.address || "Corpus Christi, TX"}</span>
              </div>
              {caseData.client?.notes && (
                <div className="pt-2 border-t border-border">
                  <span className="text-muted-foreground block text-[11px]">Client Notes:</span>
                  <p className="text-foreground/80 mt-0.5">{caseData.client.notes}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab 2: Michael Morton Act Discovery Checklist (Texas Art. 39.14 CCP) */}
      {activeTab === "morton" && (
        <Card>
          <CardHeader className="pb-3 border-b border-border">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base flex items-center gap-2">
                  <FileCheck className="h-5 w-5 text-primary" />
                  Texas Michael Morton Act Discovery Checklist (Art. 39.14 CCP)
                </CardTitle>
                <CardDescription>
                  Track mandatory state discovery disclosures from the Nueces County District Attorney.
                </CardDescription>
              </div>
              <Badge variant={mortonCompleteCount === totalMortonCount ? "success" : "info"}>
                {mortonCompleteCount} of {totalMortonCount} items received
              </Badge>
            </div>
          </CardHeader>

          <CardContent className="p-6 space-y-3">
            {[
              { key: "offense_report", label: "Police Offense & Incident Reports", desc: "Arresting officer, narrative, supplementals (CCPD / Nueces Sheriff)" },
              { key: "dashcam_video", label: "In-Car Dashcam Video Footage", desc: "Patrol car dashcam recording traffic stop / detention" },
              { key: "bodycam_video", label: "Body-Worn Camera (BWC) Video", desc: "All on-scene officer body camera recordings" },
              { key: "dps_lab_report", label: "DPS Forensic Lab Analysis", desc: "Narcotics analysis, Blood Alcohol concentration (BAC), or ballistics report" },
              { key: "call_911_audio", label: "911 Dispatch & CAD Audio Recordings", desc: "Initial caller audio and dispatch logs" },
              { key: "brady_notice", label: "Brady / Giglio Exculpatory Notice", desc: "State's notice of exculpatory or mitigating evidence" },
              { key: "witness_statements", label: "Witness & Victim Statements", desc: "Written, recorded, or transcribed witness interviews" },
            ].map((item) => {
              const isChecked = mortonItems[item.key]
              return (
                <div
                  key={item.key}
                  onClick={() => toggleMortonItem(item.key)}
                  className={`p-3.5 rounded-lg border cursor-pointer flex items-start gap-3 transition-all ${
                    isChecked
                      ? "bg-emerald-500/10 border-emerald-500/30 text-foreground"
                      : "bg-card border-border hover:border-primary/40 text-muted-foreground"
                  }`}
                >
                  <button className="mt-0.5 text-primary">
                    {isChecked ? (
                      <CheckSquare className="h-4 w-4 text-emerald-400" />
                    ) : (
                      <Square className="h-4 w-4 text-muted-foreground" />
                    )}
                  </button>
                  <div className="space-y-0.5 flex-1">
                    <div className={`text-xs font-semibold ${isChecked ? "text-emerald-300" : "text-foreground"}`}>
                      {item.label}
                    </div>
                    <div className="text-[11px] text-muted-foreground">{item.desc}</div>
                  </div>
                  <Badge variant={isChecked ? "success" : "muted"} className="text-[10px] shrink-0">
                    {isChecked ? "Received" : "Pending DA"}
                  </Badge>
                </div>
              )
            })}
          </CardContent>
        </Card>
      )}

      {/* Tab 3: Case Timeline (Docket History) */}
      {activeTab === "timeline" && (
        <Card>
          <CardHeader className="pb-3 border-b border-border">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base flex items-center gap-2">
                  <Clock className="h-5 w-5 text-primary" />
                  Case Docket & Event Timeline
                </CardTitle>
                <CardDescription>
                  Chronological record of all docket events generated during this case.
                </CardDescription>
              </div>
              <Badge variant="info">{timelineEvents?.events?.length || 0} events</Badge>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {timelineEvents?.events && timelineEvents.events.length > 0 ? (
              <div className="divide-y divide-border/60">
                {timelineEvents.events.map((ev: any, idx: number) => (
                  <div key={ev.id ?? idx} className="p-4 flex items-start gap-4 hover:bg-muted/20 transition-colors">
                    {/* Timeline dot */}
                    <div className="shrink-0 mt-0.5 flex flex-col items-center gap-1">
                      <div className="h-2.5 w-2.5 rounded-full bg-primary ring-2 ring-primary/30" />
                      {idx < (timelineEvents.events.length - 1) && (
                        <div className="w-px flex-1 min-h-4 bg-border/60" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0 space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-semibold text-foreground">{ev.title}</span>
                        {ev.event_type && (
                          <Badge variant="muted" className="text-[10px] font-mono">
                            {ev.event_type}
                          </Badge>
                        )}
                      </div>
                      {ev.description && (
                        <p className="text-[11px] text-muted-foreground leading-relaxed">{ev.description}</p>
                      )}
                      <div className="text-[10px] text-muted-foreground/70 font-mono">
                        {ev.event_date || ev.created_at
                          ? formatDate(ev.event_date || ev.created_at)
                          : "Date unknown"}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-10 text-center text-muted-foreground text-xs space-y-2">
                <Clock className="h-8 w-8 mx-auto text-muted-foreground/30" />
                <p>No docket events recorded yet for this case.</p>
                <p className="text-[11px] text-muted-foreground/60">
                  Events are auto-created when documents are ingested or case stages are updated.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Tab 4: Case Documents */}
      {activeTab === "documents" && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <FileText className="h-4 w-4 text-primary" />
                Case Document Repository
              </CardTitle>
              <Button asChild size="sm" variant="outline" className="h-7 text-xs">
                <Link to="/documents">Browse All Documents</Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {documents && documents.length > 0 ? (
              <div className="divide-y divide-border text-xs">
                {documents.map((doc: any) => (
                  <div key={doc.id} className="py-3 flex items-center justify-between gap-4">
                    <div className="space-y-1">
                      <div className="font-semibold text-foreground flex items-center gap-2">
                        <FileText className="h-3.5 w-3.5 text-primary shrink-0" />
                        <span className="font-medium text-foreground">{doc.filename}</span>
                      </div>
                      <div className="text-[11px] text-muted-foreground flex items-center gap-2">
                        <Badge variant="outline" className="text-[10px] uppercase font-mono px-1.5 py-0">{doc.doc_type}</Badge>
                        <span>&bull;</span>
                        <span>Source: <code>{doc.source}</code></span>
                        <span>&bull;</span>
                        <span>{formatDate(doc.created_at)}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <ClassificationBadge label={doc.classification_label} confidence={doc.classification_confidence} />
                      <Button asChild size="sm" variant="outline" className="h-7 text-xs gap-1">
                        <a href={api.documents.getFileUrl(doc.id)} target="_blank" rel="noreferrer">
                          <Download className="h-3 w-3 text-muted-foreground" />
                          Download
                        </a>
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground py-6 text-center">
                No documents uploaded or captured for this case yet.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Tab 4: Voucher Recovery Status */}
      {activeTab === "vouchers" && (
        <Card>
          <CardHeader className="pb-3 border-b border-border">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <DollarSign className="h-4 w-4 text-emerald-400" />
                  Nueces County Indigent Defense Vouchers
                </CardTitle>
                <CardDescription>
                  Texas Fair Defense Act statutory fee recovery for this docket.
                </CardDescription>
              </div>
              <Button
                size="sm"
                onClick={() => autoBuildMutation.mutate()}
                disabled={autoBuildMutation.isPending}
                className="text-xs h-7 gap-1"
              >
                <Plus className="h-3.5 w-3.5" />
                Build Voucher
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-4">
            {vouchers && vouchers.length > 0 ? (
              <div className="space-y-3">
                {vouchers.map((v: any) => (
                  <div
                    key={v.id}
                    className="p-4 rounded-lg border border-border bg-muted/15 flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-foreground text-sm">{v.voucher_number}</span>
                        <Badge variant="purple">{v.voucher_type}</Badge>
                      </div>
                      <div className="text-muted-foreground">
                        Claimed Amount: <strong className="text-foreground font-mono">${v.amount_requested?.toFixed(2)}</strong>
                      </div>
                      {v.submission_deadline && (
                        <div className="text-[11px] text-amber-400 font-medium">
                          Statutory Deadline: {formatDate(v.submission_deadline)} ({v.days_left != null ? `${v.days_left} days left` : ""})
                        </div>
                      )}
                      {v.notes && <div className="text-muted-foreground/80 italic text-[11px]">{v.notes}</div>}
                    </div>

                    <div className="flex items-center gap-3">
                      <Button asChild size="sm" variant="outline" className="h-7 text-xs">
                        <Link to="/vouchers">
                          Open in Voucher Radar
                          <ArrowRight className="h-3 w-3 ml-1" />
                        </Link>
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center text-muted-foreground text-xs space-y-3">
                <DollarSign className="h-8 w-8 mx-auto text-muted-foreground/40" />
                <p>No voucher created yet for this case.</p>
                <Button
                  size="sm"
                  onClick={() => autoBuildMutation.mutate()}
                  className="text-xs"
                >
                  1-Click Auto-Generate Voucher
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
