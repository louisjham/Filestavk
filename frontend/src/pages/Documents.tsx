import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  FileText,
  Upload,
  Search,
  Filter,
  Eye,
  Download,
  X,
  Scale,
  FileSpreadsheet,
  FileCheck2,
  Trash2,
  ShieldCheck,
  Calendar,
  CheckCircle2,
  ExternalLink,
  Layers,
  Settings,
  Sliders,
  Sparkles,
  Clock,
  RotateCcw,
  Edit,
  Plus,
  AlertTriangle,
  UserCheck,
} from "lucide-react"
import { formatDate } from "@/lib/utils"
import { ClassificationBadge } from "@/components/shared/ClassificationBadge"
import { DocumentDropzone } from "@/components/documents/DocumentDropzone"

export function Documents() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<"repository" | "rules">("repository")
  const [searchTerm, setSearchTerm] = useState("")
  const [selectedLabel, setSelectedLabel] = useState<string>("ALL")
  const [selectedDocType, setSelectedDocType] = useState<string>("ALL")
  const [inspectDoc, setInspectDoc] = useState<any | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [bindCaseId, setBindCaseId] = useState<string>("")
  const [bindHearingDate, setBindHearingDate] = useState<string>("")
  const [createHearingEvent, setCreateHearingEvent] = useState(false)

  // Rules State
  const [editingRule, setEditingRule] = useState<any | null>(null)
  const [ruleFormData, setRuleFormData] = useState<any>({})

  const { data: documents, isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.documents.list(),
  })

  const { data: cases } = useQuery({
    queryKey: ["cases"],
    queryFn: () => api.cases.list(),
  })

  const { data: documentRules, isLoading: isRulesLoading } = useQuery({
    queryKey: ["documentRules"],
    queryFn: () => api.documentRules.list(),
  })

  const bindMutation = useMutation({
    mutationFn: (docId: number) =>
      api.documents.bindCase(docId, {
        case_id: parseInt(bindCaseId),
        create_hearing_event: createHearingEvent,
        hearing_datetime: bindHearingDate || undefined,
      }),
    onSuccess: (res: any) => {
      queryClient.invalidateQueries({ queryKey: ["documents"] })
      queryClient.invalidateQueries({ queryKey: ["cases"] })
      setInspectDoc(null)
      alert(`Document bound to Case #${res.case_number} successfully!`)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (docId: number) => api.documents.delete(docId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] })
      setInspectDoc(null)
    },
  })

  const approveReviewMutation = useMutation({
    mutationFn: (docId: number) => api.documents.approveReview(docId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] })
      queryClient.invalidateQueries({ queryKey: ["cases"] })
      queryClient.invalidateQueries({ queryKey: ["vouchers"] })
      queryClient.invalidateQueries({ queryKey: ["voucher-stats"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard-alerts"] })
      setInspectDoc(null)
      alert("Document verified & approved! Linked case and voucher have resumed automated workflow.")
    },
    onError: (err: any) => {
      alert(`Approval failed: ${err.message || "Unknown error"}`)
    },
  })

  const updateRuleMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) =>
      api.documentRules.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documentRules"] })
      setEditingRule(null)
      alert("Static document rule updated successfully!")
    },
    onError: (err: any) => {
      alert(`Failed to update rule: ${err.message || "Unknown error"}`)
    },
  })

  const resetRulesMutation = useMutation({
    mutationFn: () => api.documentRules.resetDefaults(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documentRules"] })
      alert("Document rules reset to Nueces County legal defaults!")
    },
  })

  const filteredDocs = documents?.filter((d: any) => {
    const matchSearch =
      d.filename?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      d.doc_type?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      d.source?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      d.content_text?.toLowerCase().includes(searchTerm.toLowerCase())

    const matchLabel =
      selectedLabel === "ALL" ? true : d.classification_label === selectedLabel

    const matchType =
      selectedDocType === "ALL"
        ? true
        : selectedDocType === "spreadsheet"
        ? ["xlsx", "xls", "csv"].includes(d.doc_type?.toLowerCase())
        : selectedDocType === "word"
        ? ["docx", "doc"].includes(d.doc_type?.toLowerCase())
        : d.doc_type?.toLowerCase() === selectedDocType

    return matchSearch && matchLabel && matchType
  })

  const getDocTypeIcon = (docType: string) => {
    const t = docType?.toLowerCase()
    if (t === "pdf") return <FileText className="h-4 w-4 text-rose-400 shrink-0" />
    if (t === "docx" || t === "doc") return <FileCheck2 className="h-4 w-4 text-blue-400 shrink-0" />
    if (["xlsx", "xls", "csv"].includes(t)) return <FileSpreadsheet className="h-4 w-4 text-emerald-400 shrink-0" />
    return <FileText className="h-4 w-4 text-slate-400 shrink-0" />
  }

  const handleOpenEditRule = (rule: any) => {
    setEditingRule(rule)
    setRuleFormData({
      display_name: rule.display_name,
      description: rule.description,
      lifecycle_stage: rule.lifecycle_stage,
      target_case_stage: rule.target_case_stage,
      target_case_status: rule.target_case_status,
      is_cja_default: rule.is_cja_default,
      set_has_appointment_order: rule.set_has_appointment_order,
      set_appointment_status: rule.set_appointment_status,
      auto_populate_client: rule.auto_populate_client,
      auto_populate_case: rule.auto_populate_case,
      create_docket_event: rule.create_docket_event,
      event_type: rule.event_type,
      event_title_template: rule.event_title_template,
      event_desc_template: rule.event_desc_template,
      trigger_statutory_deadline: rule.trigger_statutory_deadline,
      statutory_basis: rule.statutory_basis,
      deadline_name: rule.deadline_name,
      deadline_hours_offset: rule.deadline_hours_offset,
      confidence_threshold: rule.confidence_threshold,
      require_human_verification: rule.require_human_verification,
      is_active: rule.is_active,
    })
  }

  return (
    <div className="space-y-6 max-w-7xl pb-16">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-5 rounded-xl">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2.5 bg-blue-600/10 text-blue-400 rounded-lg border border-blue-500/20">
              <FileText className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white">
                Intelligent Document System &amp; Rules Engine
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Batch multi-document ingestion, anti-stub verification &amp; user-editable Nueces County static lifecycle rules.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {activeTab === "repository" && (
            <Button
              size="sm"
              onClick={() => setIsUploading(!isUploading)}
              className="gap-1.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs cursor-pointer"
            >
              <Upload className="h-4 w-4" />
              {isUploading ? "Hide Batch Ingestion" : "Ingest Documents (Batch)"}
            </Button>
          )}
        </div>
      </div>

      {/* Top Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab("repository")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition cursor-pointer ${
            activeTab === "repository"
              ? "bg-blue-600/15 text-blue-400 border border-blue-500/30"
              : "text-slate-400 hover:text-white hover:bg-slate-800"
          }`}
        >
          <Layers className="w-4 h-4" />
          Document Repository &amp; Ingestion ({documents?.length || 0})
        </button>

        <button
          onClick={() => setActiveTab("rules")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition cursor-pointer ${
            activeTab === "rules"
              ? "bg-purple-600/15 text-purple-400 border border-purple-500/30"
              : "text-slate-400 hover:text-white hover:bg-slate-800"
          }`}
        >
          <Sliders className="w-4 h-4" />
          Static Document Rules Engine ({documentRules?.length || 0})
        </button>
      </div>

      {/* TAB 1: DOCUMENT REPOSITORY & BATCH INGESTION */}
      {activeTab === "repository" && (
        <div className="space-y-6">
          {/* Intelligent Multi-Format Dropzone */}
          {isUploading && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-lg space-y-3">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div>
                  <h2 className="text-sm font-bold text-white flex items-center gap-2">
                    <Upload className="w-4 h-4 text-blue-400" />
                    Multi-Document Batch Ingestion Engine
                  </h2>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Drag and drop multiple files to run automatic health checks, magic byte verification, and entity extraction.
                  </p>
                </div>
                <button
                  onClick={() => setIsUploading(false)}
                  className="text-slate-400 hover:text-white text-xs p-1 cursor-pointer"
                >
                  ✕ Close
                </button>
              </div>

              <DocumentDropzone
                cases={cases || []}
                onUploadSuccess={() => {
                  setIsUploading(false)
                }}
              />
            </div>
          )}

          {/* Filter & Search Bar */}
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="h-4 w-4 text-slate-400 absolute left-3 top-2.5" />
              <Input
                placeholder="Search full text, filename, court, or case numbers..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9 text-xs bg-slate-900 border-slate-800 text-white placeholder:text-slate-500"
              />
            </div>

            <select
              className="h-9 rounded-lg border border-slate-800 bg-slate-900 px-3 text-xs text-slate-200 focus:outline-none"
              value={selectedDocType}
              onChange={(e) => setSelectedDocType(e.target.value)}
            >
              <option value="ALL">All File Formats</option>
              <option value="pdf">PDF Documents</option>
              <option value="word">Word (DOCX / DOC)</option>
              <option value="spreadsheet">Spreadsheets (XLSX / CSV)</option>
            </select>

            <select
              className="h-9 rounded-lg border border-slate-800 bg-slate-900 px-3 text-xs text-slate-200 focus:outline-none"
              value={selectedLabel}
              onChange={(e) => setSelectedLabel(e.target.value)}
            >
              <option value="ALL">All Document Types</option>
              <option value="appointment_order">Appointment Orders (Art. 26.04 CCP)</option>
              <option value="waiver_of_arraignment">Waiver of Arraignment</option>
              <option value="court_order">Court Orders &amp; Judgments</option>
              <option value="discovery">Michael Morton Discovery (Art. 39.14)</option>
              <option value="police_report">Police &amp; Incident Reports</option>
              <option value="hearing_notice">Hearing &amp; Setting Notices</option>
              <option value="warrant_remittance">Auditor Warrant Remittances</option>
              <option value="spreadsheet_roster">Spreadsheet Rosters</option>
              <option value="invoice">Attorney Fee Invoices</option>
              <option value="uncategorized">Uncategorized</option>
            </select>
          </div>

          {/* Documents Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            {isLoading ? (
              <div className="p-8 text-center text-slate-400 text-xs">Loading documents...</div>
            ) : filteredDocs && filteredDocs.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left text-slate-300">
                  <thead className="bg-slate-950/80 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                    <tr>
                      <th className="py-3 px-4 font-semibold">Filename &amp; Format</th>
                      <th className="py-3 px-4 font-semibold">Classification</th>
                      <th className="py-3 px-4 font-semibold">Linked Case</th>
                      <th className="py-3 px-4 font-semibold">Date Ingested</th>
                      <th className="py-3 px-4 font-semibold text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-medium">
                    {filteredDocs.map((doc: any) => {
                      let meta: any = {}
                      try {
                        meta = doc.metadata_json ? JSON.parse(doc.metadata_json) : {}
                      } catch {
                        meta = {}
                      }

                      const legal = meta.legal_metadata || {}

                      return (
                        <tr key={doc.id} className="hover:bg-slate-800/40 transition">
                          <td className="py-3 px-4">
                            <div className="font-semibold text-white flex items-center gap-2">
                              {getDocTypeIcon(doc.doc_type)}
                              <span className="truncate max-w-sm" title={doc.filename}>
                                {doc.filename}
                              </span>
                              <span className="text-[10px] uppercase font-mono bg-slate-800 border border-slate-700 px-1.5 py-0.2 rounded text-slate-400">
                                {doc.doc_type}
                              </span>
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            <div className="flex flex-col gap-1 items-start">
                              <ClassificationBadge
                                label={doc.classification_label}
                                confidence={doc.classification_confidence}
                              />
                              {meta.review_status === "AWAITING_HUMAN_REVIEW" && (
                                <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-300 bg-amber-950/70 border border-amber-500/40 px-2 py-0.5 rounded-full shadow-xs">
                                  <AlertTriangle className="h-3 w-3 text-amber-400 shrink-0" /> Awaiting Review
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            {doc.case_id ? (
                              <Link
                                to={`/cases/${doc.case_id}`}
                                className="text-blue-400 hover:underline font-mono text-xs flex items-center gap-1"
                              >
                                Case #{doc.case_id}
                              </Link>
                            ) : legal.primary_case_number ? (
                              <span className="font-mono text-xs text-amber-300 bg-amber-950/40 border border-amber-900/40 px-2 py-0.5 rounded">
                                Detected #{legal.primary_case_number}
                              </span>
                            ) : (
                              <span className="text-slate-500 italic">Unassigned</span>
                            )}
                          </td>
                          <td className="py-3 px-4 text-slate-400 whitespace-nowrap">
                            {formatDate(doc.created_at)}
                          </td>
                          <td className="py-3 px-4 text-right whitespace-nowrap">
                            <div className="flex items-center justify-end gap-1.5">
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 text-xs px-2 text-blue-400 hover:text-white hover:bg-slate-800"
                                onClick={() => {
                                  setInspectDoc(doc)
                                  setBindCaseId(doc.case_id ? String(doc.case_id) : "")
                                  setBindHearingDate(legal.specialized_fields?.hearing_datetime || "")
                                }}
                              >
                                <Eye className="h-3.5 w-3.5 mr-1" />
                                Inspect &amp; Bind
                              </Button>
                              {doc.filepath && (
                                <a
                                  href={api.documents.getFileUrl(doc.id)}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="p-1.5 text-slate-400 hover:text-white rounded hover:bg-slate-800"
                                  title="Download Attachment"
                                >
                                  <Download className="h-3.5 w-3.5" />
                                </a>
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
              <div className="p-12 text-center text-slate-400 text-xs">
                <FileText className="w-8 h-8 mx-auto mb-2 text-slate-600" />
                No documents found. Use the batch ingestion dropzone above to drag and drop court orders, appointment orders, or discovery packets.
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: STATIC DOCUMENT RULES ENGINE */}
      {activeTab === "rules" && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-900/80 border border-slate-800 p-4 rounded-xl">
            <div>
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <Sliders className="w-4 h-4 text-purple-400" />
                Configurable Static Document Rules &amp; Statutory Triggers
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Define and edit how each identified court document transitions case stages, populates client/case attributes, and logs statutory deadlines.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  if (confirm("Reset all document rules to default Nueces County statutory configurations?")) {
                    resetRulesMutation.mutate()
                  }
                }}
                disabled={resetRulesMutation.isPending}
                className="gap-1.5 text-xs border-slate-700 text-slate-300 hover:bg-slate-800 cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Reset to Nueces Defaults
              </Button>
            </div>
          </div>

          {/* Rules Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {isRulesLoading ? (
              <div className="p-8 text-center text-slate-400 text-xs col-span-2">Loading document rules...</div>
            ) : (
              documentRules?.map((rule: any) => (
                <div
                  key={rule.id}
                  className={`border rounded-xl p-5 space-y-3 transition ${
                    rule.is_active
                      ? "bg-slate-900 border-slate-800 hover:border-slate-700 shadow-md"
                      : "bg-slate-950/40 border-slate-900 opacity-60"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 border-b border-slate-800 pb-2.5">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-bold text-white">
                          {rule.display_name}
                        </h3>
                        <span className="font-mono text-[10px] bg-slate-800 text-purple-300 border border-purple-500/20 px-1.5 py-0.2 rounded">
                          {rule.document_type}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                        {rule.description}
                      </p>
                    </div>

                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleOpenEditRule(rule)}
                      className="h-7 text-xs px-2.5 border-purple-700/50 text-purple-300 hover:bg-purple-950/40 shrink-0 cursor-pointer"
                    >
                      <Edit className="w-3 h-3 mr-1" />
                      Edit Rule
                    </Button>
                  </div>

                  {/* Rule Features Grid */}
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-2.5">
                      <span className="text-slate-500 block text-[10px] uppercase font-semibold">
                        Target Case Stage
                      </span>
                      <div className="font-semibold text-blue-300 text-xs mt-0.5">
                        {rule.target_case_stage}
                      </div>
                      <div className="text-[10px] text-slate-400 mt-0.5 truncate">
                        Lifecycle: {rule.lifecycle_stage}
                      </div>
                    </div>

                    <div className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-2.5">
                      <span className="text-slate-500 block text-[10px] uppercase font-semibold">
                        Statutory Deadline Alert
                      </span>
                      {rule.trigger_statutory_deadline ? (
                        <div className="font-semibold text-amber-300 text-xs mt-0.5 flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5 shrink-0" />
                          <span>{rule.deadline_hours_offset}h Offset</span>
                        </div>
                      ) : (
                        <div className="text-slate-500 text-xs mt-0.5">None</div>
                      )}
                      <div className="text-[10px] text-slate-400 mt-0.5 truncate">
                        {rule.statutory_basis || "General"}
                      </div>
                    </div>
                  </div>

                  {/* Field Population Indicators */}
                  <div className="flex flex-wrap items-center gap-1.5 text-[11px] pt-1">
                    {rule.auto_populate_client && (
                      <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" /> Auto-fill Client (DOB/Phone/Address)
                      </span>
                    )}
                    {rule.auto_populate_case && (
                      <span className="bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" /> Auto-fill Case (Court/Charge)
                      </span>
                    )}
                    {rule.set_has_appointment_order && (
                      <span className="bg-purple-500/10 text-purple-300 border border-purple-500/20 px-2 py-0.5 rounded">
                        ✓ Verifies Appointment Order
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* EDIT DOCUMENT RULE MODAL */}
      {editingRule && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden shadow-2xl">
            {/* Modal Header */}
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
              <div>
                <h2 className="text-sm font-bold text-white flex items-center gap-2">
                  <Sliders className="w-4 h-4 text-purple-400" />
                  Edit Rule: {editingRule.display_name}
                </h2>
                <p className="text-[11px] text-slate-400">
                  Configure lifecycle actions, stage transitions, and statutory triggers for category <code className="text-purple-300">{editingRule.document_type}</code>.
                </p>
              </div>
              <button
                onClick={() => setEditingRule(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 text-sm cursor-pointer"
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block text-[11px] mb-1 font-semibold">
                    Display Name
                  </label>
                  <input
                    type="text"
                    value={ruleFormData.display_name || ""}
                    onChange={(e) => setRuleFormData({ ...ruleFormData, display_name: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-white text-xs font-medium"
                  />
                </div>

                <div>
                  <label className="text-slate-400 block text-[11px] mb-1 font-semibold">
                    Target Case Stage
                  </label>
                  <select
                    value={ruleFormData.target_case_stage || "MAGISTRATE_HEARING"}
                    onChange={(e) => setRuleFormData({ ...ruleFormData, target_case_stage: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-white text-xs font-medium"
                  >
                    <option value="MAGISTRATE_HEARING">MAGISTRATE_HEARING (Arrest / Appointment)</option>
                    <option value="PRE_TRIAL">PRE_TRIAL (Arraignment Waived / Motions)</option>
                    <option value="DISCOVERY">DISCOVERY (Morton Compliance / Brady)</option>
                    <option value="TRIAL">TRIAL (Jury Trial / Plea)</option>
                    <option value="DISPOSED">DISPOSED (Judgment / Dismissal)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-slate-400 block text-[11px] mb-1 font-semibold">
                  Rule Description &amp; Legal Context
                </label>
                <textarea
                  rows={2}
                  value={ruleFormData.description || ""}
                  onChange={(e) => setRuleFormData({ ...ruleFormData, description: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white text-xs"
                />
              </div>

              {/* Toggles */}
              <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 space-y-2.5">
                <span className="text-slate-300 font-semibold block text-xs">
                  Automated Entity &amp; Docket Actions
                </span>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={ruleFormData.auto_populate_client || false}
                      onChange={(e) => setRuleFormData({ ...ruleFormData, auto_populate_client: e.target.checked })}
                      className="rounded border-slate-700 bg-slate-950 text-blue-600"
                    />
                    <span>Auto-populate Client (DOB, Address, Phone, SO#)</span>
                  </label>

                  <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={ruleFormData.auto_populate_case || false}
                      onChange={(e) => setRuleFormData({ ...ruleFormData, auto_populate_case: e.target.checked })}
                      className="rounded border-slate-700 bg-slate-950 text-blue-600"
                    />
                    <span>Auto-populate Case (Charge, Court, Judge, In-Jail)</span>
                  </label>

                  <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={ruleFormData.set_has_appointment_order || false}
                      onChange={(e) => setRuleFormData({ ...ruleFormData, set_has_appointment_order: e.target.checked })}
                      className="rounded border-slate-700 bg-slate-950 text-purple-600"
                    />
                    <span>Set Has Appointment Order = True</span>
                  </label>

                  <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={ruleFormData.create_docket_event || false}
                      onChange={(e) => setRuleFormData({ ...ruleFormData, create_docket_event: e.target.checked })}
                      className="rounded border-slate-700 bg-slate-950 text-emerald-600"
                    />
                    <span>Create Case Docket Timeline Event</span>
                  </label>
                </div>
              </div>

              {/* Timeline Event Template */}
              {ruleFormData.create_docket_event && (
                <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 space-y-2">
                  <span className="text-slate-300 font-semibold block text-xs">
                    Docket Timeline Event Title Template
                  </span>
                  <input
                    type="text"
                    value={ruleFormData.event_title_template || ""}
                    onChange={(e) => setRuleFormData({ ...ruleFormData, event_title_template: e.target.value })}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-white font-mono text-xs"
                  />
                  <p className="text-[10px] text-slate-500">
                    Available variables: <code>{"{doc_title}"}</code>, <code>{"{court}"}</code>, <code>{"{judge}"}</code>, <code>{"{defendant_name}"}</code>, <code>{"{charge}"}</code>, <code>{"{attorney_name}"}</code>, <code>{"{sbn}"}</code>.
                  </p>
                </div>
              )}

              {/* Statutory Deadline Section */}
              <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-slate-300 font-semibold block text-xs">
                    Statutory Rule &amp; Deadline Reminder Trigger
                  </span>
                  <label className="flex items-center gap-1.5 text-xs text-amber-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={ruleFormData.trigger_statutory_deadline || false}
                      onChange={(e) => setRuleFormData({ ...ruleFormData, trigger_statutory_deadline: e.target.checked })}
                      className="rounded border-amber-700 bg-slate-950 text-amber-600"
                    />
                    <span>Enable Deadline Trigger</span>
                  </label>
                </div>

                {ruleFormData.trigger_statutory_deadline && (
                  <div className="grid grid-cols-2 gap-3 pt-1">
                    <div>
                      <label className="text-slate-400 block text-[10px] mb-1">
                        Statutory Basis
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. Tex. Code Crim. Proc. art. 26.04(j)(1)"
                        value={ruleFormData.statutory_basis || ""}
                        onChange={(e) => setRuleFormData({ ...ruleFormData, statutory_basis: e.target.value })}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1 text-white text-xs"
                      />
                    </div>
                    <div>
                      <label className="text-slate-400 block text-[10px] mb-1">
                        Hours Offset (e.g. 48 for 48-Hour Contact Rule)
                      </label>
                      <input
                        type="number"
                        value={ruleFormData.deadline_hours_offset || 48}
                        onChange={(e) => setRuleFormData({ ...ruleFormData, deadline_hours_offset: parseInt(e.target.value) || 0 })}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1 text-white text-xs"
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-800 flex items-center justify-end gap-2 bg-slate-950/60">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setEditingRule(null)}
                className="text-slate-400 hover:text-white text-xs"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={() => updateRuleMutation.mutate({ id: editingRule.id, data: ruleFormData })}
                disabled={updateRuleMutation.isPending}
                className="bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs cursor-pointer"
              >
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                {updateRuleMutation.isPending ? "Saving..." : "Save Rule Configuration"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Side-by-Side Document Inspection & Binding Modal */}
      {inspectDoc && (() => {
        let inspectMeta: any = {}
        try {
          inspectMeta = inspectDoc.metadata_json ? JSON.parse(inspectDoc.metadata_json) : {}
        } catch {
          inspectMeta = {}
        }

        return (
          <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden shadow-2xl">
              {/* Modal Header */}
              <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
                <div className="flex items-center gap-2.5">
                  {getDocTypeIcon(inspectDoc.doc_type)}
                  <div>
                    <h2 className="text-sm font-bold text-white line-clamp-1">
                      {inspectDoc.filename}
                    </h2>
                    <p className="text-[11px] text-slate-400">
                      Format: <strong className="text-slate-300 uppercase">{inspectDoc.doc_type}</strong> &bull; Classification: <strong className="text-slate-300 capitalize">{inspectDoc.classification_label?.replace("_", " ")}</strong> ({(inspectDoc.classification_confidence * 100).toFixed(0)}% Confidence)
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setInspectDoc(null)}
                  className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 text-sm cursor-pointer"
                >
                  ✕
                </button>
              </div>

              {/* Modal Body: Two Columns */}
              <div className="flex-1 overflow-y-auto grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-slate-800">
                {/* Left Column: Extracted Content Viewer */}
                <div className="p-5 space-y-3 bg-slate-950/40 overflow-y-auto max-h-[70vh]">
                  <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                    <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                      <FileText className="w-4 h-4 text-blue-400" />
                      Extracted Text &amp; Structure
                    </span>
                    <span className="text-[11px] text-slate-500 font-mono">
                      {inspectDoc.content_text?.length || 0} characters
                    </span>
                  </div>

                  <pre className="bg-slate-900 border border-slate-800 rounded-lg p-3 text-xs text-slate-300 whitespace-pre-wrap font-mono leading-relaxed max-h-[60vh] overflow-y-auto">
                    {inspectDoc.content_text || "No extracted digital text content available."}
                  </pre>
                </div>

                {/* Right Column: Legal Entity Metadata & Case Binding */}
                <div className="p-5 space-y-4 bg-slate-900/60 overflow-y-auto max-h-[70vh] flex flex-col justify-between">
                  <div className="space-y-4 text-xs">
                    {/* Awaiting Human Review Banner */}
                    {inspectMeta.review_status === "AWAITING_HUMAN_REVIEW" && (
                      <div className="p-4 bg-amber-500/15 border border-amber-500/40 rounded-xl space-y-3 shadow-md">
                        <div className="flex items-center gap-2 text-amber-300 font-bold text-xs">
                          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                          <span>Awaiting Human Review: Verify Clerk Stamp &amp; Signature</span>
                        </div>
                        <p className="text-[11px] text-amber-200/90 leading-relaxed">
                          {inspectMeta.human_review_instructions ||
                            "Review document to visually identify: (1) County / District Clerk 'FILED' stamp, and (2) Attorney signature or affirmation date under 'AFFIRMED'. If confirmed, approve to resume automated voucher workflow."}
                        </p>
                        <div className="grid grid-cols-2 gap-2 text-[10px] text-slate-300 bg-slate-950/60 p-2.5 rounded-lg border border-amber-500/20">
                          <div>
                            <span className="text-slate-500 block">Clerk Stamp Detected</span>
                            <span className={inspectMeta.has_clerk_file_stamp ? "text-emerald-400 font-bold" : "text-amber-400 font-bold"}>
                              {inspectMeta.has_clerk_file_stamp ? "✓ Yes" : "✗ Not Detected"}
                            </span>
                          </div>
                          <div>
                            <span className="text-slate-500 block">Attorney Signature Detected</span>
                            <span className={inspectMeta.has_attorney_affirmation ? "text-emerald-400 font-bold" : "text-amber-400 font-bold"}>
                              {inspectMeta.has_attorney_affirmation ? "✓ Yes" : "✗ Not Detected"}
                            </span>
                          </div>
                        </div>
                        <Button
                          size="sm"
                          onClick={() => approveReviewMutation.mutate(inspectDoc.id)}
                          disabled={approveReviewMutation.isPending}
                          className="w-full bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs cursor-pointer shadow-md gap-1.5"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          {approveReviewMutation.isPending ? "Approving & Resuming Pipeline..." : "Approve Stamp & Signature (Resume Workflow)"}
                        </Button>
                      </div>
                    )}

                    <div className="border-b border-slate-800 pb-2">
                      <h3 className="font-bold text-white text-xs flex items-center gap-1.5">
                        <ShieldCheck className="w-4 h-4 text-emerald-400" />
                        Extracted Nueces County Case Metadata
                      </h3>
                    </div>

                    <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-3 space-y-2">
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <span className="text-slate-500 block text-[11px]">Primary Case #</span>
                          <div className="font-mono font-bold text-blue-300 text-sm mt-0.5">
                            {inspectDoc.case_id ? `Case #${inspectDoc.case_id}` : "Unassigned"}
                          </div>
                        </div>
                        <div>
                          <span className="text-slate-500 block text-[11px]">Classification</span>
                          <span className="inline-block mt-0.5 font-semibold text-white bg-slate-800 px-2 py-0.5 rounded">
                            {inspectDoc.classification_label}
                          </span>
                        </div>
                      </div>
                    </div>

                  {/* Case Linkage Form */}
                  <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 space-y-3">
                    <span className="text-slate-300 font-semibold block text-xs">
                      Bind to Active Case Record
                    </span>

                    <div>
                      <label className="text-slate-400 block text-[11px] mb-1">
                        Select Target Case
                      </label>
                      <select
                        value={bindCaseId}
                        onChange={(e) => setBindCaseId(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white text-xs font-medium"
                      >
                        <option value="">-- Select a case to link --</option>
                        {cases?.map((c: any) => (
                          <option key={c.id} value={c.id}>
                            #{c.case_number} &bull; {c.court}
                          </option>
                        ))}
                      </select>
                    </div>

                    {inspectDoc.classification_label === "hearing_notice" && (
                      <div className="space-y-2 pt-1 border-t border-slate-800">
                        <label className="flex items-center gap-2 text-xs text-purple-300 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={createHearingEvent}
                            onChange={(e) => setCreateHearingEvent(e.target.checked)}
                            className="rounded border-purple-700 bg-slate-950 text-purple-600"
                          />
                          <span>Create Hearing Event on Court Docket</span>
                        </label>
                        {createHearingEvent && (
                          <input
                            type="text"
                            placeholder="Hearing Date (e.g. 2026-10-14)"
                            value={bindHearingDate}
                            onChange={(e) => setBindHearingDate(e.target.value)}
                            className="w-full bg-slate-900 border border-purple-800 rounded-lg px-3 py-1.5 text-purple-200 text-xs"
                          />
                        )}
                      </div>
                    )}

                    <Button
                      size="sm"
                      disabled={!bindCaseId || bindMutation.isPending}
                      onClick={() => bindMutation.mutate(inspectDoc.id)}
                      className="w-full bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold mt-2 cursor-pointer"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                      {bindMutation.isPending ? "Binding..." : "Confirm Binding to Case"}
                    </Button>
                  </div>
                </div>

                {/* Footer Controls */}
                <div className="pt-4 border-t border-slate-800 flex items-center justify-between gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      if (confirm("Are you sure you want to delete this document from the repository?")) {
                        deleteMutation.mutate(inspectDoc.id)
                      }
                    }}
                    className="text-rose-400 hover:text-rose-300 hover:bg-rose-950/40 text-xs cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5 mr-1" />
                    Delete
                  </Button>

                  <div className="flex gap-2">
                    {inspectDoc.filepath && (
                      <Button asChild variant="outline" size="sm" className="text-xs border-slate-700 text-slate-300 cursor-pointer">
                        <a href={api.documents.getFileUrl(inspectDoc.id)} target="_blank" rel="noreferrer">
                          <Download className="w-3.5 h-3.5 mr-1" />
                          Download Original
                        </a>
                      </Button>
                    )}
                    <Button
                      size="sm"
                      onClick={() => setInspectDoc(null)}
                      className="bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium cursor-pointer"
                    >
                      Close
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )
    })()}
    </div>
  )
}
