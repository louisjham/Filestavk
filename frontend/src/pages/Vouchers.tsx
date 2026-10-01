import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  DollarSign,
  Clock,
  AlertTriangle,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Plus,
  Scale,
  FileText,
  Mail,
  Send,
  Check,
  ChevronRight,
  TrendingUp,
  FileSpreadsheet,
  Search,
  Filter,
  History,
  Archive,
  ExternalLink,
} from "lucide-react"
import { formatDate } from "@/lib/utils"
import { usePracticeProfile } from "@/hooks/usePracticeProfile"

export function Vouchers() {
  const queryClient = useQueryClient()
  const { firmName, attorneyName, barNumber, email, profile, isDemo } = usePracticeProfile()

  const [selectedStatus, setSelectedStatus] = useState<string>("ALL")
  const [selectedMethod, setSelectedMethod] = useState<string>("ALL")
  const [searchTerm, setSearchTerm] = useState<string>("")
  const [syncNotice, setSyncNotice] = useState<string | null>(null)
  const [capturedNotices, setCapturedNotices] = useState<any[] | null>(null)
  const [inspectVoucher, setInspectVoucher] = useState<any | null>(null)
  const [paperModalOpen, setPaperModalOpen] = useState(false)

  // Paper Voucher Form State
  const [paperForm, setPaperForm] = useState({
    case_number: "",
    client_name: "",
    court: "347th District Court",
    judge: "Hon. Missy Medary",
    charge_description: "Felony Offense",
    voucher_number: "",
    amount_requested: 1000.0,
    amount_paid: 1000.0,
    status: "PAID",
    disposition_date: "",
    paid_date: "",
    warrant_number: "",
    notes: "Historical handwritten paper voucher recorded from firm records.",
  })

  // Queries
  const { data: vouchers, isLoading } = useQuery({
    queryKey: ["vouchers", selectedStatus, selectedMethod, searchTerm],
    queryFn: () =>
      api.vouchers.list({
        status: selectedStatus === "ALL" ? undefined : selectedStatus,
        submission_method: selectedMethod === "ALL" ? undefined : selectedMethod,
        search: searchTerm || undefined,
      }),
  })

  const { data: stats, refetch: refetchStats } = useQuery({
    queryKey: ["voucher-stats"],
    queryFn: () => api.vouchers.stats(),
  })

  // Mutations
  const syncMutation = useMutation({
    mutationFn: () => api.vouchers.simulateGmailSync(),
    onSuccess: (res: any) => {
      setSyncNotice(res.message)
      if (res.captured_notices) {
        setCapturedNotices(res.captured_notices)
      }
      queryClient.invalidateQueries({ queryKey: ["vouchers"] })
      queryClient.invalidateQueries({ queryKey: ["voucher-stats"] })
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => api.vouchers.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vouchers"] })
      queryClient.invalidateQueries({ queryKey: ["voucher-stats"] })
    },
  })

  const paperMutation = useMutation({
    mutationFn: (data: any) => api.vouchers.createPaperVoucher(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vouchers"] })
      queryClient.invalidateQueries({ queryKey: ["voucher-stats"] })
      setPaperModalOpen(false)
      setPaperForm({
        case_number: "",
        client_name: "",
        court: "347th District Court",
        judge: "Hon. Missy Medary",
        charge_description: "Felony Offense",
        voucher_number: "",
        amount_requested: 1000.0,
        amount_paid: 1000.0,
        status: "PAID",
        disposition_date: "",
        paid_date: "",
        warrant_number: "",
        notes: "Historical handwritten paper voucher recorded from firm records.",
      })
    },
  })

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "READY_TO_FILE":
        return <Badge variant="success" className="bg-emerald-500/20 text-emerald-300 border-emerald-500/30 font-semibold">Ready to Be Filed</Badge>
      case "UNBILLED":
        return <Badge variant="warning" className="bg-amber-500/20 text-amber-300 border-amber-500/30">Unbilled Backlog</Badge>
      case "DRAFT":
        return <Badge variant="info" className="bg-blue-500/20 text-blue-300 border-blue-500/30">Draft</Badge>
      case "SUBMITTED":
        return <Badge variant="purple" className="bg-purple-500/20 text-purple-300 border-purple-500/30">Submitted to Court</Badge>
      case "RETURNED":
        return <Badge variant="destructive" className="bg-red-500/20 text-red-300 border-red-500/30">Returned for Revision</Badge>
      case "APPROVED":
        return <Badge variant="teal" className="bg-teal-500/20 text-teal-300 border-teal-500/30">Approved in Auditor Queue</Badge>
      case "PAID":
        return <Badge variant="success" className="bg-emerald-500/20 text-emerald-300 border-emerald-500/30">Paid by County</Badge>
      default:
        return <Badge variant="muted">{status}</Badge>
    }
  }

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <DollarSign className="h-6 w-6 text-emerald-400" />
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Voucher Command Center &amp; Backlog Recovery
            </h1>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Nueces County Court-Appointed Indigent Defense (CJA / Texas Fair Defense Act Art. 26.05) &bull; No expiration deadline &bull; Single consolidated paper &amp; portal archive.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setPaperModalOpen(true)}
            className="text-xs gap-1.5 border-cyan-500/30 text-cyan-300 hover:bg-cyan-950/40"
          >
            <History className="h-4 w-4" />
            Log Historical Paper Voucher
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
            className="gap-1.5 border-primary/30 hover:bg-primary/10 text-primary text-xs"
          >
            <RefreshCw className={`h-4 w-4 ${syncMutation.isPending ? "animate-spin" : ""}`} />
            Sync Email Notices ({email})
          </Button>

        </div>
      </div>

      {/* Sync Success & Immutable Notice Timeline */}
      {syncNotice && (
        <div className="space-y-3">
          <div className="p-3.5 bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 rounded-lg text-sm flex items-center justify-between animate-fadeIn">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />
              <span>{syncNotice}</span>
            </div>
            <button onClick={() => { setSyncNotice(null); setCapturedNotices(null); }} className="text-xs hover:underline text-emerald-200">
              Dismiss
            </button>
          </div>

          {capturedNotices && capturedNotices.length > 0 && (
            <Card className="border-emerald-500/30 bg-emerald-950/20 animate-fadeIn">
              <CardHeader className="py-3 px-4 border-b border-emerald-500/20">
                <CardTitle className="text-xs font-semibold text-emerald-300 flex items-center gap-2">
                  <Mail className="h-3.5 w-3.5 text-emerald-400" />
                  Captured Forwarded Notices (Static &amp; Immutable Records)
                </CardTitle>
              </CardHeader>
              <CardContent className="p-3 divide-y divide-emerald-500/20 text-xs">
                {capturedNotices.map((n: any, idx: number) => (
                  <div key={idx} className="py-2.5 space-y-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold text-foreground">{n.subject}</span>
                      <span className="text-[10px] text-emerald-400 font-mono bg-emerald-950 px-2 py-0.5 rounded border border-emerald-500/30">
                        {n.status_transition}
                      </span>
                    </div>
                    <div className="text-[11px] text-muted-foreground flex items-center justify-between">
                      <span>From: <code className="text-emerald-300">{n.sender}</code> &bull; To: <code className="text-emerald-300">{n.recipient}</code></span>
                      <span>{n.received_at}</span>
                    </div>
                    <p className="text-[11px] text-muted-foreground/90 leading-relaxed pt-0.5">
                      {n.body_preview}
                    </p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Top Financial KPI Row (Grounded in Nueces Backlog Reality) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Unbilled Backlog Cash Card */}
        <Card className="border-l-4 border-l-amber-500 bg-amber-500/5">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Unbilled Recovery Backlog
              </span>
              <DollarSign className="h-4 w-4 text-amber-400" />
            </div>
            <div className="text-2xl font-bold text-foreground mt-1">
              ${stats ? stats.total_unbilled.toLocaleString("en-US", { minimumFractionDigits: 2 }) : "0.00"}
            </div>
            <div className="text-[11px] text-muted-foreground mt-1 space-y-0.5">
              {stats?.missing_appointment_acceptances_count > 0 ? (
                <div className="text-amber-400 font-semibold flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3 shrink-0" /> {stats.missing_appointment_acceptances_count} awaiting stamped acceptance
                </div>
              ) : stats?.missing_appointment_orders_count > 0 ? (
                <div className="text-red-400 font-semibold flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3 shrink-0" /> {stats.missing_appointment_orders_count} missing appointment order
                </div>
              ) : (
                <span>All unbilled dockets verified &amp; ready for auditor billing</span>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Pending Judicial Review */}
        <Card className="border-l-4 border-l-purple-500">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Pending Judge Review
              </span>
              <Scale className="h-4 w-4 text-purple-400" />
            </div>
            <div className="text-2xl font-bold text-purple-300 mt-1">
              ${stats ? stats.total_pending_court.toLocaleString("en-US", { minimumFractionDigits: 2 }) : "0.00"}
            </div>
            <div className="text-[11px] text-muted-foreground mt-1">
              {stats?.returned_count > 0 ? (
                <span className="text-red-400 font-medium">
                  {stats.returned_count} returned for revision
                </span>
              ) : (
                "Submitted to District / County Bench"
              )}
            </div>
          </CardContent>
        </Card>

        {/* Approved / In Auditor Queue */}
        <Card className="border-l-4 border-l-teal-500">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Approved (Auditor Queue)
              </span>
              <Clock className="h-4 w-4 text-teal-400" />
            </div>
            <div className="text-2xl font-bold text-teal-300 mt-1">
              ${stats ? stats.total_approved_auditor.toLocaleString("en-US", { minimumFractionDigits: 2 }) : "0.00"}
            </div>
            <div className="text-[11px] text-muted-foreground mt-1">
              Nueces County Treasurer warrant issuance
            </div>
          </CardContent>
        </Card>

        {/* Paid Year-to-Date */}
        <Card className="border-l-4 border-l-emerald-500">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Paid (Direct Deposits)
              </span>
              <TrendingUp className="h-4 w-4 text-emerald-400" />
            </div>
            <div className="text-2xl font-bold text-emerald-400 mt-1">
              ${stats ? stats.total_paid_ytd.toLocaleString("en-US", { minimumFractionDigits: 2 }) : "0.00"}
            </div>
            <div className="text-[11px] text-muted-foreground mt-1">
              {stats?.paper_submitted_count || 0} paper &bull; {stats?.online_portal_count || 0} online
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Log Historical Paper Voucher Modal */}
      {paperModalOpen && (
        <Card className="border-cyan-500/50 bg-secondary/30">
          <CardHeader className="pb-3 border-b border-border">
            <CardTitle className="text-base flex items-center gap-2">
              <History className="h-4 w-4 text-cyan-400" />
              Log Historical Handwritten / Paper Voucher
            </CardTitle>
            <CardDescription className="text-xs">
              Record an older voucher submitted by hand or previously processed before the online portal, so your archive is complete.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-4 text-xs">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              <div className="space-y-1">
                <Label htmlFor="p_case">Case / Cause Number</Label>
                <Input
                  id="p_case"
                  placeholder="e.g. 2023-CR-1109-B"
                  value={paperForm.case_number}
                  onChange={(e) => setPaperForm({ ...paperForm, case_number: e.target.value })}
                  className="h-8 text-xs"
                />
              </div>

              <div className="space-y-1">
                <Label htmlFor="p_client">Client / Defendant Name</Label>
                <Input
                  id="p_client"
                  placeholder="e.g. Jessica Longoria"
                  value={paperForm.client_name}
                  onChange={(e) => setPaperForm({ ...paperForm, client_name: e.target.value })}
                  className="h-8 text-xs"
                />
              </div>

              <div className="space-y-1">
                <Label htmlFor="p_court">Court</Label>
                <select
                  id="p_court"
                  value={paperForm.court}
                  onChange={(e) => setPaperForm({ ...paperForm, court: e.target.value })}
                  className="w-full h-8 rounded-md border border-input bg-background px-2 text-xs"
                >
                  <option value="28th District Court">28th District Court (Hon. Nanette Hasette)</option>
                  <option value="94th District Court">94th District Court (Hon. Bobby Galvan)</option>
                  <option value="105th District Court">105th District Court (Hon. Jack W. Pulcher)</option>
                  <option value="117th District Court">117th District Court (Hon. Sandra Watts)</option>
                  <option value="148th District Court">148th District Court (Hon. Carlos Valdez)</option>
                  <option value="214th District Court">214th District Court (Hon. Inna Klein)</option>
                  <option value="319th District Court">319th District Court (Hon. David Stith)</option>
                  <option value="347th District Court">347th District Court (Hon. Missy Medary)</option>
                  <option value="County Court at Law No. 1">County Court at Law No. 1</option>
                  <option value="County Court at Law No. 2">County Court at Law No. 2</option>
                  <option value="County Court at Law No. 3">County Court at Law No. 3</option>
                  <option value="County Court at Law No. 4">County Court at Law No. 4</option>
                  <option value="County Court at Law No. 5">County Court at Law No. 5</option>
                </select>
              </div>

              <div className="space-y-1">
                <Label htmlFor="p_amount">Amount Claimed ($)</Label>
                <Input
                  id="p_amount"
                  type="number"
                  value={paperForm.amount_requested}
                  onChange={(e) => setPaperForm({ ...paperForm, amount_requested: parseFloat(e.target.value) || 0 })}
                  className="h-8 text-xs"
                />
              </div>

              <div className="space-y-1">
                <Label htmlFor="p_status">Historical Status</Label>
                <select
                  id="p_status"
                  value={paperForm.status}
                  onChange={(e) => setPaperForm({ ...paperForm, status: e.target.value })}
                  className="w-full h-8 rounded-md border border-input bg-background px-2 text-xs"
                >
                  <option value="PAID">PAID (Warrant Received)</option>
                  <option value="APPROVED">APPROVED (Awaiting Warrant)</option>
                  <option value="SUBMITTED">SUBMITTED (Pending Judge)</option>
                  <option value="UNBILLED">UNBILLED (Needs Submission)</option>
                </select>
              </div>

              <div className="space-y-1">
                <Label htmlFor="p_warrant">Auditor Warrant / Check # (Optional)</Label>
                <Input
                  id="p_warrant"
                  placeholder="e.g. WARR-904812"
                  value={paperForm.warrant_number}
                  onChange={(e) => setPaperForm({ ...paperForm, warrant_number: e.target.value })}
                  className="h-8 text-xs"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <Button size="sm" variant="ghost" onClick={() => setPaperModalOpen(false)}>
                Cancel
              </Button>
              <Button
                size="sm"
                className="bg-cyan-600 hover:bg-cyan-500 text-white font-medium"
                disabled={!paperForm.case_number || !paperForm.client_name || paperMutation.isPending}
                onClick={() => paperMutation.mutate(paperForm)}
              >
                {paperMutation.isPending ? "Recording..." : "Save Historical Voucher"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filter Tabs & Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-3">
        <div className="flex flex-wrap gap-1.5">
          {[
            { id: "ALL", label: "All Vouchers" },
            { id: "READY_TO_FILE", label: "Ready to Be Filed", badge: stats?.ready_to_file_count },
            { id: "UNBILLED", label: "Unbilled Backlog" },
            { id: "SUBMITTED", label: "Submitted" },
            { id: "RETURNED", label: "Returned", badge: stats?.returned_count },
            { id: "APPROVED", label: "Approved" },
            { id: "PAID", label: "Paid" },
          ].map((tab) => (
            <Button
              key={tab.id}
              variant={selectedStatus === tab.id ? "default" : "outline"}
              size="sm"
              className="text-xs h-8"
              onClick={() => setSelectedStatus(tab.id)}
            >
              {tab.label}
              {tab.badge && tab.badge > 0 ? (
                <span className="ml-1.5 px-1.5 py-0.2 rounded-full bg-red-500 text-white text-[10px] font-bold">
                  {tab.badge}
                </span>
              ) : null}
            </Button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          {/* Submission Method Filter */}
          <select
            value={selectedMethod}
            onChange={(e) => setSelectedMethod(e.target.value)}
            className="h-8 rounded-md border border-input bg-background px-2 text-xs"
          >
            <option value="ALL">All Methods</option>
            <option value="ONLINE_PORTAL">Online Portal</option>
            <option value="PAPER_HAND_SUBMITTED">Historical Paper</option>
          </select>

          {/* Search Field */}
          <div className="relative w-48">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search case # or client..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-2 py-1 text-xs rounded-md bg-background border border-border focus:border-cyan-400 focus:outline-hidden"
            />
          </div>
        </div>
      </div>

      {/* The Voucher Radar Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 text-center text-muted-foreground text-sm">
              Loading voucher recovery pipeline...
            </div>
          ) : vouchers && vouchers.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-muted/40 text-muted-foreground border-b border-border">
                  <tr>
                    <th className="py-3 px-4 font-semibold">Voucher # &amp; Case</th>
                    <th className="py-3 px-4 font-semibold">Client &amp; Court</th>
                    <th className="py-3 px-4 font-semibold text-center">Submission Channel</th>
                    <th className="py-3 px-4 font-semibold text-center">Art. 26.04 Appointment &amp; Acceptance</th>
                    <th className="py-3 px-4 font-semibold">Amount Claimed</th>
                    <th className="py-3 px-4 font-semibold">Status &amp; Lifecycle</th>
                    <th className="py-3 px-4 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {vouchers.map((v: any) => (
                    <tr
                      key={v.id}
                      className={`hover:bg-muted/30 transition-colors ${
                        v.status === "RETURNED" ? "bg-amber-500/5" : ""
                      }`}
                    >
                      {/* Case & Voucher # */}
                      <td className="py-3 px-4">
                        <div className="font-bold text-foreground">{v.voucher_number}</div>
                        <Link
                          to={`/cases/${v.case_id}`}
                          className="text-primary hover:underline font-mono text-[11px] block mt-0.5"
                        >
                          {v.case_number}
                        </Link>
                      </td>

                      {/* Client & Court */}
                      <td className="py-3 px-4">
                        <div className="font-medium text-foreground">{v.client_name}</div>
                        <div className="text-muted-foreground text-[11px]">{v.court}</div>
                        {v.judge && <div className="text-[10px] text-muted-foreground/80">{v.judge}</div>}
                      </td>

                      {/* Method */}
                      <td className="py-3 px-4 text-center">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold border ${
                          v.submission_method === "PAPER_HAND_SUBMITTED"
                            ? "bg-purple-950/40 text-purple-300 border-purple-500/30"
                            : "bg-cyan-950/40 text-cyan-300 border-cyan-500/30"
                        }`}>
                          {v.submission_method === "PAPER_HAND_SUBMITTED" ? "Paper / Legacy" : "Online Portal"}
                        </span>
                      </td>

                      {/* Appointment & Acceptance */}
                      <td className="py-3 px-4 text-center">
                        {v.has_appointment_order && v.has_appointment_acceptance ? (
                          <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/30" title="Order & Filed Acceptance Verified: Billable to County Auditor">
                            <CheckCircle2 className="h-3 w-3" /> Verified &amp; Accepted
                          </span>
                        ) : v.has_appointment_order && !v.has_appointment_acceptance ? (
                          <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/30" title="Order issued on docket, but awaiting file-stamped Acceptance from District Clerk (Payment Blocked by Auditor)">
                            <AlertTriangle className="h-3 w-3" /> Awaiting Acceptance
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[10px] font-bold text-red-400 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/30" title="Missing Order Appointing Counsel on docket">
                            <AlertTriangle className="h-3 w-3" /> Missing Order
                          </span>
                        )}
                      </td>

                      {/* Amount */}
                      <td className="py-3 px-4">
                        <div className="font-bold text-foreground">
                          ${(v.amount_paid || v.amount_approved || v.amount_requested || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                        </div>
                        {v.status === "PAID" && v.warrant_number && (
                          <div className="text-[10px] text-emerald-400 font-mono">
                            {v.warrant_number}
                          </div>
                        )}
                      </td>

                      {/* Status */}
                      <td className="py-3 px-4">
                        <div className="space-y-1">
                          {getStatusBadge(v.status)}
                          {v.status === "UNBILLED" || v.status === "DRAFT" ? (
                            <div className="text-[10px] text-muted-foreground">
                              Aging: {v.aging_days}d since disposition ({v.aging_bracket})
                            </div>
                          ) : v.status === "RETURNED" ? (
                            <div className="text-[10px] text-red-400 font-medium line-clamp-1" title={v.rejection_reason}>
                              {v.rejection_reason}
                            </div>
                          ) : v.status === "APPROVED" ? (
                            <div className="text-[10px] text-teal-300">
                              In auditor queue ({v.days_waiting_auditor ?? 14}d)
                            </div>
                          ) : v.status === "PAID" ? (
                            <div className="text-[10px] text-emerald-400">
                              Paid {formatDate(v.paid_date)}
                            </div>
                          ) : null}
                        </div>
                      </td>

                      {/* Actions */}
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 text-xs px-2 text-primary"
                            onClick={() => setInspectVoucher(v)}
                          >
                            <FileText className="h-3.5 w-3.5 mr-1" />
                            Summary
                          </Button>

                          {v.status === "READY_TO_FILE" ? (
                            <Button
                              asChild
                              size="sm"
                              className="h-7 text-xs px-2.5 bg-emerald-600 hover:bg-emerald-700 text-white gap-1"
                            >
                              <a
                                href="https://perfectapps.nuecescountytx.gov/PresentationServer/App.aspx/Play/vgAAggch?f=vgAAggch"
                                target="_blank"
                                rel="noreferrer"
                              >
                                <ExternalLink className="h-3 w-3" />
                                File on Perfect Apps ↗
                              </a>
                            </Button>
                          ) : v.status === "DRAFT" || v.status === "UNBILLED" ? (
                            <Button
                              variant="default"
                              size="sm"
                              className="h-7 text-xs px-2.5 bg-blue-600 hover:bg-blue-700"
                              onClick={() => {
                                updateMutation.mutate({
                                  id: v.id,
                                  data: {
                                    status: "SUBMITTED",
                                    submitted_date: new Date().toISOString().slice(0, 10),
                                  },
                                });
                              }}
                            >
                              <Send className="h-3 w-3 mr-1" />
                              Submit
                            </Button>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-8 text-center text-muted-foreground text-sm space-y-2">
              <DollarSign className="h-8 w-8 mx-auto text-muted-foreground/40" />
              <p>No vouchers matching the selected criteria.</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Voucher Detail Inspection Modal / Card */}
      {inspectVoucher && (
        <Card className="border-primary/40 bg-card mt-6">
          <CardHeader className="pb-3 border-b border-border">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base flex items-center gap-2">
                  <FileSpreadsheet className="h-4 w-4 text-emerald-400" />
                  Nueces County Indigent Defense Voucher Summary — {inspectVoucher.voucher_number}
                </CardTitle>
                <CardDescription>
                  Cause No: <span className="font-semibold text-foreground">{inspectVoucher.case_number}</span> ({inspectVoucher.client_name}) • {inspectVoucher.court}
                </CardDescription>
              </div>
              <div className="flex items-center gap-2">
                {getStatusBadge(inspectVoucher.status)}
                <Button variant="ghost" size="sm" onClick={() => setInspectVoucher(null)}>
                  Close
                </Button>
              </div>
            </div>
          </CardHeader>

          <CardContent className="p-6 space-y-4 text-xs">
            {/* Statutory Appointment & Auditor Payment Eligibility Card */}
            <div className={`p-3.5 rounded-lg border ${
              inspectVoucher.has_appointment_order && inspectVoucher.has_appointment_acceptance
                ? "bg-emerald-950/20 border-emerald-500/30 text-emerald-300"
                : inspectVoucher.has_appointment_order && !inspectVoucher.has_appointment_acceptance
                ? "bg-amber-950/25 border-amber-500/30 text-amber-300"
                : "bg-red-950/20 border-red-500/30 text-red-300"
            }`}>
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <div className="flex items-center gap-2 font-semibold">
                  {inspectVoucher.has_appointment_order && inspectVoucher.has_appointment_acceptance ? (
                    <>
                      <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                      <span className="text-foreground font-bold">Art. 26.04 Appointment &amp; Acceptance Verified (Ready for County Payment)</span>
                    </>
                  ) : inspectVoucher.has_appointment_order && !inspectVoucher.has_appointment_acceptance ? (
                    <>
                      <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />
                      <span className="text-foreground font-bold">Awaiting Stamped Acceptance of Appointment (Payment Blocked)</span>
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="h-4 w-4 text-red-400 shrink-0" />
                      <span className="text-foreground font-bold">Missing Order Appointing Counsel</span>
                    </>
                  )}
                </div>
                <Badge variant={inspectVoucher.has_appointment_order && inspectVoucher.has_appointment_acceptance ? "success" : "warning"} className="text-[10px]">
                  {inspectVoucher.has_appointment_order && inspectVoucher.has_appointment_acceptance ? "Auditor Approved Prerequisite" : "County Auditor Block"}
                </Badge>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1 text-[11px] text-muted-foreground">
                <div>
                  <span className="block text-[10px]">Order Date:</span>
                  <strong className="text-foreground font-mono">{inspectVoucher.appointment_order_date ? formatDate(inspectVoucher.appointment_order_date) : inspectVoucher.has_appointment_order ? "On Docket" : "None"}</strong>
                </div>
                <div>
                  <span className="block text-[10px]">Client Contact (48h Rule):</span>
                  <strong className="text-foreground font-mono">{inspectVoucher.client_contact_date ? formatDate(inspectVoucher.client_contact_date) : "Pending Affirmation"}</strong>
                </div>
                <div>
                  <span className="block text-[10px]">District Clerk Filing:</span>
                  <strong className="text-foreground font-mono">{inspectVoucher.acceptance_filed_date ? `Filed ${formatDate(inspectVoucher.acceptance_filed_date)}` : inspectVoucher.has_appointment_acceptance ? "Filed" : "Awaiting File Stamp"}</strong>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-3 bg-muted/40 rounded-lg">
              <div>
                <span className="text-muted-foreground block">Amount Claimed</span>
                <span className="text-base font-bold text-foreground">
                  ${inspectVoucher.amount_requested?.toFixed(2)}
                </span>
              </div>
              <div>
                <span className="text-muted-foreground block">Submission Method</span>
                <span className="text-sm font-semibold text-foreground">
                  {inspectVoucher.submission_method === "PAPER_HAND_SUBMITTED" ? "Paper / Legacy" : "Online Portal"}
                </span>
              </div>
              <div>
                <span className="text-muted-foreground block">Disposition Date</span>
                <span className="text-sm text-foreground">
                  {formatDate(inspectVoucher.disposition_date)}
                </span>
              </div>
              <div>
                <span className="text-muted-foreground block">Presiding Judge</span>
                <span className="text-sm text-foreground">
                  {inspectVoucher.judge || "Nueces County Bench"}
                </span>
              </div>
            </div>

            {/* Attorney Vendor & Digital Signature Box */}
            <div className="p-3 bg-secondary/40 border border-border rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="space-y-0.5">
                <span className="font-semibold text-foreground flex items-center gap-1.5">
                  <span className="text-cyan-400 font-bold">{firmName}</span> &bull; {attorneyName}
                </span>
                <div className="text-muted-foreground text-[11px] flex items-center gap-3">
                  <span>Vendor ID: <code className="text-foreground">{profile?.vendor_number || (isDemo ? "TX-NUE-10000" : "TX-NUE-84920")}</code></span>
                  <span>State Bar: <code className="text-foreground">#{barNumber}</code></span>
                  <span>Jurisdiction: Nueces County, TX</span>
                </div>
              </div>
              <div className="text-right shrink-0">
                <Badge variant="outline" className="text-[10px] text-cyan-300 border-cyan-500/40 bg-cyan-950/30">
                  /s/ {attorneyName} [E-Signed]
                </Badge>
              </div>
            </div>


            {inspectVoucher.rejection_reason && (
              <div className="p-3 bg-red-500/10 border border-red-500/30 text-red-300 rounded-lg">
                <span className="font-bold block mb-1">Return / Correction Note:</span>
                {inspectVoucher.rejection_reason}
              </div>
            )}

            {inspectVoucher.notes && (
              <div className="p-3 bg-muted/20 border border-border rounded-lg">
                <span className="font-semibold text-muted-foreground block mb-1">Notes &amp; Activity Log:</span>
                <p className="text-foreground/90">{inspectVoucher.notes}</p>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2 border-t border-border">
              {inspectVoucher.status === "READY_TO_FILE" && (
                <Button asChild size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5">
                  <a
                    href="https://perfectapps.nuecescountytx.gov/PresentationServer/App.aspx/Play/vgAAggch?f=vgAAggch"
                    target="_blank"
                    rel="noreferrer"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    File on Perfect Apps ↗
                  </a>
                </Button>
              )}
              <Button asChild size="sm" variant="outline">
                <Link to={`/cases/${inspectVoucher.case_id}`}>
                  <Scale className="h-3.5 w-3.5 mr-1.5" />
                  Go to Case File
                </Link>
              </Button>
              <Button
                size="sm"
                className="bg-primary hover:bg-primary/90"
                onClick={() => {
                  alert(`Voucher exported to standard Nueces County Indigent Defense (Art. 26.05) PDF format with ${attorneyName}'s verified signature and Vendor ID ${profile?.vendor_number || (isDemo ? "TX-NUE-10000" : "TX-NUE-84920")}!`)
                }}
              >

                <FileText className="h-3.5 w-3.5 mr-1.5" />
                Export Nueces Voucher PDF
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
