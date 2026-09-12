import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  ClipboardList,
  CheckCircle2,
  Clock,
  ArrowRight,
  AlertTriangle,
  MessageSquare,
  Sparkles,
  User,
  Scale,
  DollarSign,
} from "lucide-react"

export function KimbelDelegationCard() {
  const queryClient = useQueryClient()

  const { data: tasks, isLoading } = useQuery({
    queryKey: ["delegated-tasks"],
    queryFn: () => api.settings.getDelegatedTasks(),
  })

  const completeMutation = useMutation({
    mutationFn: ({ taskId, status }: { taskId: string; status: string }) =>
      api.settings.updateDelegatedTask(taskId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["delegated-tasks"] })
    },
  })

  const pendingTasks = tasks?.filter((t: any) => t.status === "PENDING") || []
  const completedTasks = tasks?.filter((t: any) => t.status === "COMPLETED") || []

  return (
    <Card className="border-cyan-500/40 bg-gradient-to-b from-card to-cyan-950/10 shadow-sm">
      <CardHeader className="pb-3 border-b border-border">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <CardTitle className="text-base flex items-center gap-2 text-foreground">
              <ClipboardList className="h-4 w-4 text-cyan-400" />
              Kimbel's Delegation Board &bull; Assistant Work Queue
            </CardTitle>
            <CardDescription className="text-xs">
              Direct tasks delegated by Kimbel Brandon from her morning briefing. Execute vouchers and dockets with 1 click.
            </CardDescription>
          </div>
          <Badge variant="outline" className="text-[10px] text-cyan-300 border-cyan-500/40 bg-cyan-950/40">
            {pendingTasks.length} Active Tasks
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="p-4 space-y-3">
        {isLoading ? (
          <div className="p-6 text-center text-xs text-muted-foreground">Loading delegated tasks...</div>
        ) : pendingTasks.length > 0 ? (
          <div className="space-y-3">
            {pendingTasks.map((t: any) => (
              <div
                key={t.id}
                className="p-3.5 rounded-lg border border-border/80 bg-secondary/40 hover:bg-secondary/60 transition-colors space-y-2 text-xs"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-foreground">{t.title}</span>
                      <Badge
                        variant={t.priority === "URGENT" ? "destructive" : t.priority === "HIGH" ? "warning" : "info"}
                        className="text-[10px] px-1.5 py-0"
                      >
                        {t.priority}
                      </Badge>
                    </div>
                    <span className="text-[11px] text-cyan-300/90 font-medium">
                      {t.due_notice}
                    </span>
                  </div>

                  {t.amount_estimate > 0 && (
                    <span className="text-xs font-bold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/30 shrink-0">
                      ${t.amount_estimate.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                    </span>
                  )}
                </div>

                {/* Kimbel's Note Box */}
                <div className="p-2.5 rounded bg-cyan-950/30 border border-cyan-500/20 text-[11px] text-muted-foreground flex items-start gap-2">
                  <MessageSquare className="h-3.5 w-3.5 text-cyan-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-cyan-300 block">Note from Kimbel:</span>
                    <p className="italic text-foreground/90 leading-relaxed">"{t.kimbel_note}"</p>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center justify-between pt-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-[11px] h-7 px-2 text-muted-foreground hover:text-emerald-400"
                    onClick={() => completeMutation.mutate({ taskId: t.id, status: "COMPLETED" })}
                  >
                    <CheckCircle2 className="h-3.5 w-3.5 mr-1" /> Mark Done
                  </Button>

                  <Button asChild size="sm" className="text-xs h-7 gap-1 bg-primary font-medium">
                    <Link to={t.link}>
                      Open &amp; Execute <ArrowRight className="h-3 w-3" />
                    </Link>
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-6 text-center text-xs text-muted-foreground space-y-1">
            <CheckCircle2 className="h-6 w-6 mx-auto text-emerald-400" />
            <p className="font-medium text-foreground">All delegated tasks completed!</p>
            <p className="text-[11px]">Kimbel will dispatch new tasks as dockets and notices arrive.</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
