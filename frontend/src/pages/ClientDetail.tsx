import { useState } from "react"
import { useParams, Link } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  User,
  Phone,
  Mail,
  MapPin,
  Scale,
  Plus,
  ArrowRight,
  FileText,
  Download,
  Copy,
  Check,
  Edit,
  Lock,
  Calendar,
  AlertTriangle,
  X,
  CheckCircle2,
  ShieldCheck,
} from "lucide-react"
import { formatDate, formatPhoneNumber, isValidEmail } from "@/lib/utils"
import { ClassificationBadge } from "@/components/shared/ClassificationBadge"

export function ClientDetail() {
  const { id } = useParams()
  const clientId = Number(id)
  const queryClient = useQueryClient()

  const [copiedField, setCopiedField] = useState<string | null>(null)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [editSuccessNotice, setEditSuccessNotice] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  // Edit form state
  const [editName, setEditName] = useState("")
  const [editPhone, setEditPhone] = useState("")
  const [editEmail, setEditEmail] = useState("")
  const [editAddress, setEditAddress] = useState("")
  const [editDob, setEditDob] = useState("")
  const [editNotes, setEditNotes] = useState("")
  const [editInCustody, setEditInCustody] = useState(false)

  const { data: client, isLoading } = useQuery({
    queryKey: ["client", clientId],
    queryFn: () => api.clients.get(clientId),
    enabled: !isNaN(clientId),
  })

  const { data: allCases } = useQuery({
    queryKey: ["cases"],
    queryFn: () => api.cases.list(),
  })

  const { data: clientDocuments } = useQuery({
    queryKey: ["client-documents", clientId],
    queryFn: () => api.documents.list({ client_id: clientId }),
    enabled: !isNaN(clientId),
  })

  const clientCases = allCases?.filter((c: any) => c.client_id === clientId) || []
  const isInCustody = Boolean(client?.is_in_custody || clientCases.some((c: any) => c.in_custody))
  const inCustodyCase = clientCases.find((c: any) => c.in_custody)

  // Open Edit Modal with current values
  const handleOpenEditModal = () => {
    if (!client) return
    setFormError(null)
    setEditName(client.name || "")
    setEditPhone(formatPhoneNumber(client.phone || ""))
    setEditEmail(client.email || "")
    setEditAddress(client.address || "")
    setEditDob(client.dob || "")
    setEditNotes(client.notes || "")
    setEditInCustody(isInCustody)
    setIsEditModalOpen(true)
  }

  // Update Client Mutation
  const updateMutation = useMutation({
    mutationFn: (payload: any) => api.clients.update(clientId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["client", clientId] })
      queryClient.invalidateQueries({ queryKey: ["clients"] })
      queryClient.invalidateQueries({ queryKey: ["cases"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard-alerts"] })
      setIsEditModalOpen(false)
      setEditSuccessNotice("Client information updated successfully.")
      setTimeout(() => setEditSuccessNotice(null), 4000)
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || err.message || "Failed to update client profile."
      setFormError(typeof msg === "string" ? msg : JSON.stringify(msg))
    },
  })

  const handleSaveEdit = (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    if (!editName.trim()) {
      setFormError("Client name cannot be empty.")
      return
    }

    let cleanedPhone: string | null = null
    if (editPhone.trim()) {
      const digits = editPhone.replace(/\D/g, "")
      const norm = digits.length === 11 && digits.startsWith("1") ? digits.slice(1) : digits
      if (norm.length !== 10) {
        setFormError("Phone number must have exactly 10 digits in format (XXX) XXX-XXXX.")
        return
      }
      cleanedPhone = `(${norm.slice(0, 3)}) ${norm.slice(3, 6)}-${norm.slice(6, 10)}`
    }

    let cleanedEmail: string | null = null
    if (editEmail.trim()) {
      if (!isValidEmail(editEmail)) {
        setFormError("Please enter a valid email address (e.g. client@gmail.com).")
        return
      }
      cleanedEmail = editEmail.trim().toLowerCase()
    }

    updateMutation.mutate({
      name: editName.trim(),
      phone: cleanedPhone,
      email: cleanedEmail,
      address: editAddress.trim() || null,
      dob: editDob.trim() || null,
      notes: editNotes.trim() || null,
      in_custody: editInCustody,
    })
  }

  // Click-to-Copy Handler with vanishing notification
  const handleCopy = (value: string | null | undefined, label: string) => {
    if (!value || value === "—" || value.trim() === "") return
    navigator.clipboard.writeText(value)
    setCopiedField(label)
    setTimeout(() => {
      setCopiedField((curr) => (curr === label ? null : curr))
    }, 1600)
  }

  if (isLoading) {
    return <div className="p-8 text-center text-muted-foreground text-xs">Loading client profile...</div>
  }

  if (!client) {
    return (
      <div className="p-8 text-center text-muted-foreground space-y-4">
        <p>Client profile not found.</p>
        <Button asChild variant="outline">
          <Link to="/clients">Back to Clients</Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Top Breadcrumb & Action Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Button asChild variant="ghost" size="sm" className="h-7 text-xs text-muted-foreground hover:text-foreground px-2">
            <Link to="/clients">&larr; All Clients</Link>
          </Button>
          <span className="text-muted-foreground text-xs">/</span>
          <span className="text-xs font-semibold text-foreground">{client.name}</span>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={handleOpenEditModal}
            className="gap-1.5 bg-primary hover:bg-primary/90 text-primary-foreground text-xs shadow-xs"
          >
            <Edit className="h-3.5 w-3.5" />
            Edit Client's Info
          </Button>
          <Button asChild size="sm" variant="outline" className="text-xs gap-1.5">
            <Link to={`/documents?client_id=${clientId}`}>
              <FileText className="h-3.5 w-3.5 text-blue-400" />
              Upload Document
            </Link>
          </Button>
          <Button asChild size="sm" className="bg-blue-600 hover:bg-blue-700 text-white gap-1.5 text-xs">
            <Link to="/ingestion/portal">
              <Scale className="h-3.5 w-3.5" />
              Lookup Records
            </Link>
          </Button>
        </div>
      </div>

      {/* Success Notification Banner */}
      {editSuccessNotice && (
        <div className="p-3.5 bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 rounded-lg text-xs flex items-center justify-between animate-fadeIn">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
            <span>{editSuccessNotice}</span>
          </div>
          <Button size="sm" variant="ghost" onClick={() => setEditSuccessNotice(null)} className="h-6 text-xs text-emerald-200">
            Dismiss
          </Button>
        </div>
      )}

      {/* Prominent Custody / In-Jail Status Banner */}
      {isInCustody ? (
        <div className="p-4 bg-red-500/15 border-2 border-red-500/60 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-red-200 shadow-sm animate-fadeIn">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-red-500/20 text-red-400 shrink-0">
              <Lock className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold tracking-wide uppercase text-red-300">
                  Currently Incarcerated in Jail
                </span>
                <Badge variant="destructive" className="bg-red-500/30 text-red-200 border-red-500/50 text-[10px] font-mono">
                  IN CUSTODY
                </Badge>
              </div>
              <p className="text-xs text-red-200/90 mt-0.5">
                Detained at <strong>{inCustodyCase?.jail_facility || "Nueces County Jail - Main"}</strong>. Subject to Art. 17.151 CCP 90-day speedy trial / bail reduction requirements.
              </p>
            </div>
          </div>
          <Button asChild size="sm" variant="outline" className="shrink-0 text-xs border-red-500/40 text-red-200 hover:bg-red-500/20">
            <Link to={inCustodyCase ? `/cases/${inCustodyCase.id}` : "/cases"}>
              Review Bond &amp; Custody
            </Link>
          </Button>
        </div>
      ) : (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg flex items-center justify-between text-xs text-emerald-300">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            <span><strong>Client Status:</strong> Out of Custody / Bonded Out</span>
          </div>
          <span className="text-[11px] text-emerald-400/80">No active jail holds recorded</span>
        </div>
      )}

      {/* Main Client Profile Card with Click-to-Copy Fields */}
      <Card className="border-border bg-card">
        <CardHeader className="pb-3 border-b border-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-primary/10 text-primary">
                <User className="h-6 w-6" />
              </div>
              <div>
                <div className="flex items-center gap-2.5">
                  <h1 className="text-2xl font-bold tracking-tight text-foreground">{client.name}</h1>
                  <Badge variant="outline" className="text-xs font-mono">ID #{client.id}</Badge>
                  {isInCustody ? (
                    <Badge variant="destructive" className="bg-red-500/20 text-red-300 border-red-500/40 font-bold text-[10px] gap-1">
                      <Lock className="h-2.5 w-2.5" />
                      IN JAIL
                    </Badge>
                  ) : (
                    <Badge variant="success" className="text-[10px]">
                      BONDED OUT
                    </Badge>
                  )}
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Click any field below to copy to clipboard &bull; {clientCases.length} case{clientCases.length === 1 ? "" : "s"} on docket
                </p>
              </div>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={handleOpenEditModal}
              className="text-xs gap-1.5 h-8"
            >
              <Edit className="h-3.5 w-3.5" />
              Edit Info
            </Button>
          </div>
        </CardHeader>

        <CardContent className="p-6">
          {/* Clickable Fields Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Phone Number */}
            <button
              type="button"
              onClick={() => handleCopy(client.phone, "Phone")}
              className="relative p-3.5 rounded-lg border border-border/80 bg-muted/20 hover:bg-muted/40 hover:border-primary/50 transition-all text-left group cursor-pointer focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                <span className="flex items-center gap-1.5 font-medium">
                  <Phone className="h-3.5 w-3.5 text-primary" />
                  Contact Phone
                </span>
                {copiedField === "Phone" ? (
                  <span className="text-[11px] font-bold text-emerald-400 flex items-center gap-1 animate-fadeIn">
                    <Check className="h-3 w-3" /> Copied!
                  </span>
                ) : (
                  <Copy className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground" />
                )}
              </div>
              <div className="font-mono text-sm font-semibold text-foreground truncate">
                {client.phone || <span className="text-muted-foreground italic font-normal text-xs">Not provided — Click edit</span>}
              </div>
            </button>

            {/* Email Address */}
            <button
              type="button"
              onClick={() => handleCopy(client.email, "Email")}
              className="relative p-3.5 rounded-lg border border-border/80 bg-muted/20 hover:bg-muted/40 hover:border-primary/50 transition-all text-left group cursor-pointer focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                <span className="flex items-center gap-1.5 font-medium">
                  <Mail className="h-3.5 w-3.5 text-primary" />
                  Client Email
                </span>
                {copiedField === "Email" ? (
                  <span className="text-[11px] font-bold text-emerald-400 flex items-center gap-1 animate-fadeIn">
                    <Check className="h-3 w-3" /> Copied!
                  </span>
                ) : (
                  <Copy className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground" />
                )}
              </div>
              <div className="font-mono text-sm font-semibold text-foreground truncate">
                {client.email || <span className="text-muted-foreground italic font-normal text-xs">Not provided — Click edit</span>}
              </div>
            </button>

            {/* Date of Birth */}
            <button
              type="button"
              onClick={() => handleCopy(client.dob, "DOB")}
              className="relative p-3.5 rounded-lg border border-border/80 bg-muted/20 hover:bg-muted/40 hover:border-primary/50 transition-all text-left group cursor-pointer focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                <span className="flex items-center gap-1.5 font-medium">
                  <Calendar className="h-3.5 w-3.5 text-primary" />
                  Date of Birth
                </span>
                {copiedField === "DOB" ? (
                  <span className="text-[11px] font-bold text-emerald-400 flex items-center gap-1 animate-fadeIn">
                    <Check className="h-3 w-3" /> Copied!
                  </span>
                ) : (
                  <Copy className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground" />
                )}
              </div>
              <div className="font-mono text-sm font-semibold text-foreground truncate">
                {client.dob || <span className="text-muted-foreground italic font-normal text-xs">Not provided</span>}
              </div>
            </button>

            {/* Custody / Jail Status */}
            <button
              type="button"
              onClick={() => handleCopy(isInCustody ? "In Jail (Nueces County Jail)" : "Out of Custody", "Custody")}
              className="relative p-3.5 rounded-lg border border-border/80 bg-muted/20 hover:bg-muted/40 hover:border-primary/50 transition-all text-left group cursor-pointer focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                <span className="flex items-center gap-1.5 font-medium">
                  <Lock className="h-3.5 w-3.5 text-primary" />
                  Custody Status
                </span>
                {copiedField === "Custody" ? (
                  <span className="text-[11px] font-bold text-emerald-400 flex items-center gap-1 animate-fadeIn">
                    <Check className="h-3 w-3" /> Copied!
                  </span>
                ) : (
                  <Copy className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground" />
                )}
              </div>
              <div className="text-sm font-semibold truncate flex items-center gap-1.5">
                {isInCustody ? (
                  <span className="text-red-400 font-bold flex items-center gap-1">
                    <Lock className="h-3.5 w-3.5" /> In Jail (Nueces Co.)
                  </span>
                ) : (
                  <span className="text-emerald-400 font-medium">Out of Custody</span>
                )}
              </div>
            </button>

            {/* Address — spans 3 columns on desktop */}
            <button
              type="button"
              onClick={() => handleCopy(client.address, "Address")}
              className="sm:col-span-2 lg:col-span-3 relative p-3.5 rounded-lg border border-border/80 bg-muted/20 hover:bg-muted/40 hover:border-primary/50 transition-all text-left group cursor-pointer focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                <span className="flex items-center gap-1.5 font-medium">
                  <MapPin className="h-3.5 w-3.5 text-primary" />
                  Residential Address
                </span>
                {copiedField === "Address" ? (
                  <span className="text-[11px] font-bold text-emerald-400 flex items-center gap-1 animate-fadeIn">
                    <Check className="h-3 w-3" /> Copied!
                  </span>
                ) : (
                  <Copy className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground" />
                )}
              </div>
              <div className="text-sm font-semibold text-foreground truncate">
                {client.address || "Corpus Christi, TX"}
              </div>
            </button>

            {/* Total Documents */}
            <div className="p-3.5 rounded-lg border border-border/80 bg-muted/20 flex flex-col justify-center">
              <span className="text-xs text-muted-foreground font-medium flex items-center gap-1.5">
                <FileText className="h-3.5 w-3.5 text-primary" />
                Total Case Files
              </span>
              <div className="text-sm font-bold text-foreground mt-1">
                {clientDocuments?.length || 0} Document{clientDocuments?.length === 1 ? "" : "s"}
              </div>
            </div>
          </div>

          {/* Client Notes */}
          {client.notes && (
            <div className="mt-4 p-3 bg-muted/30 rounded-lg border border-border/60 text-xs text-muted-foreground flex items-start gap-2">
              <span className="font-semibold text-foreground shrink-0">Notes:</span>
              <span className="italic">{client.notes}</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Linked Cases Section — Detailed At-a-Glance Docket */}
      <Card>
        <CardHeader className="pb-3 border-b border-border">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base flex items-center gap-2 text-foreground">
                <Scale className="h-4 w-4 text-primary" />
                Linked Cases &amp; Offense Docket ({clientCases.length})
              </CardTitle>
              <CardDescription className="text-xs">
                At-a-glance status, offense descriptions, courts, custody flags, and statutory stage lifecycle.
              </CardDescription>
            </div>
            <Button asChild size="sm" variant="outline" className="text-xs h-7 gap-1">
              <Link to="/cases">All Firm Cases &rarr;</Link>
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {clientCases.length > 0 ? (
            <div className="divide-y divide-border text-xs">
              {clientCases.map((c: any) => {
                const caseDocs = clientDocuments?.filter((d: any) => d.case_id === c.id) || []
                return (
                  <div key={c.id} className="p-5 space-y-3 hover:bg-muted/10 transition-colors">
                    {/* Header Row: Case #, Custody, Stage, Action */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div className="space-y-1.5">
                        {/* Status Badges Row */}
                        <div className="flex flex-wrap items-center gap-2">
                          <Link to={`/cases/${c.id}`} className="font-bold text-primary font-mono text-base hover:underline flex items-center gap-1.5">
                            #{c.case_number}
                          </Link>

                          {/* IN JAIL or OUT ON BOND */}
                          {c.in_custody ? (
                            <Badge variant="destructive" className="bg-red-500/20 text-red-300 border-red-500/40 text-xs font-bold gap-1 flex items-center">
                              <Lock className="h-3 w-3" />
                              IN JAIL
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="text-emerald-400 border-emerald-500/30 text-xs font-medium">
                              OUT ON BOND
                            </Badge>
                          )}

                          {/* Lifecycle Stage Badge */}
                          <Badge variant={c.status === "OPEN" || c.status === "open" ? "info" : c.status === "DISPOSED" ? "warning" : "success"}>
                            {c.stage || c.status}
                          </Badge>

                          {/* CJA Appointed */}
                          {c.is_cja && <Badge variant="purple">CJA Appointed</Badge>}

                          {/* Order / Acceptance Statutory Status */}
                          {c.has_appointment_acceptance ? (
                            <Badge variant="success" className="text-[10px]">
                              Acceptance Filed &bull; Billable
                            </Badge>
                          ) : c.has_appointment_order ? (
                            <Badge variant="warning" className="text-[10px] border-amber-500/40 bg-amber-500/20 text-amber-300">
                              Awaiting Acceptance
                            </Badge>
                          ) : null}
                        </div>

                        {/* Offense & Court */}
                        <div className="text-sm font-semibold text-foreground">
                          {c.charge_description || c.case_type || "Criminal Offense"}
                        </div>
                        <div className="text-muted-foreground text-xs flex flex-wrap items-center gap-2">
                          <span><strong>Court:</strong> {c.court || "Nueces County Court"}</span>
                          {c.judge && <span>&bull; <strong>Judge:</strong> {c.judge}</span>}
                          {c.bond_amount && (
                            <span>&bull; <strong>Bond:</strong> ${c.bond_amount.toLocaleString()} ({c.bond_type || "SURETY"})</span>
                          )}
                        </div>
                      </div>

                      <div className="shrink-0 flex items-center gap-2">
                        {c.has_appointment_order && !c.has_appointment_acceptance && (
                          <Button asChild size="sm" variant="outline" className="h-8 text-xs border-amber-500/40 text-amber-300 hover:bg-amber-500/10">
                            <Link to={`/documents?case_id=${c.id}`}>
                              Upload Acceptance
                            </Link>
                          </Button>
                        )}
                        <Button asChild size="sm" className="h-8 text-xs font-semibold">
                          <Link to={`/cases/${c.id}`}>
                            Open Case File
                            <ArrowRight className="h-3.5 w-3.5 ml-1" />
                          </Link>
                        </Button>
                      </div>
                    </div>

                    {/* Hierarchy: Attached Documents Under this Case */}
                    {caseDocs.length > 0 && (
                      <div className="bg-muted/30 rounded-lg p-3 border border-border/60 mt-2 space-y-2">
                        <div className="text-[11px] font-semibold text-muted-foreground flex items-center gap-1.5 uppercase tracking-wider">
                          <FileText className="h-3.5 w-3.5 text-blue-400" />
                          Attached Case Documents ({caseDocs.length})
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                          {caseDocs.map((doc: any) => (
                            <div key={doc.id} className="bg-background/80 p-2.5 rounded border border-border/60 flex items-center justify-between gap-2">
                              <div className="min-w-0">
                                <div className="font-medium text-foreground text-xs truncate flex items-center gap-1.5">
                                  <FileText className="h-3 w-3 text-primary shrink-0" />
                                  <span className="truncate">{doc.filename}</span>
                                </div>
                                <div className="text-[10px] text-muted-foreground mt-0.5">
                                  {doc.doc_type?.toUpperCase()} &bull; {formatDate(doc.created_at)}
                                </div>
                              </div>
                              <div className="flex items-center gap-1.5 shrink-0">
                                <ClassificationBadge label={doc.classification_label} confidence={doc.classification_confidence} />
                                <Button asChild size="icon" variant="ghost" className="h-6 w-6">
                                  <a href={api.documents.getFileUrl(doc.id)} target="_blank" rel="noreferrer" title="Download Document">
                                    <Download className="h-3 w-3 text-muted-foreground hover:text-foreground" />
                                  </a>
                                </Button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="p-8 text-center text-muted-foreground text-xs">
              No cases linked to this client yet.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Orphaned Documents — attached to client but not yet linked to a case */}
      {(() => {
        const orphanDocs = clientDocuments?.filter((d: any) => d.case_id === null) || []
        if (orphanDocs.length === 0) return null
        return (
          <Card>
            <CardHeader className="pb-3 border-b border-border">
              <CardTitle className="text-base flex items-center gap-2">
                <FileText className="h-4 w-4 text-amber-400" />
                Client-Level Documents (Not Yet Linked to a Case)
                <Badge variant="warning" className="text-[10px]">{orphanDocs.length}</Badge>
              </CardTitle>
              <p className="text-[11px] text-muted-foreground mt-1">
                These documents are attached to this client but haven't been matched to a case number yet. Review and link them via the Documents page.
              </p>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-border/60 text-xs">
                {orphanDocs.map((doc: any) => (
                  <div key={doc.id} className="p-4 flex items-center justify-between gap-3 hover:bg-muted/10 transition-colors">
                    <div className="min-w-0 flex items-center gap-2">
                      <FileText className="h-3.5 w-3.5 text-primary shrink-0" />
                      <div>
                        <div className="font-medium text-foreground truncate">{doc.filename}</div>
                        <div className="text-[10px] text-muted-foreground">
                          {doc.doc_type?.toUpperCase()} &bull; Ingested {formatDate(doc.created_at)}
                        </div>
                      </div>
                    </div>
                    <Button asChild size="icon" variant="ghost" className="h-7 w-7 shrink-0">
                      <a href={`/api/documents/${doc.id}/file`} target="_blank" rel="noreferrer" title="Download">
                        <Download className="h-3.5 w-3.5 text-muted-foreground" />
                      </a>
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )
      })()}

      {/* Edit Client's Info Modal Overlay */}
      {isEditModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4 backdrop-blur-xs animate-fadeIn">
          <Card className="w-full max-w-lg bg-card border-border shadow-xl">
            <CardHeader className="pb-3 border-b border-border flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-base flex items-center gap-2">
                  <Edit className="h-4 w-4 text-primary" />
                  Edit Client Information
                </CardTitle>
                <CardDescription className="text-xs">
                  Update contact info, address, DOB, and jail custody status.
                </CardDescription>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setIsEditModalOpen(false)}
                className="h-7 w-7 rounded-full text-muted-foreground hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </Button>
            </CardHeader>

            <form onSubmit={handleSaveEdit}>
              <CardContent className="p-6 space-y-4 text-xs">
                {/* Form Validation Error Banner */}
                {formError && (
                  <div className="p-3 rounded-lg bg-red-500/15 border border-red-500/40 text-red-300 text-xs flex items-center gap-2 animate-fadeIn">
                    <AlertTriangle className="h-4 w-4 shrink-0 text-red-400" />
                    <span>{formError}</span>
                  </div>
                )}

                {/* Full Name */}
                <div className="space-y-1.5">
                  <Label htmlFor="edit-name" className="text-xs font-medium">Full Legal Name *</Label>
                  <Input
                    id="edit-name"
                    value={editName}
                    onChange={(e) => {
                      setFormError(null)
                      setEditName(e.target.value)
                    }}
                    required
                    placeholder="e.g. Desiree Dennis"
                    className="h-8 text-xs"
                  />
                </div>

                {/* Contact Phone & Email */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="edit-phone" className="text-xs font-medium">Phone Number</Label>
                      <span className="text-[10px] text-muted-foreground">(XXX) XXX-XXXX</span>
                    </div>
                    <Input
                      id="edit-phone"
                      value={editPhone}
                      onChange={(e) => {
                        setFormError(null)
                        setEditPhone(formatPhoneNumber(e.target.value))
                      }}
                      placeholder="(361) 555-0100"
                      className="h-8 text-xs font-mono"
                      maxLength={14}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="edit-email" className="text-xs font-medium">Client Email</Label>
                    <Input
                      id="edit-email"
                      type="text"
                      value={editEmail}
                      onChange={(e) => {
                        setFormError(null)
                        setEditEmail(e.target.value)
                      }}
                      placeholder="client@gmail.com"
                      className={`h-8 text-xs font-mono ${
                        editEmail.trim() && !isValidEmail(editEmail) ? "border-red-500/80 focus:ring-red-500/50" : ""
                      }`}
                    />
                    {editEmail.trim() && !isValidEmail(editEmail) && (
                      <p className="text-[10px] text-red-400">Invalid format (expected user@domain.tld)</p>
                    )}
                  </div>
                </div>

                {/* Address & DOB */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label htmlFor="edit-dob" className="text-xs font-medium">Date of Birth</Label>
                    <Input
                      id="edit-dob"
                      value={editDob}
                      onChange={(e) => setEditDob(e.target.value)}
                      placeholder="MM/DD/YYYY"
                      className="h-8 text-xs"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="edit-address" className="text-xs font-medium">Residential Address</Label>
                    <Input
                      id="edit-address"
                      value={editAddress}
                      onChange={(e) => setEditAddress(e.target.value)}
                      placeholder="e.g. 4809 Calallen Dr, Corpus Christi TX"
                      className="h-8 text-xs"
                    />
                  </div>
                </div>

                {/* In Custody / Jail Toggle */}
                <div className="p-3 rounded-lg border border-border bg-muted/20 flex items-center justify-between gap-3">
                  <div className="space-y-0.5">
                    <div className="font-semibold text-foreground flex items-center gap-1.5">
                      <Lock className="h-3.5 w-3.5 text-red-400" />
                      Currently Detained in Jail
                    </div>
                    <div className="text-[11px] text-muted-foreground">
                      Flags client as incarcerated across the entire app and dashboard.
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    id="edit-custody"
                    checked={editInCustody}
                    onChange={(e) => setEditInCustody(e.target.checked)}
                    className="h-4 w-4 rounded border-border text-primary focus:ring-primary accent-primary cursor-pointer"
                  />
                </div>

                {/* Notes */}
                <div className="space-y-1.5">
                  <Label htmlFor="edit-notes" className="text-xs font-medium">Case &amp; Representation Notes</Label>
                  <textarea
                    id="edit-notes"
                    value={editNotes}
                    onChange={(e) => setEditNotes(e.target.value)}
                    rows={3}
                    placeholder="Add any specific representation notes or reminders..."
                    className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-xs shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  />
                </div>
              </CardContent>

              <div className="p-4 border-t border-border flex items-center justify-end gap-2 bg-muted/10">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setIsEditModalOpen(false)}
                  className="text-xs"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={updateMutation.isPending}
                  className="text-xs bg-primary hover:bg-primary/90"
                >
                  {updateMutation.isPending ? "Saving..." : "Save Changes"}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}
    </div>
  )
}
