import React, { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Sparkles, Loader2, ClipboardPaste, FileCheck2, AlertCircle, X } from "lucide-react"

interface GeminiBriefingIngestModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

export function GeminiBriefingIngestModal({
  open,
  onOpenChange,
  onSuccess,
}: GeminiBriefingIngestModalProps) {
  const queryClient = useQueryClient()
  const [briefText, setBriefText] = useState("")
  const [error, setError] = useState<string | null>(null)

  const pasteMutation = useMutation({
    mutationFn: (text: string) => api.briefing.paste(text),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["latest-gemini-brief"] })
      onOpenChange(false)
      setBriefText("")
      setError(null)
      if (onSuccess) onSuccess()
    },
    onError: (err: unknown) => {
      setError(err instanceof Error ? err.message : "Failed to parse Gemini Deep-Dive Brief.")
    },
  })

  const handlePasteClipboard = async () => {
    try {
      const clipText = await navigator.clipboard.readText()
      if (clipText) {
        setBriefText(clipText)
        setError(null)
      }
    } catch (err) {
      console.warn("Could not read clipboard automatically:", err)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!briefText.trim()) {
      setError("Please paste your Gemini 10-Day Deep-Dive Brief text.")
      return
    }
    pasteMutation.mutate(briefText)
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-xs p-4">
      <div className="relative w-full max-w-3xl rounded-2xl border border-cyan-500/30 bg-slate-950 p-6 text-slate-100 shadow-2xl shadow-cyan-950/50 flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-cyan-500/20 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-xl bg-cyan-950/80 border border-cyan-400/40 flex items-center justify-center text-cyan-400">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                Paste Gemini 10-Day Deep-Dive Brief
              </h2>
              <p className="text-xs text-cyan-300/80">
                Paste the raw output from your Workspace Gemini Gem. Filestavk will extract court hearings,
                appointments, arraignment waivers, and appellate orders into the Verification Board.
              </p>
            </div>
          </div>
          <Button
            size="icon"
            variant="ghost"
            onClick={() => onOpenChange(false)}
            className="h-8 w-8 text-muted-foreground hover:text-white"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex-1 flex flex-col min-h-0 space-y-4 pt-4">
          {error && (
            <div className="p-3 rounded-lg bg-red-950/40 border border-red-500/30 text-xs text-red-300 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
            <span className="font-medium text-slate-300">Brief Text (Markdown or Plain Text)</span>
            <div className="flex items-center gap-3">
              <span>{briefText.length} characters</span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handlePasteClipboard}
                className="h-7 text-xs gap-1 border-cyan-500/30 text-cyan-300 hover:bg-cyan-950/40"
              >
                <ClipboardPaste className="h-3.5 w-3.5" />
                Paste from Clipboard
              </Button>
            </div>
          </div>

          <div className="flex-1 min-h-[320px]">
            <textarea
              value={briefText}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setBriefText(e.target.value)}
              placeholder="Paste your Gemini Gem output here (e.g. 'Good morning, Counselor. Here is your 10-Day Nueces County Criminal Defense Deep-Dive Brief...')"
              className="w-full h-full min-h-[320px] font-mono text-xs leading-relaxed bg-slate-900/80 border border-cyan-500/20 rounded-xl text-slate-200 placeholder:text-slate-600 focus:outline-hidden focus:ring-1 focus:ring-cyan-500/40 resize-none p-3.5"
            />
          </div>

          <div className="border-t border-cyan-500/20 pt-3 flex flex-col sm:flex-row items-center justify-between gap-3">
            <p className="text-[11px] text-muted-foreground italic">
              Nothing is saved to database until you inspect and approve items on the Verification Board.
            </p>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => onOpenChange(false)}
                className="text-xs text-slate-400 hover:text-white"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={pasteMutation.isPending || !briefText.trim()}
                className="text-xs gap-1.5 bg-cyan-600 hover:bg-cyan-500 text-white font-medium shadow-sm shadow-cyan-900/40"
              >
                {pasteMutation.isPending ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    Parsing Brief…
                  </>
                ) : (
                  <>
                    <FileCheck2 className="h-3.5 w-3.5" />
                    Parse & Stage for Verification
                  </>
                )}
              </Button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
