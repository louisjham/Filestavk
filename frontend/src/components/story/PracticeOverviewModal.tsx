import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Sparkles,
  DollarSign,
  Users,
  ShieldCheck,
  Lock,
  ArrowRight,
  ArrowLeft,
  X,
  Scale,
  Clock,
  Mail,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react"
import { OctopusIcon } from "@/components/icons/OctopusIcon"

interface PracticeOverviewModalProps {
  isOpen: boolean
  onClose: () => void
}

export function PracticeOverviewModal({ isOpen, onClose }: PracticeOverviewModalProps) {
  const [currentSlide, setCurrentSlide] = useState(0)

  // Keyboard navigation (Arrow keys + Esc)
  useEffect(() => {
    if (!isOpen) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
      if (e.key === "ArrowRight") handleNext()
      if (e.key === "ArrowLeft") handlePrev()
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [isOpen, currentSlide])

  if (!isOpen) return null

  const slides = [
    {
      badge: "01 / PRACTICE CONTEXT",
      title: "The Solo Defense Reality in Corpus Christi",
      subtitle: "1 Lawyer &bull; 3 Teenagers &bull; High-Stakes Dockets",
      content: (
        <div className="space-y-4 text-sm text-foreground/90 leading-relaxed">
          <p>
            Running a solo criminal defense practice in Nueces County isn't like working at a 50-lawyer firm.
            Kimbel Brandon is in the courtroom daily across the 105th, 28th, 94th, 117th, 148th, 214th, and 347th District Courts.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
            <div className="p-3 rounded-lg bg-cyan-950/30 border border-cyan-500/30 space-y-1">
              <span className="font-bold text-cyan-300 text-xs block">⚡ The Feast &amp; Famine Cadence</span>
              <p className="text-xs text-muted-foreground">
                A sudden rush of activity at arrest &amp; bail, followed by 2–4 months of quiet waiting while clients sit in jail or on bond.
              </p>
            </div>
            <div className="p-3 rounded-lg bg-secondary/50 border border-border space-y-1">
              <span className="font-bold text-foreground text-xs block">⏳ Zero Spare Time</span>
              <p className="text-xs text-muted-foreground">
                Juggling 3 teenagers at home and clients in jail leaves zero patience for repetitive clerical data entry.
              </p>
            </div>
          </div>
        </div>
      ),
    },
    {
      badge: "02 / THE BOTTLENECK",
      title: "The Tyler Odyssey & Voucher Black Hole",
      subtitle: "No Search History &bull; The 30-Day Forfeiture Trap",
      content: (
        <div className="space-y-4 text-sm text-foreground/90 leading-relaxed">
          <p>
            The county indigent defense submission portal is a black box: once a voucher is sent, <strong>it cannot be searched or tracked on the website</strong>.
          </p>
          <div className="p-3.5 rounded-lg bg-red-500/10 border border-red-500/30 text-xs space-y-2">
            <div className="flex items-center gap-2 font-bold text-red-300">
              <AlertTriangle className="h-4 w-4 text-red-400" />
              The 30-Day Post-Disposition Forfeiture Rule (Art. 26.05 CCP)
            </div>
            <p className="text-muted-foreground leading-relaxed">
              If an attorney doesn't submit their voucher within 30 days of case disposition, the fee is <strong>permanently forfeited</strong>. Thousands of dollars in hard-earned revenue vanish simply because nobody was tracking the clock.
            </p>
          </div>
          <p className="text-xs text-muted-foreground">
            Voucher approvals and auditor warrant disbursements only exist as disparate notice emails sent to Kimbel's business inbox (<code className="text-cyan-300">info@hemocyaninlaw.com</code>).
          </p>
        </div>
      ),
    },
    {
      badge: "03 / THE HUMAN FACTOR",
      title: "The Assistant Rollercoaster",
      subtitle: "The Hiring &amp; Retraining Loop (And Why We Love Our Presenter)",
      content: (
        <div className="space-y-4 text-sm text-foreground/90 leading-relaxed">
          <p>
            Finding reliable assistants is tough. During quiet months, there isn't enough work to keep one full-time; when case volume spikes, you hire another and spend <strong>weeks retraining them from scratch</strong> on Tyler portal quirks and voucher billing formulas.
          </p>
          <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/30 text-xs space-y-2">
            <div className="font-bold text-amber-300 flex items-center gap-1.5">
              <span>☕</span> A Humorous Reality Check
            </div>
            <p className="text-muted-foreground leading-relaxed">
              Even with a brilliant assistant (like the one presenting this demo!), humans shouldn't have to spend 4 hours cross-referencing court minutes to type up an itemized invoice that software can generate in 1 second.
            </p>
          </div>
        </div>
      ),
    },
    {
      badge: "04 / ZERO-LEAK SECURITY",
      title: "The Scoped Assistant Persona ('asst')",
      subtitle: "Delegating Vouchers Without Exposing Private Emails",
      content: (
        <div className="space-y-4 text-sm text-foreground/90 leading-relaxed">
          <p>
            Kimbel wants assistants to crank out vouchers and pull court records—<strong>without handing over passwords to her personal inbox, private financials, or sensitive case notes</strong>.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
            <div className="p-3 rounded-lg bg-secondary/50 border border-border space-y-1">
              <span className="font-bold text-emerald-400 text-xs flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5" /> What the Assistant Sees
              </span>
              <ul className="text-xs text-muted-foreground space-y-0.5 list-disc pl-4">
                <li>1-Click Voucher Builder</li>
                <li>Nueces Odyssey Portal Assist</li>
                <li>Kimbel's Delegated Task Board</li>
                <li>Jail In-Custody Status</li>
              </ul>
            </div>
            <div className="p-3 rounded-lg bg-secondary/50 border border-border space-y-1">
              <span className="font-bold text-red-400 text-xs flex items-center gap-1.5">
                <Lock className="h-3.5 w-3.5" /> What Stays Locked
              </span>
              <ul className="text-xs text-muted-foreground space-y-0.5 list-disc pl-4">
                <li>Direct Gmail Inbox Credentials</li>
                <li>Private Attorney-Client Notes</li>
                <li>Firm Revenue &amp; Banking Setup</li>
                <li>Private Client Financials</li>
              </ul>
            </div>
          </div>
        </div>
      ),
    },
    {
      badge: "05 / THE SOLUTION",
      title: "The Hemocyanin Law Practice Engine",
      subtitle: "Autonomous &bull; Immutable &bull; Calm",
      content: (
        <div className="space-y-4 text-sm text-foreground/90 leading-relaxed">
          <div className="space-y-2">
            <div className="flex items-start gap-2.5">
              <div className="h-5 w-5 rounded-full bg-cyan-500/20 text-cyan-300 flex items-center justify-center shrink-0 mt-0.5 font-bold text-xs">1</div>
              <div>
                <strong className="text-foreground text-xs block">1-Click Docket-to-Voucher Builder</strong>
                <span className="text-xs text-muted-foreground">Turns raw court appearances into itemized Texas Art. 26.05 fee claims in seconds.</span>
              </div>
            </div>

            <div className="flex items-start gap-2.5">
              <div className="h-5 w-5 rounded-full bg-cyan-500/20 text-cyan-300 flex items-center justify-center shrink-0 mt-0.5 font-bold text-xs">2</div>
              <div>
                <strong className="text-foreground text-xs block">Immutable Static Notice Capture</strong>
                <span className="text-xs text-muted-foreground">County notices are parsed once into SQLite and locked—no live Gmail crawling needed.</span>
              </div>
            </div>

            <div className="flex items-start gap-2.5">
              <div className="h-5 w-5 rounded-full bg-cyan-500/20 text-cyan-300 flex items-center justify-center shrink-0 mt-0.5 font-bold text-xs">3</div>
              <div>
                <strong className="text-foreground text-xs block">Nueces County Jail Priority Radar</strong>
                <span className="text-xs text-muted-foreground">Actively counts days in custody to trigger bond reduction motions during the pre-trial lull.</span>
              </div>
            </div>
          </div>

          <div className="p-3 bg-cyan-950/40 border border-cyan-500/40 rounded-lg text-center text-xs text-cyan-200 font-medium">
            🎯 Result: Consistently recover thousands in voucher revenue monthly with zero assistant churn.
          </div>
        </div>
      ),
    },
  ]

  const handleNext = () => {
    if (currentSlide < slides.length - 1) {
      setCurrentSlide(currentSlide + 1)
    } else {
      onClose()
    }
  }

  const handlePrev = () => {
    if (currentSlide > 0) {
      setCurrentSlide(currentSlide - 1)
    }
  }

  const slide = slides[currentSlide]

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 animate-fadeIn">
      <div className="bg-gradient-to-b from-slate-900 via-slate-900 to-cyan-950/60 border border-cyan-500/30 rounded-2xl max-w-2xl w-full shadow-2xl overflow-hidden flex flex-col">
        {/* Modal Top Bar */}
        <div className="p-4 px-6 border-b border-border/80 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-2.5">
            <div className="h-7 w-7 rounded-full bg-cyan-950/80 border border-cyan-500/40 flex items-center justify-center">
              <OctopusIcon size={16} className="text-cyan-400" />
            </div>
            <div>
              <span className="text-xs font-bold text-foreground block leading-none">
                Filestavk &bull; Hemocyanin Law
              </span>
              <span className="text-[10px] text-cyan-300/80">
                Space-Level Practice Architecture
              </span>
            </div>
          </div>

          <Button variant="ghost" size="icon" onClick={onClose} className="h-7 w-7 text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Slide Body */}
        <div className="p-6 sm:p-8 flex-1 space-y-4">
          <div className="space-y-1">
            <Badge variant="outline" className="text-[10px] text-cyan-300 border-cyan-500/30 bg-cyan-950/40 tracking-wider">
              {slide.badge}
            </Badge>
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
              {slide.title}
            </h2>
            <p className="text-xs font-medium text-cyan-400">
              {slide.subtitle}
            </p>
          </div>

          <div className="pt-2 min-h-[220px]">
            {slide.content}
          </div>
        </div>

        {/* Modal Footer with Slide Stepper & Controls */}
        <div className="p-4 px-6 border-t border-border/80 bg-slate-950/80 flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            {slides.map((_, idx) => (
              <button
                key={idx}
                onClick={() => setCurrentSlide(idx)}
                className={`h-2 rounded-full transition-all ${
                  idx === currentSlide ? "w-6 bg-cyan-400" : "w-2 bg-muted-foreground/30 hover:bg-muted-foreground/60"
                }`}
                title={`Go to slide ${idx + 1}`}
              />
            ))}
          </div>

          <div className="flex items-center gap-2">
            {currentSlide > 0 && (
              <Button variant="outline" size="sm" onClick={handlePrev} className="text-xs gap-1 border-border">
                <ArrowLeft className="h-3.5 w-3.5" /> Previous
              </Button>
            )}

            <Button
              size="sm"
              onClick={handleNext}
              className="text-xs gap-1.5 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold shadow-md"
            >
              {currentSlide === slides.length - 1 ? (
                <>
                  Explore App <CheckCircle2 className="h-3.5 w-3.5" />
                </>
              ) : (
                <>
                  Next <ArrowRight className="h-3.5 w-3.5" />
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
