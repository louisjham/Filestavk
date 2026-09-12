import { Badge } from "@/components/ui/badge"

const LABEL_MAP: Record<string, { label: string; variant: "destructive" | "info" | "purple" | "success" | "sky" | "orange" | "warning" | "teal" | "muted" }> = {
  court_order:      { label: "Court Order",      variant: "destructive" },
  pleading:         { label: "Pleading",          variant: "info" },
  discovery:        { label: "Discovery",         variant: "purple" },
  correspondence:   { label: "Correspondence",    variant: "success" },
  email:            { label: "Email",             variant: "sky" },
  police_report:    { label: "Police Report",     variant: "orange" },
  invoice:          { label: "Invoice",           variant: "warning" },
  voucher_support:  { label: "Voucher Support",   variant: "teal" },
  uncategorized:    { label: "Uncategorized",     variant: "muted" },
}

interface ClassificationBadgeProps {
  label: string | null | undefined
  confidence?: number | null
}

export function ClassificationBadge({ label, confidence }: ClassificationBadgeProps) {
  const key = label?.toLowerCase() ?? "uncategorized"
  const mapping = LABEL_MAP[key] ?? { label: label ?? "Unknown", variant: "muted" as const }
  const pct = confidence != null ? ` ${Math.round(confidence * 100)}%` : ""

  return (
    <Badge variant={mapping.variant}>
      {mapping.label}{pct}
    </Badge>
  )
}
