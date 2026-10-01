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
  Sparkles,
  Copy,
  Check,
  RefreshCw,
  AlertOctagon,
  Eye,
  Edit,
  Trash2,
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

  // Edit Case Details State
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [editCaseForm, setEditCaseForm] = useState<any>({})

  // Timeline Import & Manual Event State
  const [isImportTimelineOpen, setIsImportTimelineOpen] = useState(false)
  const [importTimelineText, setImportTimelineText] = useState("")
  const [isAddEventOpen, setIsAddEventOpen] = useState(false)
  const [newEventForm, setNewEventForm] = useState({
    title: "",
    event_type: "DOCKET_EVENT",
    event_date: "",
    description: "",
  })

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

  // Timeline Mutations
  const importTimelineMutation = useMutation({
    mutationFn: (raw_text: string) => api.cases.importPortalTimeline(caseId, raw_text),
    onSuccess: (res: any) => {
      queryClient.invalidateQueries({ queryKey: ["case-timeline", caseId] })
      setIsImportTimelineOpen(false)
      setImportTimelineText("")
      alert(`Imported ${res.events_count || 0} events from Odyssey Portal summary!`)
    },
    onError: (err: any) => {
      alert(`Timeline import failed: ${err.message || "Error parsing text"}`)
    },
  })

  const addEventMutation = useMutation({
    mutationFn: (data: any) => api.cases.addEvent(caseId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["case-timeline", caseId] })
      setIsAddEventOpen(false)
      setNewEventForm({ title: "", event_type: "DOCKET_EVENT", event_date: "", description: "" })
    },
    onError: (err: any) => {
      alert(`Failed to add event: ${err.message || "Unknown error"}`)
    },
  })

  const deleteEventMutation = useMutation({
    mutationFn: (eventId: number) => api.cases.deleteEvent(caseId, eventId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["case-timeline", caseId] })
    },
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
      queryClient.invalidateQueries({ queryKey: ["dashboard-alerts"] })
      setIsEditModalOpen(false)
    },
  })

  const handleOpenEditCase = () => {
    if (caseData) {
      setEditCaseForm({
        case_number: caseData.case_number || "",
        court: caseData.court || "",
        judge: caseData.judge || "",
        charge_description: caseData.charge_description || "",
        appellate_court: caseData.appellate_court || "",
        appellate_case_number: caseData.appellate_case_number || "",
        trial_court_case_number: caseData.trial_court_case_number || "",
        appellate_brief_due_date: caseData.appellate_brief_due_date ? caseData.appellate_brief_due_date.slice(0, 10) : "",
        stage: caseData.stage || "DISCOVERY",
        status: caseData.status || "open",
        is_cja: caseData.is_cja || false,
        in_custody: caseData.in_custody || false,
        jail_facility: caseData.jail_facility || "Nueces County Jail - Main",
        notes: caseData.notes || "",
      })
      setIsEditModalOpen(true)
    }
  }

  const handleSaveEditCase = () => {
    updateCaseMutation.mutate(editCaseForm)
  }

  // Discovery Gap Audit Query
  const { data: auditData, isLoading: auditLoading } = useQuery({
    queryKey: ["case-discovery-audit", caseId],
    queryFn: () => api.discovery.getAudit(caseId),
    enabled: !isNaN(caseId),
  })

  // Run Automated Discovery Audit Mutation
  const runAuditMutation = useMutation({
    mutationFn: () => api.discovery.runAudit(caseId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["case-discovery-audit", caseId] })
      queryClient.invalidateQueries({ queryKey: ["case", caseId] })
    },
  })

  const [motionText, setMotionText] = useState<string | null>(null)
  const [copiedMotion, setCopiedMotion] = useState(false)
  const [isGeneratingMotion, setIsGeneratingMotion] = useState(false)

  const [appellateDraftText, setAppellateDraftText] = useState<string | null>(null)
  const [copiedAppellateDraft, setCopiedAppellateDraft] = useState(false)
  const [isGeneratingAppellateMotion, setIsGeneratingAppellateMotion] = useState(false)

  const handleGenerateMotion = async () => {
    setIsGeneratingMotion(true)
    try {
      const text = await api.discovery.getMotionToCompel(caseId)
      setMotionText(text)
    } catch (err) {
      console.error("Failed to generate motion to compel", err)
    } finally {
      setIsGeneratingMotion(false)
    }
  }

  const handleCopyMotion = () => {
    if (motionText) {
      navigator.clipboard.writeText(motionText)
      setCopiedMotion(true)
      setTimeout(() => setCopiedMotion(false), 2500)
    }
  }

  const handleGenerateAppellateMotion = async () => {
    setIsGeneratingAppellateMotion(true)
    try {
      const res = await api.cases.getAppellateExtensionDraft(caseId)
      setAppellateDraftText(res.draft_pleading_text)
    } catch (err) {
      console.error("Failed to generate appellate motion draft", err)
    } finally {
      setIsGeneratingAppellateMotion(false)
    }
  }

  const handleCopyAppellateDraft = () => {
    if (appellateDraftText) {
      navigator.clipboard.writeText(appellateDraftText)
      setCopiedAppellateDraft(true)
      setTimeout(() => setCopiedAppellateDraft(false), 2500)
    }
  }

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

  let appellateDaysLeft: number | null = null
  if (caseData.appellate_brief_due_date) {
    try {
      const due = new Date(caseData.appellate_brief_due_date.slice(0, 10))
      const today = new Date()
      today.setHours(0, 0, 0, 0)
      appellateDaysLeft = Math.ceil((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
    } catch {}
  }
  const isAppellateCase = Boolean(caseData.appellate_brief_due_date || caseData.stage === "APPEAL" || caseData.appellate_case_number)

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
                {isAppellateCase ? (
                  <Badge variant="teal" className="bg-cyan-500/20 text-cyan-300 border-cyan-500/40 gap-1 flex items-center font-bold">
                    <Scale className="h-3 w-3" />
                    13th Court of Appeals
                  </Badge>
                ) : caseData.is_cja ? (
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

            {/* Top Right Action Buttons */}
            <div className="flex flex-col sm:flex-row items-end sm:items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleOpenEditCase}
                className="text-xs gap-1.5 border-border hover:bg-muted"
              >
                <Edit className="h-3.5 w-3.5 text-primary" />
                Edit Case Details
              </Button>
              {caseData.is_cja && !isAppellateCase && (
                <Button
                  onClick={() => autoBuildMutation.mutate()}
                  disabled={autoBuildMutation.isPending}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5 text-xs shadow-md"
                >
                  <DollarSign className="h-4 w-4" />
                  1-Click Auto-Build Voucher
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Texas 13th Court of Appeals Brief Extension & Due Date Card */}
      {isAppellateCase && (
        <Card className={`border ${
          appellateDaysLeft !== null && appellateDaysLeft < 0
            ? "bg-red-950/30 border-red-500/50 text-red-300"
            : appellateDaysLeft !== null && appellateDaysLeft <= 7
            ? "bg-amber-950/25 border-amber-500/50 text-amber-300"
            : "bg-cyan-950/20 border-cyan-500/40 text-cyan-300"
        }`}>
          <CardContent className="p-4">
            <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
              <div className="space-y-2 flex-1">
                <div className="flex items-center gap-2.5 flex-wrap">
                  <Scale className="h-5 w-5 text-cyan-400 shrink-0" />
                  <span className="text-foreground font-bold text-sm">
                    13th Court of Appeals — Appellant's Brief Extension Tracker
                  </span>
                  {appellateDaysLeft !== null && appellateDaysLeft < 0 ? (
                    <Badge variant="destructive" className="bg-red-600 text-white font-bold text-xs animate-pulse">
                      OVERDUE BY {Math.abs(appellateDaysLeft)} DAYS (TRAP 38.8)
                    </Badge>
                  ) : appellateDaysLeft !== null && appellateDaysLeft <= 7 ? (
                    <Badge variant="destructive" className="bg-amber-500/20 text-amber-300 border-amber-500/50 font-bold text-xs">
                      ⚠️ {appellateDaysLeft} DAYS REMAINING (URGENT)
                    </Badge>
                  ) : (
                    <Badge variant="teal" className="bg-cyan-500/20 text-cyan-300 border-cyan-500/40 font-semibold text-xs">
                      ⏱️ {appellateDaysLeft ?? "—"} Days Remaining
                    </Badge>
                  )}
                  <Badge variant="outline" className="text-[10px] uppercase font-mono">
                    {caseData.appellate_motion_status === "EXTENSION_GRANTED" ? "Extension Granted" : "Motion Pending"}
                  </Badge>
                </div>

                <p className="text-xs text-muted-foreground leading-relaxed">
                  {caseData.appellate_motion_status === "EXTENSION_GRANTED"
                    ? `The 13th Court of Appeals officially GRANTED Appellant's motion for extension of time under Tex. R. App. P. 38.6(d). The primary argumentative document must be e-filed on or before the calendar deadline.`
                    : `Counsel filed a formal Motion to Extend Time for Filing Appellant's Brief under Tex. R. App. P. 10.5(b) & 38.6(d) requesting an enlarged 30-day deadline.`}
                </p>

                {/* Stated Good Cause & Docket Data Chips */}
                <div className="flex flex-wrap items-center gap-3 text-xs pt-1">
                  <div className="bg-card/60 px-2.5 py-1 rounded border border-border flex items-center gap-1.5">
                    <span className="text-muted-foreground text-[11px]">Appellate Cause:</span>
                    <strong className="text-foreground font-mono">{caseData.appellate_case_number || caseData.case_number}</strong>
                  </div>

                  {caseData.trial_court_case_number && (
                    <div className="bg-card/60 px-2.5 py-1 rounded border border-border flex items-center gap-1.5">
                      <span className="text-muted-foreground text-[11px]">Trial Court Cause:</span>
                      <strong className="text-foreground font-mono">{caseData.trial_court_case_number}</strong>
                    </div>
                  )}

                  <div className="bg-card/60 px-2.5 py-1 rounded border border-border flex items-center gap-1.5">
                    <span className="text-muted-foreground text-[11px]">Brief Due Date:</span>
                    <strong className="text-foreground font-mono">
                      {caseData.appellate_brief_due_date ? formatDate(caseData.appellate_brief_due_date) : "Pending Schedule"}
                    </strong>
                  </div>

                  <div className="bg-card/60 px-2.5 py-1 rounded border border-border flex items-center gap-1.5">
                    <span className="text-muted-foreground text-[11px]">Extension Count:</span>
                    <strong className="text-foreground font-mono">
                      {caseData.appellate_extension_count ? `${caseData.appellate_extension_count} Granted/Filed` : "1st Request"}
                    </strong>
                  </div>
                </div>

                {caseData.appellate_extension_reason && (
                  <div className="text-xs bg-slate-950/40 p-2.5 rounded-lg border border-cyan-500/15 text-slate-300">
                    <strong className="text-cyan-200">Good Cause Statement on Record: </strong>
                    <span className="italic">{caseData.appellate_extension_reason}</span>
                  </div>
                )}
              </div>

              <div className="shrink-0 flex sm:flex-col items-end justify-center gap-2">
                <Button
                  size="sm"
                  onClick={handleGenerateAppellateMotion}
                  disabled={isGeneratingAppellateMotion}
                  className="text-xs h-7.5 gap-1.5 bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white shadow-xs"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  Draft Next Motion to Extend
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => updateCaseMutation.mutate({ appellate_motion_status: "BRIEF_FILED" })}
                  className="text-xs h-7 gap-1 border-cyan-500/30 text-cyan-300 hover:bg-cyan-950/40"
                >
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                  Mark Brief Filed
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Interactive Appellate Pleading Viewer Drawer / Modal */}
      {appellateDraftText && (
        <Card className="border-cyan-500/40 bg-slate-950 shadow-xl animate-fadeIn">
          <CardHeader className="pb-3 border-b border-cyan-500/20 flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-sm font-bold text-cyan-200 flex items-center gap-2">
                <FileText className="h-4 w-4 text-cyan-400" />
                Pleading Draft: Motion to Extend Time for Filing Appellant's Brief (13th Court of Appeals)
              </CardTitle>
              <CardDescription className="text-xs">
                File-ready Texas appellate motion conforming to Tex. R. App. P. 10.5(b) &amp; 38.6(d).
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={handleCopyAppellateDraft}
                className="text-xs gap-1.5 border-cyan-500/30 text-cyan-300 hover:bg-cyan-950/60"
              >
                {copiedAppellateDraft ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                {copiedAppellateDraft ? "Copied!" : "Copy Pleading"}
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setAppellateDraftText(null)}
                className="text-xs text-muted-foreground hover:text-white"
              >
                Close
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-4">
            <pre className="p-4 rounded-lg bg-slate-900 border border-slate-800 text-cyan-100 font-mono text-xs leading-relaxed overflow-x-auto max-h-96 whitespace-pre-wrap">
              {appellateDraftText}
            </pre>
          </CardContent>
        </Card>
      )}


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

      {/* Tab 2: Michael Morton Act Discovery Checklist & "Red Ink" Gap Auditor */}
      {activeTab === "morton" && (
        <div className="space-y-6">
          {/* 1. Automated Discovery Gap Auditor Command Card */}
          <Card className="border-border bg-gradient-to-r from-card via-card to-cyan-950/20">
            <CardHeader className="pb-3 border-b border-border">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <CardTitle className="text-base flex items-center gap-2">
                    <FileCheck className="h-5 w-5 text-cyan-400" />
                    <span>Michael Morton Act Discovery Gap Auditor (Art. 39.14 CCP)</span>
                  </CardTitle>
                  <CardDescription>
                    Automated scan of police narratives, CAD logs, and chain of custody records to identify missing discovery and constitutional suppression triggers.
                  </CardDescription>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => runAuditMutation.mutate()}
                    disabled={runAuditMutation.isPending}
                    className="text-xs gap-1.5 border-cyan-500/30 text-cyan-300 hover:bg-cyan-950/40"
                  >
                    <RefreshCw className={`h-3.5 w-3.5 ${runAuditMutation.isPending ? "animate-spin text-cyan-400" : ""}`} />
                    Run Gap Audit
                  </Button>

                  <Button
                    size="sm"
                    onClick={handleGenerateMotion}
                    disabled={isGeneratingMotion}
                    className="text-xs gap-1.5 bg-cyan-600 hover:bg-cyan-500 text-white font-medium shadow-xs"
                  >
                    <Sparkles className="h-3.5 w-3.5" />
                    Draft Motion to Compel
                  </Button>
                </div>
              </div>
            </CardHeader>

            <CardContent className="p-6">
              {auditLoading ? (
                <div className="text-center py-6 text-xs text-muted-foreground">Running evidentiary audit...</div>
              ) : auditData ? (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="p-3 rounded-lg bg-card border border-border">
                    <div className="text-[11px] text-muted-foreground font-medium">Mentioned in Narratives</div>
                    <div className="text-xl font-bold text-foreground mt-0.5">{auditData.summary?.total_items_mentioned ?? 0}</div>
                  </div>
                  <div className="p-3 rounded-lg bg-emerald-950/20 border border-emerald-500/30">
                    <div className="text-[11px] text-emerald-300 font-medium">Verified in Discovery</div>
                    <div className="text-xl font-bold text-emerald-400 mt-0.5">{auditData.summary?.produced_count ?? 0}</div>
                  </div>
                  <div className={`p-3 rounded-lg border ${
                    (auditData.summary?.missing_count ?? 0) > 0
                      ? "bg-red-950/30 border-red-500/50 text-red-300"
                      : "bg-card border-border"
                  }`}>
                    <div className="text-[11px] font-medium">Missing Evidence Gaps</div>
                    <div className="text-xl font-bold text-red-400 mt-0.5 flex items-center gap-1.5">
                      {auditData.summary?.missing_count ?? 0}
                      {(auditData.summary?.missing_count ?? 0) > 0 && (
                        <span className="text-xs px-1.5 py-0.5 rounded-sm bg-red-500/20 text-red-300 border border-red-500/30">RED INK</span>
                      )}
                    </div>
                  </div>
                  <div className={`p-3 rounded-lg border ${
                    (auditData.summary?.suppression_flags_count ?? 0) > 0
                      ? "bg-amber-950/30 border-amber-500/50 text-amber-300"
                      : "bg-card border-border"
                  }`}>
                    <div className="text-[11px] font-medium">Suppression Triggers</div>
                    <div className="text-xl font-bold text-amber-400 mt-0.5">{auditData.summary?.suppression_flags_count ?? 0}</div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-4 text-xs text-muted-foreground">Click "Run Gap Audit" to cross-reference police narratives against state productions.</div>
              )}
            </CardContent>
          </Card>

          {/* 2. Motion to Compel Interactive Pleading Viewer */}
          {motionText && (
            <Card className="border-cyan-500/40 bg-slate-950 shadow-xl animate-fadeIn">
              <CardHeader className="pb-3 border-b border-cyan-500/20 flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-sm font-bold text-cyan-200 flex items-center gap-2">
                    <FileText className="h-4 w-4 text-cyan-400" />
                    Pleading Draft: Defendant's Notice of Discovery Deficit &amp; Motion to Compel (Art. 39.14 CCP)
                  </CardTitle>
                  <CardDescription className="text-xs">
                    File-ready Texas pleading referencing Watkins v. State, 619 S.W.3d 265 and itemized deficits.
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleCopyMotion}
                    className="text-xs gap-1.5 border-cyan-500/30 text-cyan-300 hover:bg-cyan-950/60"
                  >
                    {copiedMotion ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                    {copiedMotion ? "Copied!" : "Copy Pleading"}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setMotionText(null)}
                    className="text-xs text-muted-foreground hover:text-white"
                  >
                    Close
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="p-4">
                <pre className="p-4 rounded-lg bg-slate-900 border border-slate-800 text-cyan-100 font-mono text-xs leading-relaxed overflow-x-auto max-h-96 whitespace-pre-wrap">
                  {motionText}
                </pre>
              </CardContent>
            </Card>
          )}

          {/* 3. Red Ink Missing Evidence Deficits */}
          {auditData?.missing_evidence && auditData.missing_evidence.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-red-400 flex items-center gap-1.5">
                  <AlertOctagon className="h-4 w-4 text-red-500" />
                  Red Ink Missing Evidence Deficits ({auditData.missing_evidence.length})
                </h3>
                <span className="text-[11px] text-muted-foreground">Disclosed in Narrative &bull; Missing from State Production</span>
              </div>

              <div className="space-y-2.5">
                {auditData.missing_evidence.map((gap: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-4 rounded-xl border border-red-500/40 bg-red-950/20 shadow-xs flex flex-col sm:flex-row sm:items-start justify-between gap-3"
                  >
                    <div className="space-y-1.5 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-bold text-red-200">{gap.name}</span>
                        <Badge variant="destructive" className="text-[10px] bg-red-500/20 text-red-300 border-red-500/40">
                          {gap.category}
                        </Badge>
                        <span className="text-[10px] font-mono text-red-400/90">{gap.statutory_basis}</span>
                      </div>
                      <p className="text-xs text-slate-300 italic bg-slate-950/40 p-2.5 rounded-lg border border-red-500/10">
                        {gap.snippet}
                      </p>
                    </div>

                    <div className="shrink-0 self-end sm:self-center">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={handleGenerateMotion}
                        className="text-xs border-red-500/40 text-red-300 hover:bg-red-950/50"
                      >
                        Compel in Motion
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 4. Constitutional & Statutory Suppression Triggers */}
          {auditData?.suppression_flags && auditData.suppression_flags.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
                  <Shield className="h-4 w-4 text-amber-500" />
                  Constitutional &amp; Procedural Suppression Flags ({auditData.suppression_flags.length})
                </h3>
              </div>

              <div className="space-y-2.5">
                {auditData.suppression_flags.map((sup: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-4 rounded-xl border border-amber-500/40 bg-amber-950/20 shadow-xs space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-bold text-amber-200">{sup.title}</span>
                        <Badge variant="warning" className="text-[10px] bg-amber-500/20 text-amber-300 border-amber-500/40">
                          {sup.basis}
                        </Badge>
                      </div>
                      <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">{sup.severity}</span>
                    </div>
                    <p className="text-xs text-slate-300">{sup.description}</p>
                    <div className="text-[11px] text-amber-400/90 italic bg-slate-950/50 p-2 rounded border border-amber-500/15">
                      Grounds: {sup.recommended_motion}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 5. Standard Morton Checklist */}
          <Card>
            <CardHeader className="pb-3 border-b border-border">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-sm flex items-center gap-2 font-semibold">
                    <FileCheck className="h-4 w-4 text-primary" />
                    State Discovery Disclosures Checklist
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Manual receipt override and inspection confirmation.
                  </CardDescription>
                </div>
                <Badge variant={mortonCompleteCount === totalMortonCount ? "success" : "info"}>
                  {mortonCompleteCount} of {totalMortonCount} checked
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
        </div>
      )}

      {/* Tab 3: Case Timeline (Docket History) */}
      {activeTab === "timeline" && (
        <Card>
          <CardHeader className="pb-3 border-b border-border">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <CardTitle className="text-base flex items-center gap-2">
                  <Clock className="h-5 w-5 text-primary" />
                  Case Docket &amp; Event Timeline
                </CardTitle>
                <CardDescription>
                  Chronological record of docket milestones, Odyssey Portal history, and statutory deadlines.
                </CardDescription>
              </div>

              <div className="flex items-center gap-2">
                <Badge variant="info">{timelineEvents?.events?.length || 0} events</Badge>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setIsImportTimelineOpen(true)}
                  className="h-8 text-xs gap-1.5 border-cyan-500/40 text-cyan-300 hover:bg-cyan-950/40"
                >
                  <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
                  Import Odyssey Summary
                </Button>
                <Button
                  size="sm"
                  onClick={() => setIsAddEventOpen(true)}
                  className="h-8 text-xs gap-1.5 bg-primary hover:bg-primary/90 text-primary-foreground"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Add Event
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {timelineEvents?.events && timelineEvents.events.length > 0 ? (
              <div className="divide-y divide-border/60">
                {timelineEvents.events.map((ev: any, idx: number) => {
                  const evType = (ev.event_type || "").toUpperCase()
                  let badgeVariant: "purple" | "teal" | "warning" | "destructive" | "info" | "muted" = "muted"
                  let badgeLabel = ev.event_type || "Event"

                  if (evType.includes("COMPETENCY")) {
                    badgeVariant = "warning"
                    badgeLabel = "Competency Evaluation"
                  } else if (evType.includes("PLEA") || evType.includes("SENTENC")) {
                    badgeVariant = "destructive"
                    badgeLabel = "Plea & Sentencing"
                  } else if (evType.includes("ABATEMENT")) {
                    badgeVariant = "purple"
                    badgeLabel = "COA Abatement"
                  } else if (evType.includes("APPEAL")) {
                    badgeVariant = "teal"
                    badgeLabel = "13th COA Appeal"
                  } else if (evType.includes("ARREST") || evType.includes("INDICT")) {
                    badgeVariant = "info"
                    badgeLabel = "Arrest & Indictment"
                  } else if (evType.includes("APPOINT")) {
                    badgeVariant = "teal"
                    badgeLabel = "Counsel Appointed"
                  } else if (evType.includes("DEADLINE")) {
                    badgeVariant = "warning"
                    badgeLabel = "Statutory Deadline"
                  }

                  return (
                    <div key={ev.id ?? idx} className="p-4 flex items-start justify-between gap-4 hover:bg-muted/20 transition-colors group">
                      <div className="flex items-start gap-3.5 flex-1 min-w-0">
                        {/* Timeline dot */}
                        <div className="shrink-0 mt-1 flex flex-col items-center gap-1">
                          <div className={`h-2.5 w-2.5 rounded-full ${
                            badgeVariant === "destructive" ? "bg-red-400 ring-2 ring-red-400/30" :
                            badgeVariant === "warning" ? "bg-amber-400 ring-2 ring-amber-400/30" :
                            badgeVariant === "teal" ? "bg-cyan-400 ring-2 ring-cyan-400/30" :
                            badgeVariant === "purple" ? "bg-purple-400 ring-2 ring-purple-400/30" :
                            "bg-primary ring-2 ring-primary/30"
                          }`} />
                          {idx < (timelineEvents.events.length - 1) && (
                            <div className="w-px flex-1 min-h-6 bg-border/60" />
                          )}
                        </div>

                        <div className="flex-1 min-w-0 space-y-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-xs font-bold text-foreground">{ev.title}</span>
                            <Badge variant={badgeVariant} className="text-[10px] uppercase font-mono">
                              {badgeLabel}
                            </Badge>
                          </div>
                          {ev.description && (
                            <p className="text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap">{ev.description}</p>
                          )}
                          <div className="text-[10px] text-muted-foreground/80 font-mono flex items-center gap-2 pt-0.5">
                            <Calendar className="h-3 w-3 inline text-primary/70" />
                            <span>
                              {ev.event_date || ev.created_at
                                ? formatDate(ev.event_date || ev.created_at)
                                : "Date unknown"}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Delete Event Action */}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          if (confirm(`Delete event "${ev.title}"?`)) {
                            deleteEventMutation.mutate(ev.id)
                          }
                        }}
                        className="h-7 w-7 p-0 text-muted-foreground hover:text-rose-400 hover:bg-rose-950/30 opacity-0 group-hover:opacity-100 transition-opacity"
                        title="Delete event"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="p-10 text-center text-muted-foreground text-xs space-y-3">
                <Clock className="h-8 w-8 mx-auto text-muted-foreground/30" />
                <p className="font-semibold text-foreground">No docket events recorded yet for this case.</p>
                <p className="text-[11px] text-muted-foreground/70 max-w-sm mx-auto">
                  Paste summary text from Odyssey Portal or add docket events manually to populate the timeline.
                </p>
                <div className="flex justify-center gap-2 pt-1">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setIsImportTimelineOpen(true)}
                    className="text-xs border-cyan-500/40 text-cyan-300"
                  >
                    <Sparkles className="h-3.5 w-3.5 mr-1" />
                    Import Odyssey Summary
                  </Button>
                </div>
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

      {/* Edit Case Details Modal */}
      {isEditModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-xs">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Edit className="w-5 h-5 text-cyan-400" />
                <h3 className="text-base font-bold text-white">Edit Case Record &amp; Provenance</h3>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsEditModalOpen(false)}
                className="h-7 w-7 p-0 text-slate-400 hover:text-white"
              >
                ✕
              </Button>
            </div>

            <div className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1 font-semibold">Primary Case Number</label>
                  <input
                    type="text"
                    value={editCaseForm.case_number || ""}
                    onChange={(e) => setEditCaseForm({ ...editCaseForm, case_number: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-white font-mono"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1 font-semibold">Charge Description</label>
                  <input
                    type="text"
                    value={editCaseForm.charge_description || ""}
                    onChange={(e) => setEditCaseForm({ ...editCaseForm, charge_description: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1 font-semibold">Court / Appellate Venue</label>
                  <input
                    type="text"
                    value={editCaseForm.court || ""}
                    onChange={(e) => setEditCaseForm({ ...editCaseForm, court: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-white"
                    placeholder="e.g. 13th Court of Appeals (Corpus Christi - Edinburg)"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1 font-semibold">Presiding Judge / Clerk</label>
                  <input
                    type="text"
                    value={editCaseForm.judge || ""}
                    onChange={(e) => setEditCaseForm({ ...editCaseForm, judge: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-white"
                    placeholder="e.g. Kathy S. Mills, Clerk / Hon. James D. Granberry"
                  />
                </div>
              </div>

              {/* Appellate Linkage Fields */}
              <div className="bg-slate-950/80 border border-cyan-500/30 rounded-xl p-3.5 space-y-3">
                <span className="text-cyan-400 font-bold block text-xs uppercase tracking-wider">
                  Appellate &amp; Trial Court Linking (Texas 13th COA)
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="text-slate-400 block mb-1">Appellate Cause #</label>
                    <input
                      type="text"
                      value={editCaseForm.appellate_case_number || ""}
                      onChange={(e) => setEditCaseForm({ ...editCaseForm, appellate_case_number: e.target.value })}
                      className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-white font-mono"
                      placeholder="e.g. 13-26-00155-CR"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Trial Court Cause #</label>
                    <input
                      type="text"
                      value={editCaseForm.trial_court_case_number || ""}
                      onChange={(e) => setEditCaseForm({ ...editCaseForm, trial_court_case_number: e.target.value })}
                      className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-white font-mono"
                      placeholder="e.g. 24FC-2874E"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Brief Due Date</label>
                    <input
                      type="date"
                      value={editCaseForm.appellate_brief_due_date || ""}
                      onChange={(e) => setEditCaseForm({ ...editCaseForm, appellate_brief_due_date: e.target.value })}
                      className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-white"
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1 font-semibold">Lifecycle Stage</label>
                  <select
                    value={editCaseForm.stage || "DISCOVERY"}
                    onChange={(e) => setEditCaseForm({ ...editCaseForm, stage: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-white"
                  >
                    <option value="MAGISTRATE_HEARING">Magistrate Hearing</option>
                    <option value="ARREST">Arrest &amp; Magistration</option>
                    <option value="BOND">Bail &amp; Conditions</option>
                    <option value="INDICTMENT">Grand Jury</option>
                    <option value="DISCOVERY">Morton Discovery</option>
                    <option value="PRE_TRIAL">Pre-Trial &amp; Suppression</option>
                    <option value="TRIAL">Plea / Trial</option>
                    <option value="APPEAL">Appeal (13th Court of Appeals)</option>
                    <option value="DISPOSED">Disposed / Vouchers</option>
                  </select>
                </div>
                <div>
                  <label className="text-slate-400 block mb-1 font-semibold">Case Status</label>
                  <select
                    value={editCaseForm.status || "open"}
                    onChange={(e) => setEditCaseForm({ ...editCaseForm, status: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-white"
                  >
                    <option value="open">Open</option>
                    <option value="pending">Pending</option>
                    <option value="DISPOSED">Disposed</option>
                    <option value="CLOSED">Closed</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-slate-400 block mb-1 font-semibold">Attorney Notes &amp; History</label>
                <textarea
                  rows={3}
                  value={editCaseForm.notes || ""}
                  onChange={(e) => setEditCaseForm({ ...editCaseForm, notes: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded p-2.5 text-white text-xs"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 border-t border-slate-800 pt-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsEditModalOpen(false)}
                className="text-xs border-slate-700 text-slate-300"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSaveEditCase}
                disabled={updateCaseMutation.isPending}
                className="text-xs bg-cyan-600 hover:bg-cyan-500 text-white font-semibold"
              >
                {updateCaseMutation.isPending ? "Saving..." : "Save Case Details"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Import Odyssey Portal Summary Modal */}
      {isImportTimelineOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-xs">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-xl w-full p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-cyan-400" />
                <h3 className="text-base font-bold text-white">Import Odyssey Portal Summary</h3>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsImportTimelineOpen(false)}
                className="h-7 w-7 p-0 text-slate-400 hover:text-white"
              >
                ✕
              </Button>
            </div>

            <div className="space-y-3 text-xs">
              <p className="text-muted-foreground leading-relaxed">
                Paste raw case summary paragraphs, docket bullets, or hearing entries from the Tyler Odyssey Portal. Filestavk will parse the dates, milestones, competency hearings, and procedural actions into chronological timeline events.
              </p>

              <div>
                <label className="text-slate-300 block mb-1 font-semibold">Odyssey Portal Narrative / Docket Summary Text</label>
                <textarea
                  rows={8}
                  value={importTimelineText}
                  onChange={(e) => setImportTimelineText(e.target.value)}
                  placeholder="e.g. July 5, 2024 – October 14, 2024 (Arrest & Indictment): Defendant charged with Aggravated Robbery...&#10;&#10;December 3, 2024 (Incompetency Finding): Court found defendant incompetent..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-white font-mono text-xs leading-relaxed focus:border-cyan-500/50"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 border-t border-slate-800 pt-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsImportTimelineOpen(false)}
                className="text-xs border-slate-700 text-slate-300"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={() => importTimelineMutation.mutate(importTimelineText)}
                disabled={importTimelineMutation.isPending || !importTimelineText.trim()}
                className="text-xs bg-cyan-600 hover:bg-cyan-500 text-white font-semibold gap-1.5"
              >
                <Sparkles className="h-3.5 w-3.5" />
                {importTimelineMutation.isPending ? "Parsing..." : "Parse & Import Timeline"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Add Single Manual Event Modal */}
      {isAddEventOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-xs">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Plus className="w-5 h-5 text-primary" />
                <h3 className="text-base font-bold text-white">Add Timeline Event</h3>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsAddEventOpen(false)}
                className="h-7 w-7 p-0 text-slate-400 hover:text-white"
              >
                ✕
              </Button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-400 block mb-1 font-semibold">Event Title</label>
                <input
                  type="text"
                  value={newEventForm.title}
                  onChange={(e) => setNewEventForm({ ...newEventForm, title: e.target.value })}
                  placeholder="e.g. Competency Hearing Held"
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1 font-semibold">Event Type</label>
                  <select
                    value={newEventForm.event_type}
                    onChange={(e) => setNewEventForm({ ...newEventForm, event_type: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-white"
                  >
                    <option value="DOCKET_EVENT">Docket Event</option>
                    <option value="HEARING">Court Hearing</option>
                    <option value="ORDER">Judicial Order</option>
                    <option value="MOTION">Motion Filed</option>
                    <option value="COMPETENCY">Competency</option>
                    <option value="PLEA_SENTENCING">Plea &amp; Sentencing</option>
                    <option value="APPEAL">Appeal / Record</option>
                    <option value="ABATEMENT">COA Abatement</option>
                    <option value="APPOINTMENT_ORDER">Appointment</option>
                    <option value="DEADLINE">Deadline</option>
                  </select>
                </div>
                <div>
                  <label className="text-slate-400 block mb-1 font-semibold">Event Date</label>
                  <input
                    type="date"
                    value={newEventForm.event_date}
                    onChange={(e) => setNewEventForm({ ...newEventForm, event_date: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-white"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-400 block mb-1 font-semibold">Description &amp; Procedural Notes</label>
                <textarea
                  rows={4}
                  value={newEventForm.description}
                  onChange={(e) => setNewEventForm({ ...newEventForm, description: e.target.value })}
                  placeholder="Details of the event, appearances, or court findings..."
                  className="w-full bg-slate-950 border border-slate-800 rounded p-2.5 text-white text-xs"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 border-t border-slate-800 pt-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsAddEventOpen(false)}
                className="text-xs border-slate-700 text-slate-300"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={() => addEventMutation.mutate(newEventForm)}
                disabled={addEventMutation.isPending || !newEventForm.title.trim()}
                className="text-xs bg-primary hover:bg-primary/90 text-primary-foreground font-semibold"
              >
                {addEventMutation.isPending ? "Adding..." : "Add Event"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
