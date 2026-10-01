import React, { useState } from "react"
import { AlertTriangle, CheckCircle2, BookOpen, Sparkles, X, ChevronRight } from "lucide-react"
import { api } from "@/lib/api"

interface HumanReviewCorrectionModalProps {
  documentItem: any
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export const HumanReviewCorrectionModal: React.FC<HumanReviewCorrectionModalProps> = ({
  documentItem,
  isOpen,
  onClose,
  onSuccess,
}) => {
  if (!isOpen || !documentItem) return null

  const meta = typeof documentItem.metadata_json === "string"
    ? (() => {
        try {
          return JSON.parse(documentItem.metadata_json)
        } catch {
          return {}
        }
      })()
    : documentItem.metadata_json || {}

  const legalMeta = meta.legal_metadata || {}
  const missingFields: string[] = meta.missing_fields || legalMeta.missing_fields || ["court"]
  const docType = documentItem.classification_label || legalMeta.classification_label || "appointment_order"

  const [corrections, setCorrections] = useState<Record<string, string>>({
    court: legalMeta.court || "",
    judge: legalMeta.judge || "",
    case_number: legalMeta.primary_case_number || "",
    defendant_name: legalMeta.defendant_name || "",
    extended_due_date_iso: legalMeta.specialized_fields?.extended_due_date_iso || "",
    appellate_case_number: legalMeta.appellate_case_number || "",
  })

  const [learnSubrule, setLearnSubrule] = useState(true)
  const [subruleField, setSubruleField] = useState(missingFields[0] || "court")
  const [subruleType, setSubruleType] = useState("CONSTANT_OVERRIDE")
  const [anchorSnippet, setAnchorSnippet] = useState(
    legalMeta.primary_case_number || documentItem.filename?.replace(/\.[^/.]+$/, "") || ""
  )
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const handleFieldChange = (field: string, val: string) => {
    setCorrections((prev) => ({ ...prev, [field]: val }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    setErrorMsg(null)

    try {
      const payload = {
        corrections: {
          ...corrections,
          ...(corrections.case_number ? { primary_case_number: corrections.case_number } : {}),
        },
        learn_subrule: learnSubrule,
        subrule_field: learnSubrule ? subruleField : undefined,
        subrule_pattern: learnSubrule ? (corrections[subruleField] || anchorSnippet) : undefined,
        subrule_type: learnSubrule ? subruleType : "CONSTANT_OVERRIDE",
        subrule_doc_type: docType,
        sample_text_snippet: learnSubrule ? anchorSnippet : undefined,
      }

      await api.documents.submitHumanCorrection(documentItem.id, payload)
      onSuccess()
      onClose()
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to submit human review correction.")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl bg-slate-900 border border-amber-500/30 rounded-xl shadow-2xl overflow-hidden text-slate-100 my-8">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 bg-amber-950/40 border-b border-amber-500/20">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-amber-500/10 rounded-lg text-amber-400 border border-amber-500/20">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-amber-100 flex items-center gap-2">
                Human-in-the-Loop Review
                <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 font-mono">
                  {docType}
                </span>
              </h2>
              <p className="text-xs text-slate-400 truncate max-w-md">
                {documentItem.filename}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {/* Missing Fields Banner */}
          <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg text-xs text-amber-200 flex items-start gap-2">
            <Sparkles className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-amber-300">Required fields missing: </span>
              {missingFields.map((f) => (
                <span key={f} className="inline-block bg-amber-500/20 px-1.5 py-0.5 rounded font-mono mr-1 text-amber-200">
                  {f}
                </span>
              ))}
              <p className="mt-1 text-slate-300">
                Filestavk halted downstream execution to prevent hallucinating incorrect court venues or judges.
                Please confirm the correct values below.
              </p>
            </div>
          </div>

          {errorMsg && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-xs text-rose-300">
              {errorMsg}
            </div>
          )}

          {/* Missing Fields Input Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Court Venue <span className="text-amber-400">*</span>
              </label>
              <input
                type="text"
                value={corrections.court}
                onChange={(e) => handleFieldChange("court", e.target.value)}
                placeholder="e.g. 105th District Court or 13th Court of Appeals"
                className="w-full bg-slate-800 border border-slate-700 focus:border-amber-500 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 outline-none transition"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Presiding Judge / Clerk
              </label>
              <input
                type="text"
                value={corrections.judge}
                onChange={(e) => handleFieldChange("judge", e.target.value)}
                placeholder="e.g. Hon. Jack W. Pulcher / Kathy S. Mills, Clerk"
                className="w-full bg-slate-800 border border-slate-700 focus:border-amber-500 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 outline-none transition"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Case / Cause Number <span className="text-amber-400">*</span>
              </label>
              <input
                type="text"
                value={corrections.case_number}
                onChange={(e) => handleFieldChange("case_number", e.target.value)}
                placeholder="e.g. 2024-CR-1042-D or 13-26-00155-CR"
                className="w-full bg-slate-800 border border-slate-700 focus:border-amber-500 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 outline-none transition"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Defendant / Appellant Name
              </label>
              <input
                type="text"
                value={corrections.defendant_name}
                onChange={(e) => handleFieldChange("defendant_name", e.target.value)}
                placeholder="e.g. Frank A. Roberts"
                className="w-full bg-slate-800 border border-slate-700 focus:border-amber-500 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 outline-none transition"
              />
            </div>

            {docType.includes("appellate") && (
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Appellate Brief Due Date (ISO)
                </label>
                <input
                  type="date"
                  value={corrections.extended_due_date_iso}
                  onChange={(e) => handleFieldChange("extended_due_date_iso", e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 focus:border-amber-500 rounded-lg px-3 py-2 text-sm text-slate-100 outline-none transition"
                />
              </div>
            )}
          </div>

          {/* Sub-Rule Learning Toggle Box */}
          <div className="p-4 bg-slate-800/60 border border-cyan-500/20 rounded-lg space-y-3">
            <div className="flex items-center justify-between">
              <label className="flex items-center space-x-2 text-sm font-medium text-cyan-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={learnSubrule}
                  onChange={(e) => setLearnSubrule(e.target.checked)}
                  className="rounded bg-slate-900 border-slate-700 text-cyan-500 focus:ring-cyan-500 h-4 w-4"
                />
                <span className="flex items-center gap-1.5">
                  <BookOpen className="h-4 w-4 text-cyan-400" />
                  Teach Filestavk: Save Sub-Rule for Future Parsing
                </span>
              </label>
              <span className="text-[11px] text-slate-400">Zero-Touch Automation</span>
            </div>

            {learnSubrule && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 text-xs">
                <div>
                  <label className="block text-slate-400 mb-1">Field to Automate</label>
                  <select
                    value={subruleField}
                    onChange={(e) => setSubruleField(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 outline-none"
                  >
                    <option value="court">Court Venue</option>
                    <option value="judge">Presiding Judge</option>
                    <option value="case_number">Case Number</option>
                    <option value="extended_due_date">Appellate Due Date</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">Anchor Match / Key</label>
                  <input
                    type="text"
                    value={anchorSnippet}
                    onChange={(e) => setAnchorSnippet(e.target.value)}
                    placeholder="Anchor phrase in document"
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 outline-none"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end space-x-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex items-center space-x-2 px-5 py-2 text-xs font-medium bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-slate-950 font-semibold rounded-lg shadow-lg shadow-amber-500/20 transition disabled:opacity-50"
            >
              <CheckCircle2 className="h-4 w-4" />
              <span>{isSubmitting ? "Synthesizing Sub-Rule..." : "Confirm & Resume Pipeline"}</span>
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
