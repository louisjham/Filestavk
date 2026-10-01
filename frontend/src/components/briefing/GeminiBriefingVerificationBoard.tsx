import React, { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Sparkles,
  Calendar,
  AlertTriangle,
  FileCheck2,
  ExternalLink,
  Clock,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  Loader2,
  FileText,
  Copy,
  Check,
  Edit,
  Trash2,
} from "lucide-react"

interface GeminiBriefingVerificationBoardProps {
  onOpenIngestModal: () => void
}

export function GeminiBriefingVerificationBoard({ onOpenIngestModal }: GeminiBriefingVerificationBoardProps) {
  const queryClient = useQueryClient()
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL")
  const [selectedIndexes, setSelectedIndexes] = useState<number[]>([])
  const [showRawBrief, setShowRawBrief] = useState(false)
  const [copiedDraftIndex, setCopiedDraftIndex] = useState<number | null>(null)
  const [commitSuccessMessage, setCommitSuccessMessage] = useState<string | null>(null)

  // Edit proposal state
  const [editingProposal, setEditingProposal] = useState<any | null>(null)
  const [editProposalIndex, setEditProposalIndex] = useState<number | null>(null)
  const [editForm, setEditForm] = useState<any>({})

  const { data: briefData, isLoading } = useQuery({
    queryKey: ["latest-gemini-brief"],
    queryFn: () => api.briefing.getLatest(),
    staleTime: 1000 * 60 * 5,
  })

  const proposals: any[] = briefData?.proposals || []
  const summary: Record<string, number> = briefData?.summary_counts || { total_items: 0 }
  const conflicts: string[] = briefData?.conflicts || []

  // Initialize selected indexes when proposals load
  React.useEffect(() => {
    if (proposals.length > 0 && selectedIndexes.length === 0) {
      setSelectedIndexes(proposals.map((_: any, i: number) => i))
    }
  }, [proposals.length])

  const commitMutation = useMutation({
    mutationFn: (items: any[]) => api.briefing.commit(items),
    onSuccess: (data: any) => {
      setCommitSuccessMessage(
        `Successfully committed ${data.committed_total} items! Created ${data.created_cases.length} case(s), ${data.created_clients.length} client(s), and ${data.created_events.length} docket event(s).`
      )
      queryClient.invalidateQueries({ queryKey: ["dashboard-alerts"] })
      queryClient.invalidateQueries({ queryKey: ["cases"] })
      queryClient.invalidateQueries({ queryKey: ["clients"] })
      queryClient.invalidateQueries({ queryKey: ["events"] })
      queryClient.invalidateQueries({ queryKey: ["vouchers"] })
      setTimeout(() => setCommitSuccessMessage(null), 8000)
    },
  })

  const updateProposalMutation = useMutation({
    mutationFn: ({ index, data }: { index: number; data: any }) =>
      api.briefing.updateProposal(index, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["latest-gemini-brief"] })
      setEditingProposal(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (index: number) => api.briefing.deleteProposal(index),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["latest-gemini-brief"] })
    },
  })

  const handleOpenEditModal = (item: any, originalIndex: number) => {
    setEditingProposal(item)
    setEditProposalIndex(originalIndex)
    setEditForm({ ...item })
  }

  const handleSaveEditProposal = () => {
    if (editProposalIndex !== null) {
      updateProposalMutation.mutate({
        index: editProposalIndex,
        data: editForm,
      })
    }
  }

  const toggleSelectAll = () => {
    if (selectedIndexes.length === proposals.length) {
      setSelectedIndexes([])
    } else {
      setSelectedIndexes(proposals.map((_: any, i: number) => i))
    }
  }

  const toggleItem = (index: number) => {
    setSelectedIndexes((prev) =>
      prev.includes(index) ? prev.filter((i) => i !== index) : [...prev, index]
    )
  }

  const handleCopyDraft = (text: string, index: number) => {
    navigator.clipboard.writeText(text)
    setCopiedDraftIndex(index)
    setTimeout(() => setCopiedDraftIndex(null), 2000)
  }

  const handleCommitSelected = () => {
    const selectedProposals = proposals.filter((_: any, i: number) => selectedIndexes.includes(i))
    if (selectedProposals.length > 0) {
      commitMutation.mutate(selectedProposals)
    }
  }

  const filteredProposals = proposals
    .map((item: any, originalIndex: number) => ({ ...item, originalIndex }))
    .filter((item: any) => {
      if (selectedCategory === "ALL") return true
      if (selectedCategory === "HEARINGS") return item.category === "COURT_HEARING"
      if (selectedCategory === "DEADLINES") return item.category === "CRITICAL_DEADLINE"
      if (selectedCategory === "WAIVERS") return item.badge === "Waiver of Arraignment"
      if (selectedCategory === "APPEALS") return item.category === "APPELLATE_ORDER"
      return true
    })

  if (!briefData?.has_brief && !isLoading) {
    return (
      <Card className="border border-dashed border-cyan-500/30 bg-slate-950/40 p-6 text-center shadow-xs">
        <div className="max-w-md mx-auto space-y-3">
          <div className="h-10 w-10 mx-auto rounded-full bg-cyan-950/80 border border-cyan-500/40 flex items-center justify-center text-cyan-400">
            <Sparkles className="h-5 w-5" />
          </div>
          <h3 className="text-sm font-semibold text-slate-200">No Gemini 10-Day Deep-Dive Brief Staged</h3>
          <p className="text-xs text-muted-foreground">
            Run your custom Gemini Gem in Google Workspace, copy the generated brief, and paste it here to auto-populate dockets, client intake, and arraignment waivers.
          </p>
          <Button
            size="sm"
            onClick={onOpenIngestModal}
            className="text-xs gap-1.5 bg-cyan-600 hover:bg-cyan-500 text-white"
          >
            <Sparkles className="h-3.5 w-3.5" />
            Paste 10-Day Gem Brief
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <Card className="border border-cyan-500/30 bg-slate-950/90 shadow-xl shadow-cyan-950/20 overflow-hidden">
      <CardHeader className="p-5 border-b border-cyan-500/20 bg-gradient-to-r from-slate-950 via-slate-900 to-cyan-950/30">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <div className="h-7 w-7 rounded-lg bg-cyan-950 border border-cyan-400/40 flex items-center justify-center text-cyan-400">
                <Sparkles className="h-4 w-4" />
              </div>
              <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                Gemini 10-Day Deep-Dive Verification Board
              </CardTitle>
              <Badge variant="outline" className="text-[10px] border-cyan-500/40 text-cyan-300 bg-cyan-950/60">
                {proposals.length} Action Items
              </Badge>
            </div>
            <CardDescription className="text-xs text-cyan-300/80">
              Deterministic extraction from Kimbel's Gemini Gem. Review proposals and verify to populate Cases, Dockets, and Deadlines.
            </CardDescription>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowRawBrief(!showRawBrief)}
              className="text-xs gap-1 border-cyan-500/30 text-cyan-300 hover:bg-cyan-950/40"
            >
              <FileText className="h-3.5 w-3.5" />
              {showRawBrief ? "Hide Markdown" : "View Full Brief"}
              {showRawBrief ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </Button>
            <Button
              size="sm"
              onClick={onOpenIngestModal}
              className="text-xs gap-1.5 bg-cyan-600 hover:bg-cyan-500 text-white"
            >
              <Sparkles className="h-3.5 w-3.5" />
              Paste New Brief
            </Button>
          </div>
        </div>

        {/* Docket Conflict Banner if conflicts exist */}
        {conflicts.length > 0 && (
          <div className="mt-3 p-3 rounded-lg bg-amber-950/40 border border-amber-500/40 text-xs text-amber-200 flex items-start gap-2.5">
            <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-amber-300">Docket Conflict Alert Detected: </span>
              {conflicts.join(" | ")}
            </div>
          </div>
        )}

        {/* Success Commit Message Banner */}
        {commitSuccessMessage && (
          <div className="mt-3 p-3 rounded-lg bg-emerald-950/40 border border-emerald-500/40 text-xs text-emerald-200 flex items-center gap-2.5">
            <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
            <span>{commitSuccessMessage}</span>
          </div>
        )}
      </CardHeader>

      {/* Raw Markdown Brief Drawer */}
      {showRawBrief && briefData?.raw_text && (
        <div className="border-b border-cyan-500/20 bg-slate-900/90 p-4 max-h-[300px] overflow-y-auto">
          <div className="flex items-center justify-between mb-2 pb-1 border-b border-slate-800">
            <span className="text-xs font-semibold text-slate-300">Raw Gemini Brief Output</span>
            <span className="text-[11px] text-muted-foreground">{briefData.parsed_at ? new Date(briefData.parsed_at).toLocaleTimeString() : ""}</span>
          </div>
          <pre className="text-xs text-slate-300 font-mono whitespace-pre-wrap leading-relaxed">
            {briefData.raw_text}
          </pre>
        </div>
      )}

      {/* Category Tabs & Select All Header */}
      <div className="p-4 border-b border-border/40 bg-slate-950 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-1.5 flex-wrap">
          {[
            { id: "ALL", label: `All (${proposals.length})` },
            { id: "HEARINGS", label: `Hearings (${summary.hearings || 0})` },
            { id: "DEADLINES", label: `Deadlines & Appts (${summary.critical_deadlines || 0})` },
            { id: "WAIVERS", label: `Arraignment Waivers (${summary.waivers_of_arraignment || 0})` },
            { id: "APPEALS", label: `Appellate Orders (${summary.appellate_orders || 0})` },
          ].map((tab) => (
            <Button
              key={tab.id}
              variant={selectedCategory === tab.id ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setSelectedCategory(tab.id)}
              className={`text-xs h-7 px-2.5 rounded-md ${
                selectedCategory === tab.id
                  ? "bg-cyan-950/80 text-cyan-300 border border-cyan-500/40"
                  : "text-muted-foreground hover:text-slate-200"
              }`}
            >
              {tab.label}
            </Button>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={toggleSelectAll}
            className="text-xs text-cyan-400 hover:text-cyan-300 underline font-medium"
          >
            {selectedIndexes.length === proposals.length ? "Deselect All" : "Select All"}
          </button>
          <span className="text-muted-foreground">|</span>
          <Button
            size="sm"
            onClick={handleCommitSelected}
            disabled={selectedIndexes.length === 0 || commitMutation.isPending}
            className="text-xs gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold shadow-sm shadow-emerald-950/50"
          >
            {commitMutation.isPending ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Committing…
              </>
            ) : (
              <>
                <FileCheck2 className="h-3.5 w-3.5" />
                Verify & Commit ({selectedIndexes.length})
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Proposals List */}
      <CardContent className="p-4 space-y-3 max-h-[600px] overflow-y-auto">
        {filteredProposals.length === 0 ? (
          <div className="text-center py-8 text-xs text-muted-foreground">
            No items match the selected category.
          </div>
        ) : (
          filteredProposals.map((item: any) => {
            const isSelected = selectedIndexes.includes(item.originalIndex)
            return (
              <div
                key={item.originalIndex}
                className={`p-3.5 rounded-xl border transition-all ${
                  isSelected
                    ? "bg-slate-900/90 border-cyan-500/40 shadow-sm"
                    : "bg-slate-950/50 border-slate-800/80 opacity-70"
                }`}
              >
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleItem(item.originalIndex)}
                    className="mt-1 h-4 w-4 rounded-sm border-cyan-500/40 bg-slate-950 text-cyan-600 focus:ring-cyan-500/40 cursor-pointer"
                  />

                  <div className="flex-1 space-y-1.5 min-w-0">
                    {/* Header Row: Badges & Cause */}
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge
                          variant="outline"
                          className={`text-[10px] uppercase font-bold tracking-wider ${
                            item.badge === "Waiver of Arraignment"
                              ? "border-purple-500/40 text-purple-300 bg-purple-950/40"
                              : item.category === "COURT_HEARING"
                              ? "border-blue-500/40 text-blue-300 bg-blue-950/40"
                              : item.in_custody
                              ? "border-red-500/40 text-red-300 bg-red-950/40"
                              : "border-cyan-500/40 text-cyan-300 bg-cyan-950/40"
                          }`}
                        >
                          {item.badge}
                        </Badge>

                        {item.in_custody && (
                          <Badge variant="destructive" className="text-[10px] bg-red-900/60 text-red-200 border border-red-500/40">
                            <ShieldAlert className="h-3 w-3 mr-1 inline" />
                            In Jail
                          </Badge>
                        )}

                        {item.has_conflict && (
                          <Badge variant="outline" className="text-[10px] bg-amber-950/60 text-amber-300 border border-amber-500/50 font-semibold">
                            <AlertTriangle className="h-3 w-3 mr-1 inline text-amber-400" />
                            Docket Conflict
                          </Badge>
                        )}

                        <span className="text-xs font-semibold text-slate-100">
                          {item.client_name}
                        </span>

                        <span className="text-xs text-muted-foreground font-mono">
                          ({item.case_number})
                        </span>
                      </div>

                      {/* Source Link */}
                      {item.source_link && (
                        <a
                          href={item.source_link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[11px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1 shrink-0 underline"
                        >
                          <span>Source</span>
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                    </div>

                    {/* Venue & Event Date */}
                    <div className="flex items-center gap-3 text-[11px] text-muted-foreground flex-wrap">
                      <span className="text-slate-300 font-medium">{item.court}</span>
                      {item.judge && <span>&bull; {item.judge}</span>}
                      {item.event_date && (
                        <span className="flex items-center gap-1 text-cyan-300">
                          <Calendar className="h-3 w-3 inline" />
                          {item.event_date} {item.event_time ? `at ${item.event_time}` : ""}
                        </span>
                      )}
                      {item.charge && (
                        <span className="text-amber-300/90">&bull; Charge: {item.charge}</span>
                      )}
                    </div>

                    {/* Details narrative */}
                    <p className="text-xs text-slate-300 leading-relaxed font-normal pt-0.5">
                      {item.details}
                    </p>

                    {/* Proposed Action Draft */}
                    {item.proposed_action && (
                      <div className="mt-2 p-2.5 rounded-lg bg-slate-950 border border-cyan-500/20 text-xs text-cyan-200/90 flex items-start justify-between gap-3">
                        <div>
                          <span className="font-semibold text-cyan-300 block text-[10px] uppercase tracking-wider mb-0.5">
                            Proposed Draft for ADA / Clerk:
                          </span>
                          <p className="italic">"{item.proposed_action}"</p>
                        </div>
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => handleCopyDraft(item.proposed_action, item.originalIndex)}
                          className="h-7 w-7 text-cyan-400 hover:text-cyan-200 shrink-0"
                          title="Copy Proposed Draft"
                        >
                          {copiedDraftIndex === item.originalIndex ? (
                            <Check className="h-3.5 w-3.5 text-emerald-400" />
                          ) : (
                            <Copy className="h-3.5 w-3.5" />
                          )}
                        </Button>
                      </div>
                    )}

                    {/* Statutory Basis Tag */}
                    {item.statutory_basis && (
                      <div className="pt-1 text-[11px] text-cyan-400/90 flex items-center gap-1.5 font-mono">
                        <Clock className="h-3 w-3 inline text-cyan-400" />
                        <span>Statutory Clock: {item.statutory_basis}</span>
                      </div>
                    )}

                    {/* Proposal Action Buttons: Edit & Dismiss */}
                    <div className="pt-2 flex items-center justify-end gap-2 border-t border-slate-800/60 mt-2">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleOpenEditModal(item, item.originalIndex)}
                        className="h-7 px-2.5 text-xs text-slate-300 hover:text-cyan-300 hover:bg-cyan-950/40 gap-1"
                      >
                        <Edit className="h-3 w-3" />
                        Edit Data
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => deleteMutation.mutate(item.originalIndex)}
                        className="h-7 px-2 text-xs text-slate-400 hover:text-rose-400 hover:bg-rose-950/40 gap-1"
                        title="Dismiss from verification board"
                      >
                        <Trash2 className="h-3 w-3" />
                        Dismiss
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            )
          })
        )}
      </CardContent>

      {/* Edit Proposal Modal */}
      {editingProposal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-xs">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Edit className="w-4 h-4 text-cyan-400" />
                <h3 className="text-sm font-bold text-white">Edit Verification Item</h3>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setEditingProposal(null)}
                className="h-7 w-7 p-0 text-slate-400 hover:text-white"
              >
                ✕
              </Button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1">Client Name</label>
                  <input
                    type="text"
                    value={editForm.client_name || ""}
                    onChange={(e) => setEditForm({ ...editForm, client_name: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-white"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Cause Number</label>
                  <input
                    type="text"
                    value={editForm.case_number || ""}
                    onChange={(e) => setEditForm({ ...editForm, case_number: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-white font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1">Court</label>
                  <input
                    type="text"
                    value={editForm.court || ""}
                    onChange={(e) => setEditForm({ ...editForm, court: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-white"
                    placeholder="e.g. 13th Court of Appeals"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Judge / Clerk</label>
                  <input
                    type="text"
                    value={editForm.judge || ""}
                    onChange={(e) => setEditForm({ ...editForm, judge: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-white"
                    placeholder="e.g. Kathy S. Mills, Clerk"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1">Event / Due Date</label>
                  <input
                    type="date"
                    value={editForm.event_date || ""}
                    onChange={(e) => setEditForm({ ...editForm, event_date: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-white"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Badge / Category</label>
                  <input
                    type="text"
                    value={editForm.badge || ""}
                    onChange={(e) => setEditForm({ ...editForm, badge: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-white"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Details &amp; Procedural Summary</label>
                <textarea
                  rows={3}
                  value={editForm.details || ""}
                  onChange={(e) => setEditForm({ ...editForm, details: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded p-2.5 text-white text-xs"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Proposed Draft / Action</label>
                <textarea
                  rows={2}
                  value={editForm.proposed_action || ""}
                  onChange={(e) => setEditForm({ ...editForm, proposed_action: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-white text-xs italic"
                  placeholder="Optional draft pleading or notice..."
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 border-t border-slate-800 pt-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setEditingProposal(null)}
                className="text-xs border-slate-700 text-slate-300"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSaveEditProposal}
                disabled={updateProposalMutation.isPending}
                className="text-xs bg-cyan-600 hover:bg-cyan-500 text-white font-semibold"
              >
                {updateProposalMutation.isPending ? "Saving..." : "Save Proposal"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </Card>
  )
}
