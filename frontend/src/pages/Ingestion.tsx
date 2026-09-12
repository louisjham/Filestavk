import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "../lib/api"
import {
  Mail,
  ShieldCheck,
  RefreshCw,
  Inbox,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileCode,
  ArrowRight,
  Database,
  ExternalLink,
  Layers,
  KeyRound,
  FileCheck2,
  Trash2,
  SlidersHorizontal,
} from "lucide-react"

export function Ingestion() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<"stream" | "verification" | "settings" | "database">("stream")
  const [selectedMsgIds, setSelectedMsgIds] = useState<string[]>([])
  const [selectedStagedId, setSelectedStagedId] = useState<number | null>(null)
  const [verificationFilter, setVerificationFilter] = useState<string>("PARSED")

  // Connection settings state
  const [configForm, setConfigForm] = useState({
    email_address: "info@hemocyaninlaw.com",
    app_password: "",
    imap_host: "imap.gmail.com",
    imap_port: 993,
  })
  const [testResult, setTestResult] = useState<any>(null)

  // Side-by-side editing form state
  const [verifyForm, setVerifyForm] = useState({
    case_number: "",
    court: "",
    category: "",
    defendant_name: "",
    hearing_datetime: "",
    warrant_number: "",
    amount_paid: 0,
    notes: "",
    verified_by: "Kimbel Brandon, Esq.",
  })

  // Purge confirmation state
  const [purgeConfirmed, setPurgeConfirmed] = useState(false)
  const [purgeResult, setPurgeResult] = useState<any>(null)

  // 1. Fetch Gmail Connector Config
  const { data: configData } = useQuery({
    queryKey: ["gmail-config"],
    queryFn: () => api.ingestion.getGmailConfig(),
  })

  // 2. Fetch Live Headers
  const {
    data: headersData,
    isLoading: loadingHeaders,
    refetch: refetchHeaders,
    isFetching: fetchingHeaders,
  } = useQuery({
    queryKey: ["gmail-live-headers"],
    queryFn: () => api.ingestion.getLiveHeaders({ limit: 40 }),
  })

  // 3. Fetch Staged Items Awaiting / Completed Verification
  const {
    data: stagedList,
    isLoading: loadingStaged,
    refetch: refetchStaged,
  } = useQuery({
    queryKey: ["staged-emails", verificationFilter],
    queryFn: () => api.ingestion.listStaged({ status: verificationFilter || undefined }),
  })

  // 4. Fetch Detailed Staged Item for Modal / Side-by-Side Review
  const { data: stagedDetail, isLoading: loadingDetail } = useQuery({
    queryKey: ["staged-detail", selectedStagedId],
    queryFn: () => (selectedStagedId ? api.ingestion.getStagedDetail(selectedStagedId) : null),
    enabled: !!selectedStagedId,
  })

  // Populate verify form when detail loads
  const handleOpenDetail = async (id: number) => {
    setSelectedStagedId(id)
    try {
      const detail = await api.ingestion.getStagedDetail(id)
      const ext = detail.extracted_meta?.extracted || {}
      const spec = ext.specialized_fields || {}
      setVerifyForm({
        case_number: ext.primary_case_number || "",
        court: ext.court || "105th District Court",
        category: ext.category || detail.filter_tag || "UNCATEGORIZED",
        defendant_name: ext.defendant_name || "",
        hearing_datetime: spec.hearing_datetime || "",
        warrant_number: spec.warrant_number || "",
        amount_paid: spec.amount_paid || 0,
        notes: detail.parsed_email?.plain_body?.slice(0, 200) || "",
        verified_by: "Kimbel Brandon, Esq.",
      })
    } catch {
      // ignore
    }
  }

  // Mutations
  const stageMutation = useMutation({
    mutationFn: (message_ids: string[]) => api.ingestion.stageEmails({ message_ids }),
    onSuccess: (res) => {
      setSelectedMsgIds([])
      queryClient.invalidateQueries({ queryKey: ["staged-emails"] })
      setActiveTab("verification")
      alert(res.message || "Emails successfully staged to semi-permanent storage for Human Review.")
    },
  })

  const commitMutation = useMutation({
    mutationFn: (data: { id: number; payload: any }) => api.ingestion.commitStaged(data.id, data.payload),
    onSuccess: (res) => {
      setSelectedStagedId(null)
      queryClient.invalidateQueries({ queryKey: ["staged-emails"] })
      queryClient.invalidateQueries({ queryKey: ["cases"] })
      queryClient.invalidateQueries({ queryKey: ["vouchers"] })
      alert(`Case data verified & committed!\n${res.committed_actions?.join("\n") || "Committed successfully"}`)
    },
  })

  const rejectMutation = useMutation({
    mutationFn: (id: number) => api.ingestion.rejectStaged(id),
    onSuccess: () => {
      setSelectedStagedId(null)
      queryClient.invalidateQueries({ queryKey: ["staged-emails"] })
    },
  })

  const testConnMutation = useMutation({
    mutationFn: (data: any) => api.ingestion.testGmailConnection(data),
    onSuccess: (res) => {
      setTestResult(res)
      queryClient.invalidateQueries({ queryKey: ["gmail-config"] })
    },
    onError: (err: any) => {
      setTestResult({ success: false, error: err.message || "Connection failed" })
    },
  })

  const purgeMutation = useMutation({
    mutationFn: () => api.settings.purgeMockData(),
    onSuccess: (res) => {
      setPurgeResult(res)
      setPurgeConfirmed(false)
      queryClient.invalidateQueries()
      alert("Database purged cleanly. Ready for production real-world ingestion.")
    },
  })

  const headers = headersData?.headers || []
  const stagedCount = stagedList?.length || 0

  const handleSelectAllHeaders = () => {
    if (selectedMsgIds.length === headers.length) {
      setSelectedMsgIds([])
    } else {
      setSelectedMsgIds(headers.map((h: any) => h.id))
    }
  }

  const handleToggleHeader = (id: string) => {
    setSelectedMsgIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    )
  }

  const getTagBadge = (tag: string) => {
    switch (tag) {
      case "COUNTY_AUDITOR_WARRANT":
        return <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded text-xs font-semibold flex items-center gap-1">🟢 Auditor Warrant</span>
      case "NUECES_COURT_NOTICE":
        return <span className="bg-purple-500/10 text-purple-400 border border-purple-500/20 px-2 py-0.5 rounded text-xs font-semibold flex items-center gap-1">🟣 Court Notice</span>
      case "ODYSSEY_EFILING":
        return <span className="bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded text-xs font-semibold flex items-center gap-1">🔵 Odyssey E-File</span>
      case "APPOINTMENT_ORDER":
        return <span className="bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2 py-0.5 rounded text-xs font-semibold flex items-center gap-1">🟡 Appointment Order</span>
      case "DA_DISCOVERY":
        return <span className="bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-2 py-0.5 rounded text-xs font-semibold flex items-center gap-1">📜 Morton Discovery</span>
      default:
        return <span className="bg-slate-800 text-slate-400 px-2 py-0.5 rounded text-xs">General Mail</span>
    }
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-5 rounded-xl">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-blue-600/10 text-blue-400 rounded-lg border border-blue-500/20">
            <Mail className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-white">Live Ingestion & Verification Hub</h1>
              <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2.5 py-0.5 rounded-full text-xs font-semibold flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5" />
                Google for Business (Zero 2FA Prompts)
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Secure IMAP/SSL • Semi-Permanent RFC 822 MIME Staging • Mandatory Human Case Verification
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => refetchHeaders()}
            disabled={fetchingHeaders}
            className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-3 py-1.5 rounded-lg text-xs font-medium transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${fetchingHeaders ? "animate-spin text-blue-400" : ""}`} />
            {fetchingHeaders ? "Streaming..." : "Fetch Live Stream"}
          </button>
          <button
            onClick={() => setActiveTab("settings")}
            className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 px-3 py-1.5 rounded-lg text-xs font-medium transition"
          >
            <SlidersHorizontal className="w-3.5 h-3.5 text-slate-400" />
            Connector Config
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab("stream")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition ${
            activeTab === "stream"
              ? "bg-blue-600 text-white shadow-sm"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
          }`}
        >
          <Inbox className="w-4 h-4" />
          Live Mailbox Stream
          <span className="bg-blue-950 text-blue-200 text-xs px-2 py-0.5 rounded-full">
            {headers.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("verification")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition relative ${
            activeTab === "verification"
              ? "bg-blue-600 text-white shadow-sm"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
          }`}
        >
          <FileCheck2 className="w-4 h-4" />
          Human Verification Board
          {stagedCount > 0 && (
            <span className="bg-amber-500 text-slate-950 font-bold text-xs px-2 py-0.5 rounded-full">
              {stagedCount}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("settings")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition ${
            activeTab === "settings"
              ? "bg-blue-600 text-white shadow-sm"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
          }`}
        >
          <KeyRound className="w-4 h-4" />
          Connector Settings
        </button>

        <button
          onClick={() => setActiveTab("database")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition ${
            activeTab === "database"
              ? "bg-blue-600 text-white shadow-sm"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
          }`}
        >
          <Database className="w-4 h-4" />
          Clean Slate Purge Tool
        </button>
      </div>

      {/* TAB 1: LIVE MAILBOX STREAM */}
      {activeTab === "stream" && (
        <div className="space-y-4">
          <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-medium">Bulk Action:</span>
              <button
                onClick={handleSelectAllHeaders}
                className="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs px-3 py-1.5 rounded-lg border border-slate-700 font-medium"
              >
                {selectedMsgIds.length === headers.length ? "Deselect All" : "Select All"}
              </button>
              {selectedMsgIds.length > 0 && (
                <button
                  onClick={() => stageMutation.mutate(selectedMsgIds)}
                  disabled={stageMutation.isPending}
                  className="bg-blue-600 hover:bg-blue-500 text-white text-xs px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1.5 shadow-sm"
                >
                  <Layers className="w-3.5 h-3.5" />
                  Stage ({selectedMsgIds.length}) Raw .eml to Verification Board
                </button>
              )}
            </div>

            <div className="text-xs text-slate-400">
              Connected Account: <strong className="text-white">{configData?.email_address || "info@hemocyaninlaw.com"}</strong>
            </div>
          </div>

          {loadingHeaders ? (
            <div className="p-12 text-center text-slate-400 bg-slate-900 border border-slate-800 rounded-xl">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-blue-400" />
              Fetching live mailbox headers via IMAP/SSL...
            </div>
          ) : headers.length === 0 ? (
            <div className="p-12 text-center text-slate-400 bg-slate-900 border border-slate-800 rounded-xl">
              No matching emails found in INBOX.
            </div>
          ) : (
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950/80 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                  <tr>
                    <th className="p-3.5 w-10 text-center">
                      <input
                        type="checkbox"
                        checked={selectedMsgIds.length === headers.length && headers.length > 0}
                        onChange={handleSelectAllHeaders}
                        className="rounded border-slate-700 bg-slate-950 text-blue-600"
                      />
                    </th>
                    <th className="p-3.5 w-48">Sender</th>
                    <th className="p-3.5">Subject & Detection Tag</th>
                    <th className="p-3.5 w-36">Detected Case #</th>
                    <th className="p-3.5 w-40">Date</th>
                    <th className="p-3.5 w-28 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-medium">
                  {headers.map((h: any) => {
                    const isSelected = selectedMsgIds.includes(h.id)
                    return (
                      <tr
                        key={h.id}
                        className={`hover:bg-slate-800/40 transition cursor-pointer ${
                          isSelected ? "bg-blue-950/20" : ""
                        }`}
                        onClick={() => handleToggleHeader(h.id)}
                      >
                        <td className="p-3.5 text-center" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => handleToggleHeader(h.id)}
                            className="rounded border-slate-700 bg-slate-950 text-blue-600"
                          />
                        </td>
                        <td className="p-3.5 truncate max-w-[200px]" title={h.from}>
                          <span className="text-white font-medium">{h.from.split("<")[0].trim() || h.from}</span>
                        </td>
                        <td className="p-3.5">
                          <div className="flex items-center gap-2">
                            {getTagBadge(h.filter_tag)}
                            <span className="text-white truncate max-w-lg">{h.subject}</span>
                          </div>
                        </td>
                        <td className="p-3.5">
                          {h.extracted_case_numbers?.length > 0 ? (
                            <span className="font-mono text-xs bg-slate-800 border border-slate-700 text-blue-300 px-2 py-0.5 rounded">
                              {h.extracted_case_numbers.join(", ")}
                            </span>
                          ) : (
                            <span className="text-slate-500 italic">—</span>
                          )}
                        </td>
                        <td className="p-3.5 text-slate-400 whitespace-nowrap text-xs">
                          {h.date ? h.date.slice(0, 16) : "Recent"}
                        </td>
                        <td className="p-3.5 text-right" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={() => stageMutation.mutate([h.id])}
                            disabled={stageMutation.isPending}
                            className="bg-slate-800 hover:bg-blue-600 hover:text-white text-slate-300 border border-slate-700 px-2.5 py-1 rounded text-xs transition flex items-center gap-1 ml-auto"
                          >
                            <Layers className="w-3 h-3" />
                            Stage
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: HUMAN VERIFICATION BOARD */}
      {activeTab === "verification" && (
        <div className="space-y-4">
          <div className="bg-amber-500/10 border border-amber-500/20 p-4 rounded-xl flex items-start gap-3 text-amber-200 text-xs">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <strong className="text-amber-300 font-semibold block text-sm">Mandatory Grounding Rule: Human Verification First</strong>
              Raw RFC 822 MIME byte streams are stored in semi-permanent staging (<code className="text-amber-300 bg-amber-950/40 px-1 py-0.5 rounded">backend/data/raw_emails/</code>). To eliminate hallucinations and false assumptions, all extracted court dates, case numbers, and auditor warrant disbursements must be approved by an attorney before writing into active database records.
            </div>
          </div>

          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Filter Queue:</span>
              <button
                onClick={() => setVerificationFilter("PARSED")}
                className={`text-xs px-3 py-1 rounded-lg border font-medium transition ${
                  verificationFilter === "PARSED"
                    ? "bg-amber-500 text-slate-950 border-amber-400 font-bold"
                    : "bg-slate-900 text-slate-400 border-slate-800 hover:text-white"
                }`}
              >
                Awaiting Review (PARSED)
              </button>
              <button
                onClick={() => setVerificationFilter("VERIFIED_COMMITTED")}
                className={`text-xs px-3 py-1 rounded-lg border font-medium transition ${
                  verificationFilter === "VERIFIED_COMMITTED"
                    ? "bg-emerald-600 text-white border-emerald-500 font-bold"
                    : "bg-slate-900 text-slate-400 border-slate-800 hover:text-white"
                }`}
              >
                Verified & Committed
              </button>
              <button
                onClick={() => setVerificationFilter("")}
                className={`text-xs px-3 py-1 rounded-lg border font-medium transition ${
                  verificationFilter === ""
                    ? "bg-blue-600 text-white border-blue-500 font-bold"
                    : "bg-slate-900 text-slate-400 border-slate-800 hover:text-white"
                }`}
              >
                All Records
              </button>
            </div>

            <button
              onClick={() => refetchStaged()}
              className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Refresh Board
            </button>
          </div>

          {loadingStaged ? (
            <div className="p-12 text-center text-slate-400 bg-slate-900 border border-slate-800 rounded-xl">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-blue-400" />
              Loading staged verification queue...
            </div>
          ) : stagedList?.length === 0 ? (
            <div className="p-12 text-center text-slate-400 bg-slate-900 border border-slate-800 rounded-xl">
              <FileCode className="w-8 h-8 mx-auto mb-2 text-slate-600" />
              No records in this queue. Head over to the <strong className="text-white">Live Mailbox Stream</strong> tab to stage incoming court notices and auditor disbursements!
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3">
              {stagedList.map((item: any) => {
                const ext = item.extracted_data?.extracted || {}
                const isCommitted = item.etl_status === "VERIFIED_COMMITTED"
                const isRejected = item.etl_status === "REJECTED"

                return (
                  <div
                    key={item.id}
                    onClick={() => handleOpenDetail(item.id)}
                    className="bg-slate-900 border border-slate-800 hover:border-slate-700 p-4 rounded-xl cursor-pointer transition shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4"
                  >
                    <div className="space-y-1.5 flex-1">
                      <div className="flex items-center gap-2">
                        {getTagBadge(item.filter_tag)}
                        <span className="text-xs text-slate-400 font-mono">ID #{item.id}</span>
                        {isCommitted ? (
                          <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs px-2 py-0.5 rounded font-semibold flex items-center gap-1">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Verified by {item.verified_by || "Kimbel Brandon"}
                          </span>
                        ) : isRejected ? (
                          <span className="bg-rose-500/10 text-rose-400 border border-rose-500/20 text-xs px-2 py-0.5 rounded font-semibold flex items-center gap-1">
                            <XCircle className="w-3.5 h-3.5" /> Rejected
                          </span>
                        ) : (
                          <span className="bg-amber-500/10 text-amber-300 border border-amber-500/20 text-xs px-2 py-0.5 rounded font-semibold flex items-center gap-1 animate-pulse">
                            ⏳ Needs Human Approval
                          </span>
                        )}
                        <span className="text-xs bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">
                          Confidence: {Math.round((ext.confidence || 0.8) * 100)}%
                        </span>
                      </div>

                      <h3 className="text-sm font-bold text-white line-clamp-1">{item.subject}</h3>
                      
                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400">
                        <span>From: <strong className="text-slate-300">{item.sender}</strong></span>
                        <span>Date: <strong className="text-slate-300">{item.date_sent}</strong></span>
                        {ext.court && <span>Court: <strong className="text-purple-300">{ext.court}</strong></span>}
                      </div>

                      {/* Extracted Proposal Preview */}
                      <div className="mt-2 bg-slate-950/80 border border-slate-800/80 rounded-lg p-2.5 flex items-center gap-3 text-xs">
                        <div className="font-mono bg-blue-950 text-blue-300 px-2 py-0.5 rounded border border-blue-900">
                          {ext.primary_case_number || "No Case # Detected"}
                        </div>
                        <div className="text-slate-300 truncate">
                          {ext.proposed_actions?.[0]?.description || "Link email to case record"}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-end md:self-center">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleOpenDetail(item.id)
                        }}
                        className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-4 py-2 rounded-lg transition flex items-center gap-1 shadow-sm"
                      >
                        Inspect & Verify
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: CONNECTOR SETTINGS */}
      {activeTab === "settings" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <KeyRound className="w-5 h-5 text-blue-400" />
                Google for Business Connector (App Password)
              </h2>
              <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2.5 py-0.5 rounded-full font-medium">
                Non-Expiring / No 2FA Prompts
              </span>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-400 font-medium mb-1">Attorney Email Address</label>
                <input
                  type="email"
                  value={configForm.email_address}
                  onChange={(e) => setConfigForm({ ...configForm, email_address: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono"
                  placeholder="info@hemocyaninlaw.com"
                />
              </div>

              <div>
                <label className="block text-slate-400 font-medium mb-1">
                  Google 16-Character App Password
                </label>
                <input
                  type="password"
                  value={configForm.app_password}
                  onChange={(e) => setConfigForm({ ...configForm, app_password: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono"
                  placeholder="xxxx xxxx xxxx xxxx"
                />
                <span className="text-[11px] text-slate-500 mt-1 block">
                  Generated once under Google Account Security. Bypasses ongoing 2FA phone prompts forever.
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 font-medium mb-1">IMAP Host</label>
                  <input
                    type="text"
                    value={configForm.imap_host}
                    onChange={(e) => setConfigForm({ ...configForm, imap_host: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 font-medium mb-1">SSL Port</label>
                  <input
                    type="number"
                    value={configForm.imap_port}
                    onChange={(e) => setConfigForm({ ...configForm, imap_port: Number(e.target.value) })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono"
                  />
                </div>
              </div>

              <div className="pt-3 flex gap-2">
                <button
                  onClick={() => testConnMutation.mutate(configForm)}
                  disabled={testConnMutation.isPending}
                  className="bg-blue-600 hover:bg-blue-500 text-white font-semibold px-4 py-2 rounded-lg text-xs transition flex-1 flex items-center justify-center gap-1.5"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${testConnMutation.isPending ? "animate-spin" : ""}`} />
                  {testConnMutation.isPending ? "Testing Handshake..." : "Test IMAP/SSL Handshake"}
                </button>
              </div>

              {testResult && (
                <div
                  className={`p-3 rounded-lg border text-xs mt-3 ${
                    testResult.success
                      ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-300"
                      : "bg-rose-500/10 border-rose-500/20 text-rose-300"
                  }`}
                >
                  <strong>{testResult.success ? "Connection Verified!" : "Handshake Failed"}</strong>
                  <p className="mt-0.5">{testResult.message || testResult.error}</p>
                </div>
              )}
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4 text-xs text-slate-300">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              How to Generate a Google App Password in 60 Seconds
            </h3>
            <ol className="list-decimal list-inside space-y-2 text-slate-400">
              <li>Log in to Kimbel's Google for Business account (<strong className="text-slate-200">info@hemocyaninlaw.com</strong>).</li>
              <li>Go to <strong className="text-slate-200">Google Account Security</strong> (<a href="https://myaccount.google.com/security" target="_blank" rel="noreferrer" className="text-blue-400 underline inline-flex items-center gap-0.5">myaccount.google.com/security <ExternalLink className="w-3 h-3" /></a>).</li>
              <li>Under "How you sign in to Google", select <strong className="text-slate-200">2-Step Verification</strong>.</li>
              <li>Scroll to the bottom and click <strong className="text-slate-200">App Passwords</strong>.</li>
              <li>Enter <code className="text-blue-300 bg-slate-950 px-1 py-0.5 rounded">Filestavk Ingestion</code> as the app name and click <strong className="text-slate-200">Create</strong>.</li>
              <li>Copy the 16-character code and paste it into the box on the left.</li>
            </ol>
            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-slate-400">
              💡 <strong>Why this is superior:</strong> Unlike standard OAuth tokens which expire every 7 days without Enterprise publishing, Google App Passwords stay connected indefinitely and never send 2FA prompts to the attorney's smartphone.
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: DATABASE CLEAN SLATE PURGE TOOL */}
      {activeTab === "database" && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-2xl mx-auto space-y-4">
          <div className="flex items-center gap-3 border-b border-slate-800 pb-3">
            <div className="p-2.5 bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded-lg">
              <Trash2 className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Production Clean Slate Reset</h2>
              <p className="text-xs text-slate-400">Purge demo and mock seed data while preserving system schemas and attorney profile</p>
            </div>
          </div>

          <div className="bg-rose-500/10 border border-rose-500/20 p-4 rounded-lg text-rose-300 text-xs space-y-2">
            <p className="font-semibold">⚠️ Production Milestone Warning</p>
            <p>
              This action will permanently delete all mock cases, demo clients, mock vouchers, and mock time entries from the SQLite database.
              Attorney credentials, lookup directories, and classification categories will remain untouched.
            </p>
          </div>

          <div className="space-y-3 pt-2">
            <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={purgeConfirmed}
                onChange={(e) => setPurgeConfirmed(e.target.checked)}
                className="rounded border-slate-700 bg-slate-950 text-rose-600"
              />
              <span>I confirm I want to reset the database to a clean production state for live data ingestion.</span>
            </label>

            <button
              onClick={() => purgeMutation.mutate()}
              disabled={!purgeConfirmed || purgeMutation.isPending}
              className={`w-full py-2.5 rounded-lg text-xs font-bold transition flex items-center justify-center gap-2 ${
                purgeConfirmed
                  ? "bg-rose-600 hover:bg-rose-500 text-white shadow-lg cursor-pointer"
                  : "bg-slate-800 text-slate-500 cursor-not-allowed"
              }`}
            >
              <Trash2 className="w-4 h-4" />
              {purgeMutation.isPending ? "Purging Mock Tables..." : "Purge All Mock Data Now"}
            </button>
          </div>

          {purgeResult && (
            <div className="bg-emerald-500/10 border border-emerald-500/20 p-4 rounded-lg text-emerald-300 text-xs mt-4">
              <strong>Database Purged Cleanly!</strong>
              <p className="mt-1">{purgeResult.message}</p>
            </div>
          )}
        </div>
      )}

      {/* SIDE-BY-SIDE HUMAN VERIFICATION DRAWER / MODAL */}
      {selectedStagedId && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-6xl max-h-[92vh] flex flex-col overflow-hidden shadow-2xl">
            {/* Modal Header */}
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
              <div className="flex items-center gap-2.5">
                <FileCheck2 className="w-5 h-5 text-amber-400" />
                <div>
                  <h2 className="text-sm font-bold text-white">
                    Side-by-Side Human Verification: Staged Email #{selectedStagedId}
                  </h2>
                  <p className="text-[11px] text-slate-400">
                    Compare raw RFC 822 MIME byte stream on left against proposed structured database record on right.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedStagedId(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 text-sm"
              >
                ✕
              </button>
            </div>

            {/* Modal Body: Two Columns */}
            <div className="flex-1 overflow-y-auto grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-slate-800">
              {/* Left Column: Raw Email RFC 822 / HTML Viewer */}
              <div className="p-5 space-y-3 bg-slate-950/40 overflow-y-auto max-h-[72vh]">
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                  <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                    <Mail className="w-4 h-4 text-blue-400" />
                    Raw RFC 822 MIME Email Content
                  </span>
                  <span className="text-[11px] text-slate-500 font-mono">
                    {stagedDetail?.raw_size_bytes || 0} bytes
                  </span>
                </div>

                <div className="space-y-1 text-xs text-slate-300 bg-slate-900/80 p-3 rounded-lg border border-slate-800">
                  <div><strong className="text-slate-400">From:</strong> {stagedDetail?.sender}</div>
                  <div><strong className="text-slate-400">To:</strong> {stagedDetail?.recipient}</div>
                  <div><strong className="text-slate-400">Date:</strong> {stagedDetail?.date_sent}</div>
                  <div><strong className="text-slate-400">Subject:</strong> {stagedDetail?.subject}</div>
                </div>

                {stagedDetail?.parsed_email?.html_body ? (
                  <div className="border border-slate-800 rounded-lg p-4 bg-white text-slate-900 text-xs overflow-x-auto">
                    <div
                      dangerouslySetInnerHTML={{ __html: stagedDetail.parsed_email.html_body }}
                    />
                  </div>
                ) : (
                  <pre className="bg-slate-900 border border-slate-800 rounded-lg p-3 text-xs text-slate-300 whitespace-pre-wrap font-mono">
                    {stagedDetail?.parsed_email?.plain_body || stagedDetail?.subject}
                  </pre>
                )}
              </div>

              {/* Right Column: Structured Case Extraction Proposal Form */}
              <div className="p-5 space-y-4 bg-slate-900/60 overflow-y-auto max-h-[72vh]">
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                  <span className="text-xs font-bold text-white flex items-center gap-1.5">
                    <FileCheck2 className="w-4 h-4 text-emerald-400" />
                    Structured Case Extraction Proposal (Human Editable)
                  </span>
                  <span className="text-xs bg-amber-500/10 text-amber-300 border border-amber-500/20 px-2 py-0.5 rounded font-semibold">
                    Requires Approval
                  </span>
                </div>

                <div className="space-y-3 text-xs">
                  <div>
                    <label className="block text-slate-300 font-semibold mb-1">
                      Nueces County Case Number
                    </label>
                    <input
                      type="text"
                      value={verifyForm.case_number}
                      onChange={(e) => setVerifyForm({ ...verifyForm, case_number: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white font-mono font-bold"
                      placeholder="e.g. 2024-CR-1042-D"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-slate-300 font-semibold mb-1">Presiding Court</label>
                      <input
                        type="text"
                        value={verifyForm.court}
                        onChange={(e) => setVerifyForm({ ...verifyForm, court: e.target.value })}
                        className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white"
                        placeholder="105th District Court"
                      />
                    </div>
                    <div>
                      <label className="block text-slate-300 font-semibold mb-1">Category</label>
                      <select
                        value={verifyForm.category}
                        onChange={(e) => setVerifyForm({ ...verifyForm, category: e.target.value })}
                        className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white"
                      >
                        <option value="COUNTY_AUDITOR_WARRANT">Auditor Disbursement Warrant</option>
                        <option value="HEARING_NOTICE">Hearing / Court Notice</option>
                        <option value="ODYSSEY_EFILING">Odyssey E-Filing Acceptance</option>
                        <option value="APPOINTMENT_ORDER">Order Appointing Counsel</option>
                        <option value="DA_DISCOVERY">Michael Morton Discovery</option>
                        <option value="UNCATEGORIZED">General Case Document</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-slate-300 font-semibold mb-1">Defendant Name</label>
                    <input
                      type="text"
                      value={verifyForm.defendant_name}
                      onChange={(e) => setVerifyForm({ ...verifyForm, defendant_name: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white"
                      placeholder="e.g. Carlos Ramirez"
                    />
                  </div>

                  {verifyForm.category === "COUNTY_AUDITOR_WARRANT" && (
                    <div className="grid grid-cols-2 gap-3 bg-emerald-950/20 border border-emerald-900/40 p-3 rounded-lg">
                      <div>
                        <label className="block text-emerald-300 font-semibold mb-1">Warrant / Check #</label>
                        <input
                          type="text"
                          value={verifyForm.warrant_number}
                          onChange={(e) => setVerifyForm({ ...verifyForm, warrant_number: e.target.value })}
                          className="w-full bg-slate-950 border border-emerald-800 rounded-lg px-3 py-2 text-emerald-200 font-mono"
                          placeholder="WARR-904812"
                        />
                      </div>
                      <div>
                        <label className="block text-emerald-300 font-semibold mb-1">Amount Paid ($)</label>
                        <input
                          type="number"
                          step="0.01"
                          value={verifyForm.amount_paid}
                          onChange={(e) => setVerifyForm({ ...verifyForm, amount_paid: parseFloat(e.target.value) || 0 })}
                          className="w-full bg-slate-950 border border-emerald-800 rounded-lg px-3 py-2 text-emerald-200 font-mono"
                        />
                      </div>
                    </div>
                  )}

                  {verifyForm.category === "HEARING_NOTICE" && (
                    <div className="bg-purple-950/20 border border-purple-900/40 p-3 rounded-lg">
                      <label className="block text-purple-300 font-semibold mb-1">Hearing Date & Time</label>
                      <input
                        type="text"
                        value={verifyForm.hearing_datetime}
                        onChange={(e) => setVerifyForm({ ...verifyForm, hearing_datetime: e.target.value })}
                        className="w-full bg-slate-950 border border-purple-800 rounded-lg px-3 py-2 text-purple-200"
                        placeholder="e.g. October 14, 2026 at 9:00 AM"
                      />
                    </div>
                  )}

                  <div>
                    <label className="block text-slate-300 font-semibold mb-1">Attorney Verification Stamp</label>
                    <input
                      type="text"
                      value={verifyForm.verified_by}
                      onChange={(e) => setVerifyForm({ ...verifyForm, verified_by: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-300 font-medium"
                    />
                  </div>
                </div>

                {/* Commit Actions */}
                <div className="pt-4 border-t border-slate-800 flex items-center justify-between gap-3">
                  <button
                    onClick={() => rejectMutation.mutate(selectedStagedId)}
                    disabled={rejectMutation.isPending}
                    className="bg-slate-800 hover:bg-rose-900/60 text-rose-300 border border-slate-700 px-4 py-2.5 rounded-lg text-xs font-semibold transition"
                  >
                    Dismiss / Reject
                  </button>

                  <button
                    onClick={() =>
                      commitMutation.mutate({
                        id: selectedStagedId,
                        payload: verifyForm,
                      })
                    }
                    disabled={commitMutation.isPending}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white px-5 py-2.5 rounded-lg text-xs font-bold transition flex items-center gap-2 shadow-lg cursor-pointer"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    {commitMutation.isPending ? "Committing..." : "Verify & Commit to Live Database"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
