import { useState, useRef } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  FileSpreadsheet,
  Upload,
  Download,
  Copy,
  Check,
  ExternalLink,
  Plus,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Sparkles,
  Search,
  Filter,
  ArrowRight,
  RefreshCw,
  FileText,
} from "lucide-react"

export function SpreadsheetQueue() {
  const queryClient = useQueryClient()
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [pasteModalOpen, setPasteModalOpen] = useState(false)
  const [rawPastedText, setRawPastedText] = useState("")
  const [searchTerm, setSearchTerm] = useState("")
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { data, isLoading } = useQuery({
    queryKey: ["spreadsheet-queue"],
    queryFn: () => api.spreadsheet.getQueue(),
  })

  const pasteMutation = useMutation({
    mutationFn: (text: string) => api.spreadsheet.pasteRows(text),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["spreadsheet-queue"] })
      setPasteModalOpen(false)
      setRawPastedText("")
    },
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => api.spreadsheet.upload(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["spreadsheet-queue"] })
    },
  })

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      uploadMutation.mutate(e.target.files[0])
    }
  }

  const items = data?.queue || []
  const filteredItems = items.filter((item: any) => {
    if (!searchTerm) return true
    const q = searchTerm.toLowerCase()
    return (
      item.case_number.toLowerCase().includes(q) ||
      item.client_name.toLowerCase().includes(q) ||
      item.court.toLowerCase().includes(q) ||
      item.notes.toLowerCase().includes(q)
    )
  })

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-cyan-950/40 to-slate-900 border border-cyan-500/20 p-6 rounded-xl shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-cyan-950/80 border border-cyan-500/40 flex items-center justify-center shrink-0">
                <FileSpreadsheet className="h-5 w-5 text-cyan-400" />
              </div>
              <div>
                <h1 className="text-xl font-bold tracking-tight text-foreground">
                  Master Spreadsheet &amp; Voucher Queue
                </h1>
                <p className="text-xs text-cyan-300/80 font-medium">
                  Source of Truth &bull; Fast 1-Click Clipboard &bull; Tyler Odyssey Portal Synchronization
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept=".csv,.txt"
              className="hidden"
            />
            <Button
              size="sm"
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadMutation.isPending}
              className="text-xs gap-1.5 border-cyan-500/30 text-cyan-300 hover:bg-cyan-950/40"
            >
              <Upload className="h-3.5 w-3.5" />
              Upload CSV
            </Button>

            <Button
              size="sm"
              variant="outline"
              onClick={() => setPasteModalOpen(true)}
              className="text-xs gap-1.5 border-cyan-500/30 text-cyan-300 hover:bg-cyan-950/40"
            >
              <Plus className="h-3.5 w-3.5" />
              Paste Excel Rows
            </Button>

            <Button
              asChild
              size="sm"
              className="text-xs gap-1.5 bg-cyan-600 hover:bg-cyan-500 text-white font-medium"
            >
              <a
                href="https://portal-txnueces.tylertech.cloud/Portal/Home/Dashboard/29"
                target="_blank"
                rel="noreferrer"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                Launch Odyssey Portal
              </a>
            </Button>

            <Button asChild size="sm" variant="secondary" className="text-xs gap-1.5">
              <a href={api.spreadsheet.getExportUrl()} download="nueces_voucher_master_tracker.csv">
                <Download className="h-3.5 w-3.5" />
                Export Reconciled CSV
              </a>
            </Button>
          </div>
        </div>
      </div>

      {/* KPI Stats Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-l-4 border-l-cyan-500">
          <CardContent className="p-4">
            <span className="text-xs font-semibold text-muted-foreground uppercase">Master Queue Size</span>
            <div className="text-2xl font-bold text-foreground mt-1">{data?.total_items || 0} Cases</div>
            <div className="text-[11px] text-muted-foreground mt-1">Cross-referenced with local SQLite</div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-emerald-500">
          <CardContent className="p-4">
            <span className="text-xs font-semibold text-muted-foreground uppercase">Disposed (Claimable Cash)</span>
            <div className="text-2xl font-bold text-emerald-400 mt-1">{data?.disposed_count || 0} Cases</div>
            <div className="text-[11px] text-muted-foreground mt-1">
              {data?.ready_to_bill_count || 0} ready to submit (no expiration deadline)
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-amber-500">
          <CardContent className="p-4">
            <span className="text-xs font-semibold text-muted-foreground uppercase">Order Appointing Counsel Alert</span>
            <div className="text-2xl font-bold text-amber-400 mt-1">{data?.missing_appointment_count || 0} Cases</div>
            <div className="text-[11px] text-muted-foreground mt-1">Missing order delays voucher approval</div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-purple-500">
          <CardContent className="p-4">
            <span className="text-xs font-semibold text-muted-foreground uppercase">Fast Ingestion Tool</span>
            <div className="text-sm font-bold text-foreground mt-1">Select-All &amp; Paste</div>
            <div className="text-[11px] text-muted-foreground mt-1">
              <Link to="/ingestion/portal" className="text-primary hover:underline flex items-center gap-1 font-medium">
                Open Odyssey Raw Parser <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Paste Rows Modal / Drawer */}
      {pasteModalOpen && (
        <Card className="border-cyan-500/50 bg-secondary/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Plus className="h-4 w-4 text-cyan-400" />
              Paste Rows from Excel / Google Sheets
            </CardTitle>
            <CardDescription className="text-xs">
              Copy rows from your spreadsheet (Columns: Case Number, Client Name, Court, Notes) and paste below. Tab or comma separated.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <textarea
              className="w-full h-32 p-3 font-mono text-xs rounded-md bg-background border border-border focus:border-cyan-400 focus:outline-hidden"
              placeholder="2024-CR-1042-D	Marcus Hernandez	105th District Court	Disposed dismissal&#10;2024-CR-0891-A	Elena Rodriguez	28th District Court	Ready for voucher"
              value={rawPastedText}
              onChange={(e) => setRawPastedText(e.target.value)}
            />
            <div className="flex items-center justify-end gap-2">
              <Button size="sm" variant="ghost" onClick={() => setPasteModalOpen(false)}>
                Cancel
              </Button>
              <Button
                size="sm"
                className="bg-cyan-600 hover:bg-cyan-500 text-white font-medium"
                disabled={!rawPastedText.trim() || pasteMutation.isPending}
                onClick={() => pasteMutation.mutate(rawPastedText)}
              >
                {pasteMutation.isPending ? "Queuing..." : "Import Rows to Queue"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Live Table with 1-Click Clipboard */}
      <Card className="border-cyan-500/30">
        <CardHeader className="pb-3 border-b border-border">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="space-y-0.5">
              <CardTitle className="text-base flex items-center gap-2">
                <FileSpreadsheet className="h-4 w-4 text-cyan-400" />
                Voucher Production Workflow
              </CardTitle>
              <CardDescription className="text-xs">
                Copy the case number, solve the captcha in Odyssey, and paste the page into Raw Parser.
              </CardDescription>
            </div>
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search case #, client, court..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 text-xs rounded-md bg-background border border-border focus:border-cyan-400 focus:outline-hidden"
              />
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 text-center text-xs text-muted-foreground">Loading spreadsheet queue...</div>
          ) : filteredItems.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border text-left text-muted-foreground bg-muted/20">
                    <th className="py-2.5 px-4 font-medium">1-Click Copy</th>
                    <th className="py-2.5 px-4 font-medium">Client &amp; Court</th>
                    <th className="py-2.5 px-4 font-medium text-center">Appointed Order</th>
                    <th className="py-2.5 px-4 font-medium text-center">Disposition &amp; Voucher</th>
                    <th className="py-2.5 px-4 font-medium">Notes</th>
                    <th className="py-2.5 px-4 font-medium text-right">Quick Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {filteredItems.map((item: any) => {
                    const isCopiedNum = copiedId === `case-${item.id}`
                    const isCopiedName = copiedId === `name-${item.id}`

                    return (
                      <tr key={item.id} className="hover:bg-muted/10 transition-colors">
                        {/* 1-Click Copy Buttons */}
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleCopy(item.case_number, `case-${item.id}`)}
                              title="Click to copy case number to clipboard"
                              className={`flex items-center gap-1.5 px-2.5 py-1 rounded font-mono font-bold text-xs transition-colors border ${
                                isCopiedNum
                                  ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/50"
                                  : "bg-secondary text-primary hover:bg-cyan-950/40 border-cyan-500/30"
                              }`}
                            >
                              {isCopiedNum ? (
                                <>
                                  <Check className="h-3 w-3 text-emerald-400" />
                                  <span>COPIED!</span>
                                </>
                              ) : (
                                <>
                                  <Copy className="h-3 w-3 text-cyan-400" />
                                  <span>{item.case_number}</span>
                                </>
                              )}
                            </button>

                            <button
                              onClick={() => handleCopy(item.client_name, `name-${item.id}`)}
                              title="Click to copy client name to clipboard"
                              className={`p-1 rounded text-muted-foreground hover:text-foreground hover:bg-secondary border border-transparent hover:border-border transition-colors ${
                                isCopiedName ? "text-emerald-400 bg-emerald-500/10" : ""
                              }`}
                            >
                              {isCopiedName ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                            </button>
                          </div>
                        </td>

                        {/* Client & Court */}
                        <td className="py-3 px-4">
                          <div className="font-semibold text-foreground">{item.client_name}</div>
                          <div className="text-muted-foreground text-[11px]">
                            {item.court} {item.judge !== "—" ? `&bull; ${item.judge}` : ""}
                          </div>
                        </td>

                        {/* Appointment Order Verification */}
                        <td className="py-3 px-4 text-center">
                          {item.has_appointment_order ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                              <CheckCircle2 className="h-3 w-3 text-emerald-400" /> Order on Docket
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-300 border border-amber-500/40" title="Missing Order Appointing Counsel on docket. Contact Court Coordinator.">
                              <AlertTriangle className="h-3 w-3 text-amber-400" /> Missing Order
                            </span>
                          )}
                        </td>

                        {/* Disposition & Voucher Status */}
                        <td className="py-3 px-4 text-center">
                          <div className="flex flex-col items-center gap-1">
                            <Badge
                              variant={item.is_disposed ? "default" : "secondary"}
                              className="text-[10px] px-1.5 py-0"
                            >
                              {item.disposition_type || "ACTIVE"}
                            </Badge>

                            <span className={`text-[10px] font-semibold ${
                              item.voucher_status === "PAID"
                                ? "text-emerald-400"
                                : item.voucher_status === "APPROVED"
                                ? "text-blue-400"
                                : item.voucher_status === "SUBMITTED"
                                ? "text-purple-400"
                                : item.voucher_status === "RETURNED"
                                ? "text-red-400"
                                : "text-amber-400"
                            }`}>
                              Voucher: {item.voucher_status}
                            </span>
                          </div>
                        </td>

                        {/* Notes */}
                        <td className="py-3 px-4 max-w-[260px]">
                          <p className="text-muted-foreground text-[11px] truncate" title={item.notes}>
                            {item.notes || "—"}
                          </p>
                        </td>

                        {/* Action */}
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <Button asChild size="sm" variant="outline" className="text-xs h-7 gap-1">
                              <Link to="/ingestion/portal">
                                <Sparkles className="h-3 w-3 text-cyan-400" /> Parse
                              </Link>
                            </Button>
                            {item.case_id && (
                              <Button asChild size="sm" variant="ghost" className="text-xs h-7">
                                <Link to={`/cases/${item.case_id}`}>View</Link>
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-8 text-center text-muted-foreground text-xs">
              No cases matching filter in spreadsheet queue.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
