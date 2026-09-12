import { useState, useRef, DragEvent, ChangeEvent } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import {
  Upload,
  FileText,
  FileSpreadsheet,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Eye,
  ArrowRight,
  ShieldCheck,
  FileCheck,
  Trash2,
  Layers,
  Sparkles,
  Clock,
  UserCheck,
} from "lucide-react"

interface DocumentDropzoneProps {
  onUploadSuccess?: () => void
  cases?: any[]
}

const ALLOWED_EXTS = [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv"]

export function DocumentDropzone({ onUploadSuccess, cases = [] }: DocumentDropzoneProps) {
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [isDragging, setIsDragging] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [batchInspection, setBatchInspection] = useState<any | null>(null)
  const [inspectError, setInspectError] = useState<string | null>(null)
  const [autoProvision, setAutoProvision] = useState(true)

  // Batch Inspection Mutation
  const inspectMutation = useMutation({
    mutationFn: (files: File[]) => api.documents.batchInspect(files),
    onSuccess: (data) => {
      setBatchInspection(data)
      setInspectError(null)
    },
    onError: (err: any) => {
      setInspectError(err.message || "Failed to inspect batch documents")
      setBatchInspection(null)
    },
  })

  // Final Batch Upload Mutation
  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (selectedFiles.length === 0) return
      return api.documents.batchUpload(selectedFiles, autoProvision)
    },
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ["documents"] })
      queryClient.invalidateQueries({ queryKey: ["cases"] })
      queryClient.invalidateQueries({ queryKey: ["clients"] })
      setSelectedFiles([])
      setBatchInspection(null)
      if (onUploadSuccess) onUploadSuccess()
      alert(`Batch Ingestion Complete: ${data?.success_count || 0} document(s) saved and processed!`)
    },
    onError: (err: any) => {
      alert(`Upload failed: ${err.message || "Error saving batch documents"}`)
    },
  })

  const handleFiles = (filesList: FileList | File[]) => {
    const filesArr = Array.from(filesList)
    const validFiles: File[] = []
    const invalidNames: string[] = []

    filesArr.forEach((f) => {
      const ext = "." + f.name.split(".").pop()?.toLowerCase()
      if (ALLOWED_EXTS.includes(ext)) {
        validFiles.push(f)
      } else {
        invalidNames.push(f.name)
      }
    })

    if (invalidNames.length > 0) {
      setInspectError(`Unsupported files skipped: ${invalidNames.join(", ")}. Allowed formats: PDF, DOCX, DOC, XLSX, XLS, CSV.`)
    } else {
      setInspectError(null)
    }

    if (validFiles.length > 0) {
      const combined = [...selectedFiles, ...validFiles]
      setSelectedFiles(combined)
      inspectMutation.mutate(combined)
    }
  }

  const handleRemoveFile = (index: number) => {
    const next = selectedFiles.filter((_, i) => i !== index)
    setSelectedFiles(next)
    if (next.length > 0) {
      inspectMutation.mutate(next)
    } else {
      setBatchInspection(null)
    }
  }

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files)
    }
  }

  const handleFileInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files)
    }
  }

  const getFormatIcon = (filename: string) => {
    const ext = filename.split(".").pop()?.toLowerCase()
    if (ext === "pdf") return <FileText className="w-5 h-5 text-rose-400 shrink-0" />
    if (ext === "docx" || ext === "doc") return <FileCheck className="w-5 h-5 text-blue-400 shrink-0" />
    if (ext === "xlsx" || ext === "xls" || ext === "csv") return <FileSpreadsheet className="w-5 h-5 text-emerald-400 shrink-0" />
    return <FileText className="w-5 h-5 text-slate-400 shrink-0" />
  }

  return (
    <div className="space-y-4">
      {/* Dropzone Box */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-200 ${
          isDragging
            ? "border-blue-500 bg-blue-500/10 scale-[1.01]"
            : "border-slate-800 bg-slate-900/60 hover:bg-slate-900 hover:border-slate-700"
        }`}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileInputChange}
          multiple
          accept=".pdf,.docx,.doc,.xlsx,.xls,.csv"
          className="hidden"
        />

        <div className="max-w-md mx-auto space-y-3">
          <div className="w-12 h-12 rounded-xl bg-blue-500/10 text-blue-400 flex items-center justify-center mx-auto border border-blue-500/20">
            <Upload className="w-6 h-6" />
          </div>

          <div>
            <p className="text-sm font-bold text-white">
              Drag &amp; Drop Single or Multiple Legal Documents
            </p>
            <p className="text-xs text-slate-400 mt-0.5">
              Select multiple files at once &bull; PDF, DOCX, DOC, XLSX, XLS, CSV
            </p>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-1.5 pt-1 text-[11px] font-medium text-slate-400">
            <span className="bg-rose-500/10 text-rose-400 border border-rose-500/20 px-2 py-0.5 rounded">
              PDF Documents
            </span>
            <span className="bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded">
              Word (DOCX/DOC)
            </span>
            <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded">
              Spreadsheets (XLSX/CSV)
            </span>
            <span className="bg-purple-500/10 text-purple-400 border border-purple-500/20 px-2 py-0.5 rounded">
              Multi-File Batch Ingest
            </span>
          </div>
        </div>
      </div>

      {/* Loading Inspection State */}
      {inspectMutation.isPending && (
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl text-center space-y-2">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto text-blue-400" />
          <p className="text-xs font-semibold text-white">
            Inspecting {selectedFiles.length} Document(s) &amp; Matching Static Legal Rules...
          </p>
          <p className="text-[11px] text-slate-400">
            Validating magic byte integrity, parsing Nueces entities, and evaluating stage transitions.
          </p>
        </div>
      )}

      {/* Error / Rejection Card */}
      {inspectError && (
        <div className="bg-rose-500/10 border border-rose-500/20 p-4 rounded-xl flex items-start gap-3 text-xs text-rose-300">
          <XCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <strong className="font-bold block text-sm">Notice</strong>
            <p className="mt-0.5">{inspectError}</p>
          </div>
        </div>
      )}

      {/* Batch Staging Queue & Resolution Overview */}
      {batchInspection && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
          {/* Top Aggregate Summary Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3.5">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-600/10 text-blue-400 rounded-lg border border-blue-500/20">
                <Layers className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <span>Batch Staging Queue ({batchInspection.total_files} file{batchInspection.total_files > 1 ? "s" : ""})</span>
                  <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                    {batchInspection.healthy_count} Healthy
                  </span>
                </h3>
                <div className="flex items-center gap-2.5 text-xs text-slate-400 mt-0.5">
                  <span className="text-blue-300 font-medium">✨ {batchInspection.clients_to_create} New Client(s)</span>
                  <span>&bull;</span>
                  <span className="text-purple-300 font-medium">⚖️ {batchInspection.cases_to_create} New Case(s)</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  setSelectedFiles([])
                  setBatchInspection(null)
                }}
                className="bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
              >
                Clear All
              </button>
              <button
                onClick={() => uploadMutation.mutate()}
                disabled={uploadMutation.isPending || batchInspection.healthy_count === 0}
                className="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 shadow-md cursor-pointer disabled:opacity-50"
              >
                <CheckCircle2 className="w-4 h-4" />
                {uploadMutation.isPending ? "Processing..." : `Confirm & Ingest All (${batchInspection.healthy_count})`}
              </button>
            </div>
          </div>

          {/* Staged Files List */}
          <div className="space-y-2.5">
            {batchInspection.files?.map((item: any, idx: number) => {
              const legal = item.legal_metadata || {}
              const rule = item.matched_rule
              const isHealthy = item.is_healthy

              return (
                <div
                  key={idx}
                  className={`border rounded-xl p-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3 transition ${
                    isHealthy
                      ? "bg-slate-950/80 border-slate-800 hover:border-slate-700"
                      : "bg-rose-950/20 border-rose-900"
                  }`}
                >
                  {/* File & Category */}
                  <div className="flex items-start gap-3 min-w-[260px]">
                    {getFormatIcon(item.filename)}
                    <div>
                      <h4 className="text-xs font-bold text-white line-clamp-1" title={item.filename}>
                        {item.filename}
                      </h4>
                      <div className="flex items-center gap-2 text-[11px] text-slate-400 mt-0.5">
                        <span className="uppercase font-mono text-[10px] bg-slate-800 px-1.5 py-0.2 rounded">
                          {item.detected_format || "DOC"}
                        </span>
                        <span>{(item.file_size_bytes / 1024).toFixed(1)} KB</span>
                        {isHealthy ? (
                          <span className="text-emerald-400 font-medium">✓ Anti-Stub OK</span>
                        ) : (
                          <span className="text-rose-400 font-medium">✗ {item.error || "Rejected"}</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Extracted Entities & Rule Details */}
                  {isHealthy && (
                    <div className="flex-1 grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                      {/* Identified Category & Rule */}
                      <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-2">
                        <span className="text-slate-500 block text-[10px] uppercase font-semibold">
                          Document Rule
                        </span>
                        <div className="font-semibold text-purple-300 text-xs truncate mt-0.5">
                          {rule?.display_name || legal.classification_label || "Uncategorized"}
                        </div>
                        {rule?.target_case_stage && (
                          <div className="text-[10px] text-slate-400 mt-0.5">
                            Stage: <strong className="text-slate-300">{rule.target_case_stage}</strong>
                          </div>
                        )}
                      </div>

                      {/* Client Hierarchy Resolution */}
                      <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-2">
                        <span className="text-slate-500 block text-[10px] uppercase font-semibold">
                          1. Client Record
                        </span>
                        <div className="font-medium text-slate-200 text-xs truncate mt-0.5">
                          {item.client_resolution?.exists ? (
                            <span className="text-emerald-400 font-semibold flex items-center gap-1">
                              <UserCheck className="w-3 h-3" /> Reusing #{item.client_resolution.id} ({item.client_resolution.name})
                            </span>
                          ) : (
                            <span className="text-blue-400 font-semibold flex items-center gap-1">
                              <Sparkles className="w-3 h-3" /> Auto-creating: {legal.defendant_name || "New Client"}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Case Hierarchy Resolution */}
                      <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-2">
                        <span className="text-slate-500 block text-[10px] uppercase font-semibold">
                          2. Case Record
                        </span>
                        <div className="font-medium text-slate-200 text-xs truncate mt-0.5">
                          {item.case_resolution?.exists ? (
                            <span className="text-emerald-400 font-semibold">
                              Reusing #{item.case_resolution.case_number}
                            </span>
                          ) : (
                            <span className="text-blue-400 font-semibold flex items-center gap-1">
                              <Sparkles className="w-3 h-3" /> Auto-creating #{legal.primary_case_number || "New Case"}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex items-center justify-end gap-1.5 shrink-0">
                    <button
                      onClick={() => handleRemoveFile(idx)}
                      className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition"
                      title="Remove from batch queue"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Auto Provision Toggle */}
          <div className="pt-2 flex items-center justify-between border-t border-slate-800/80 text-xs text-slate-400">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={autoProvision}
                onChange={(e) => setAutoProvision(e.target.checked)}
                className="rounded border-slate-700 bg-slate-950 text-blue-600"
              />
              <span>Automatically provision and link missing Client &amp; Case records during batch ingestion</span>
            </label>
          </div>
        </div>
      )}
    </div>
  )
}
