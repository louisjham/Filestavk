import { Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg"
  className?: string
  text?: string
}

export function LoadingSpinner({ size = "md", className, text }: LoadingSpinnerProps) {
  const sizeMap = { sm: "h-4 w-4", md: "h-6 w-6", lg: "h-10 w-10" }
  return (
    <div className={cn("flex items-center justify-center gap-2 text-muted-foreground", className)}>
      <Loader2 className={cn("animate-spin", sizeMap[size])} />
      {text && <span className="text-sm">{text}</span>}
    </div>
  )
}

export function PageLoader() {
  return (
    <div className="flex h-64 items-center justify-center">
      <LoadingSpinner size="lg" text="Loading…" />
    </div>
  )
}
