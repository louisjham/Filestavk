import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Scale,
  DollarSign,
  AlertTriangle,
  RefreshCw,
  Globe,
  ArrowRight,
  TrendingUp,
  User,
  Clock,
  ShieldAlert,
  FileText,
  Lock,
  Calendar,
  ExternalLink,
  Sparkles,
} from "lucide-react"
import { OctopusIcon } from "@/components/icons/OctopusIcon"
import { useAuth } from "@/lib/auth"
import { KimbelDelegationCard } from "@/components/delegation/KimbelDelegationCard"
import { KimbelDailyGreeting } from "@/components/KimbelDailyGreeting"
import { GeminiBriefingIngestModal } from "@/components/briefing/GeminiBriefingIngestModal"
import { GeminiBriefingVerificationBoard } from "@/components/briefing/GeminiBriefingVerificationBoard"
import { formatDate } from "@/lib/utils"
import { usePracticeProfile } from "@/hooks/usePracticeProfile"

export function Dashboard() {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const { isDemo, attorneyName, barNumber } = usePracticeProfile()

  const isAssistant = user?.role === "assistant"
  const [isIngestModalOpen, setIsIngestModalOpen] = useState(false)

  // Unified Morning Briefing & Alerts
  const { data: briefing, isLoading: briefingLoading } = useQuery({
    queryKey: ["dashboard-alerts"],
    queryFn: () => api.settings.getDashboardAlerts(),
    refetchInterval: 15000,
  })

  // Financial Stats
  const { data: voucherStats } = useQuery({
    queryKey: ["voucher-stats"],
    queryFn: () => api.vouchers.stats(),
  })

  const syncMutation = useMutation({
    mutationFn: () => api.vouchers.simulateGmailSync(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard-alerts"] })
      queryClient.invalidateQueries({ queryKey: ["vouchers"] })
      queryClient.invalidateQueries({ queryKey: ["voucher-stats"] })
    },
  })

  const alerts = briefing?.alerts || []
  const inCustodyRoster = briefing?.in_custody_roster || []

  return (
    <div className="space-y-6 max-w-7xl">
      {/* 1. Kimbel Brandon Daily Cephalopod Greeting & Command Header */}
      <KimbelDailyGreeting />

      {/* Quick Action Toolbar */}
      <div className="flex items-center justify-between gap-3 px-1 -mt-2">
        <p className="text-xs text-muted-foreground font-medium">
          {briefing?.date_today || "Nueces County Defense Command"} &bull; {isAssistant ? "Assistant Workspace" : `${attorneyName}, State Bar #${barNumber}`}
        </p>


        <div className="flex items-center gap-2.5">
          <Button
            size="sm"
            onClick={() => setIsIngestModalOpen(true)}
            className="text-xs gap-1.5 bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white font-medium shadow-xs"
          >
            <Sparkles className="h-3.5 w-3.5" />
            Paste 10-Day Gem Brief
          </Button>

          {!isAssistant && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending}
              className="text-xs gap-1.5 border-cyan-500/30 text-cyan-300 hover:bg-cyan-950/40"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${syncMutation.isPending ? "animate-spin text-cyan-400" : ""}`} />
              Sync Gmail
            </Button>
          )}
          <Button asChild size="sm" className="text-xs gap-1.5 bg-cyan-600 hover:bg-cyan-500 text-white font-medium">
            <Link to="/ingestion/portal">
              <Globe className="h-3.5 w-3.5" />
              Nueces Portal Assist
            </Link>
          </Button>
        </div>
      </div>

      {/* 2. Gemini 10-Day Deep-Dive Verification Board */}
      <GeminiBriefingVerificationBoard onOpenIngestModal={() => setIsIngestModalOpen(true)} />

      {/* Modal for pasting Gemini Brief */}
      <GeminiBriefingIngestModal open={isIngestModalOpen} onOpenChange={setIsIngestModalOpen} />

      {/* 2. Kimbel's Delegated Tasks (Always on top for assistant, visible for attorney) */}
      <KimbelDelegationCard />

      {/* 2. Unified Priority Action Alerts (Vouchers OR Case Milestones) */}
      {alerts.length > 0 && (
        <div className="space-y-2.5">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
              Immediate Attention Required ({alerts.length})
            </h3>
          </div>

          <div className="space-y-2">
            {alerts.map((alert: any) => (
              <div
                key={alert.id}
                className={`p-4 rounded-lg border flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-colors ${
                  alert.severity === "CRITICAL"
                    ? "bg-red-500/10 border-red-500/40 text-foreground"
                    : alert.severity === "HIGH"
                    ? "bg-amber-500/10 border-amber-500/40 text-foreground"
                    : "bg-blue-500/10 border-blue-500/30 text-foreground"
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 shrink-0">
                    {alert.severity === "CRITICAL" ? (
                      <span className="text-lg">🚨</span>
                    ) : alert.severity === "HIGH" ? (
                      <span className="text-lg">⚠️</span>
                    ) : (
                      <span className="text-lg">📋</span>
                    )}
                  </div>
                  <div className="space-y-0.5 text-xs">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-foreground">
                        {alert.title}
                      </span>
                      <Badge
                        variant={
                          alert.severity === "CRITICAL"
                            ? "destructive"
                            : alert.severity === "HIGH"
                            ? "warning"
                            : "info"
                        }
                        className="text-[10px] px-1.5 py-0"
                      >
                        {alert.severity}
                      </Badge>
                    </div>
                    <p className="text-muted-foreground leading-relaxed">
                      {alert.description}
                    </p>
                  </div>
                </div>

                <Button
                  asChild
                  size="sm"
                  variant={alert.severity === "CRITICAL" ? "destructive" : "default"}
                  className="shrink-0 text-xs h-8 font-medium gap-1"
                >
                  <Link to={alert.link}>
                    {alert.action_label} <ArrowRight className="h-3 w-3" />
                  </Link>
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. Awaiting Acceptance of Appointment — Art. 26.04 CCP */}
      {(() => {
        const awaitingList = briefing?.awaiting_acceptance || []
        if (awaitingList.length === 0) return null
        return (
          <Card className="border-amber-500/30 bg-card/60">
            <CardHeader className="pb-3 border-b border-border">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <CardTitle className="text-base flex items-center gap-2 text-foreground">
                    <AlertTriangle className="h-4 w-4 text-amber-400" />
                    Awaiting Acceptance of Appointment ({awaitingList.length})
                  </CardTitle>
                  <CardDescription className="text-xs">
                    CJA cases with an Order of Appointment but no file-stamped Acceptance. Auditor blocks payment until Acceptance is filed with District Clerk Lorentzen.
                  </CardDescription>
                </div>
                <Button asChild size="sm" variant="ghost" className="text-xs h-7 text-amber-400 hover:text-amber-300">
                  <Link to="/cases">View All Cases</Link>
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-border text-left text-muted-foreground bg-muted/20">
                      <th className="py-2.5 px-4 font-medium">Client &amp; Case</th>
                      <th className="py-2.5 px-4 font-medium">Charge &amp; Court</th>
                      <th className="py-2.5 px-4 font-medium">Order Date</th>
                      <th className="py-2.5 px-4 font-medium text-center">Days Pending</th>
                      <th className="py-2.5 px-4 font-medium text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60">
                    {awaitingList.map((item: any) => (
                      <tr key={item.case_id} className="hover:bg-muted/10 transition-colors">
                        <td className="py-3 px-4">
                          <div className="font-bold text-foreground">{item.client_name}</div>
                          <Link to={`/cases/${item.case_id}`} className="text-primary font-mono text-[11px] hover:underline">
                            #{item.case_number}
                          </Link>
                        </td>
                        <td className="py-3 px-4">
                          <div className="font-medium text-foreground max-w-[220px] truncate" title={item.charge}>{item.charge}</div>
                          <div className="text-muted-foreground text-[11px]">{item.court}</div>
                        </td>
                        <td className="py-3 px-4 text-muted-foreground font-mono text-[11px]">
                          {item.appointment_order_date ? formatDate(item.appointment_order_date) : "—"}
                        </td>
                        <td className="py-3 px-4 text-center">
                          {item.days_pending != null ? (
                            <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold ${
                              item.days_pending >= 14
                                ? "bg-red-500/20 text-red-300 border border-red-500/40"
                                : item.days_pending >= 7
                                ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                                : "bg-blue-500/20 text-blue-300 border border-blue-500/40"
                            }`}>
                              {item.days_pending}d
                            </span>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <Button asChild size="sm" variant="outline" className="text-xs h-7 gap-1 border-amber-500/40 text-amber-300 hover:bg-amber-500/10">
                            <Link to={`/documents?case_id=${item.case_id}`}>
                              <FileText className="h-3 w-3" />
                              Upload Acceptance
                            </Link>
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        )
      })()}

      {/* 4. In-Custody / Nueces County Jail Priority Roster */}
      <Card className="border-cyan-500/30 bg-card/60">
        <CardHeader className="pb-3 border-b border-border">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <CardTitle className="text-base flex items-center gap-2 text-foreground">
                <Lock className="h-4 w-4 text-cyan-400" />
                In-Custody Clients &bull; Jail Priority Roster ({inCustodyRoster.length})
              </CardTitle>
              <CardDescription className="text-xs">
                Clients currently detained in Nueces County Jail. Prioritize bond reduction hearings (Art. 17.151 CCP).
              </CardDescription>
            </div>
            <Button asChild size="sm" variant="ghost" className="text-xs h-7 text-cyan-400 hover:text-cyan-300">
              <Link to="/cases">View All Cases</Link>
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {inCustodyRoster.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border text-left text-muted-foreground bg-muted/20">
                    <th className="py-2.5 px-4 font-medium">Case &amp; Client</th>
                    <th className="py-2.5 px-4 font-medium">Charge &amp; Court</th>
                    <th className="py-2.5 px-4 font-medium text-center">Days in Jail</th>
                    <th className="py-2.5 px-4 font-medium">Bond Required</th>
                    <th className="py-2.5 px-4 font-medium">Facility</th>
                    <th className="py-2.5 px-4 font-medium text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {inCustodyRoster.map((item: any) => (
                    <tr key={item.case_id} className="hover:bg-muted/10 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-bold text-foreground text-xs">
                          <Link to={`/clients/${item.client_id}`} className="hover:underline flex items-center gap-1.5">
                            <User className="h-3.5 w-3.5 text-primary" />
                            {item.client_name || `Client #${item.client_id}`}
                          </Link>
                        </div>
                        <div className="text-primary font-mono text-[11px]">
                          <Link to={`/cases/${item.case_id}`} className="hover:underline">
                            #{item.case_number}
                          </Link>
                        </div>
                      </td>

                      <td className="py-3 px-4">
                        <div className="font-medium text-foreground max-w-[240px] truncate" title={item.charge}>
                          {item.charge}
                        </div>
                        <div className="text-muted-foreground text-[11px]">
                          {item.court} &bull; <span className="capitalize">{item.stage}</span>
                        </div>
                      </td>

                      <td className="py-3 px-4 text-center">
                        <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold ${
                          item.days_in_jail >= 60
                            ? "bg-red-500/20 text-red-300 border border-red-500/40"
                            : item.days_in_jail >= 30
                            ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                            : "bg-blue-500/20 text-blue-300 border border-blue-500/40"
                        }`}>
                          {item.days_in_jail} Days
                        </span>
                      </td>

                      <td className="py-3 px-4">
                        <div className="font-semibold text-foreground">
                          {item.bond_amount ? `$${item.bond_amount.toLocaleString()}` : "No Bond"}
                        </div>
                        <div className="text-[10px] text-muted-foreground">
                          {item.bond_type}
                        </div>
                      </td>

                      <td className="py-3 px-4 text-muted-foreground text-[11px]">
                        {item.facility}
                      </td>

                      <td className="py-3 px-4 text-right">
                        <Button asChild size="sm" variant="outline" className="text-xs h-7 gap-1">
                          <Link to={`/cases/${item.case_id}`}>
                            Review Case
                          </Link>
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-8 text-center text-muted-foreground text-xs">
              No clients currently flagged as in-custody.
            </div>
          )}
        </CardContent>
      </Card>

      {/* 4. Financial Health & Voucher KPI Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Unbilled Revenue Card */}
        <Card className="border-l-4 border-l-amber-500">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground uppercase">Unbilled Claimable Cash</span>
              <DollarSign className="h-4 w-4 text-amber-400" />
            </div>
            <div className="text-2xl font-bold text-foreground mt-1">
              ${voucherStats ? voucherStats.total_unbilled.toLocaleString("en-US", { minimumFractionDigits: 2 }) : "0.00"}
            </div>
            <div className="text-[11px] text-muted-foreground mt-1">
              <Link to="/vouchers" className="text-primary hover:underline flex items-center gap-1 font-medium">
                Voucher Radar <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
          </CardContent>
        </Card>

        {/* Pending Court Review Card */}
        <Card className="border-l-4 border-l-purple-500">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground uppercase">Pending Court Approval</span>
              <Scale className="h-4 w-4 text-purple-400" />
            </div>
            <div className="text-2xl font-bold text-purple-300 mt-1">
              ${voucherStats ? voucherStats.total_pending_court.toLocaleString("en-US", { minimumFractionDigits: 2 }) : "0.00"}
            </div>
            <div className="text-[11px] text-muted-foreground mt-1">
              Awaiting District / County Judge signature
            </div>
          </CardContent>
        </Card>

        {/* Auditor Queue */}
        <Card className="border-l-4 border-l-blue-500">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground uppercase">Auditor Queue</span>
              <Clock className="h-4 w-4 text-blue-400" />
            </div>
            <div className="text-2xl font-bold text-blue-400 mt-1">
              ${voucherStats ? voucherStats.total_approved_auditor.toLocaleString("en-US", { minimumFractionDigits: 2 }) : "0.00"}
            </div>
            <div className="text-[11px] text-muted-foreground mt-1">
              Approved &bull; 14-45d disbursement window
            </div>
          </CardContent>
        </Card>

        {/* Paid Year-to-Date */}
        <Card className="border-l-4 border-l-emerald-500">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground uppercase">Paid Year-to-Date</span>
              <TrendingUp className="h-4 w-4 text-emerald-400" />
            </div>
            <div className="text-2xl font-bold text-emerald-400 mt-1">
              ${voucherStats ? voucherStats.total_paid_ytd.toLocaleString("en-US", { minimumFractionDigits: 2 }) : "0.00"}
            </div>
            <div className="text-[11px] text-muted-foreground mt-1">
              Nueces County direct deposits received
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
