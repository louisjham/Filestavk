import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Users, Plus, Search, Phone, Mail, MapPin, ArrowRight, User, Sparkles, Trash2, CheckCircle2, Scale, Lock, AlertTriangle } from "lucide-react"
import { formatDate, formatPhoneNumber, isValidEmail } from "@/lib/utils"

export function Clients() {
  const queryClient = useQueryClient()
  const [searchTerm, setSearchTerm] = useState("")
  const [isCreating, setIsCreating] = useState(false)
  const [dedupNotice, setDedupNotice] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [newName, setNewName] = useState("")
  const [newDob, setNewDob] = useState("")
  const [newPhone, setNewPhone] = useState("")
  const [newEmail, setNewEmail] = useState("")
  const [newAddress, setNewAddress] = useState("Corpus Christi, TX")
  const [newNotes, setNewNotes] = useState("")

  const { data: clients, isLoading } = useQuery({
    queryKey: ["clients"],
    queryFn: () => api.clients.list(),
  })

  const createMutation = useMutation({
    mutationFn: (data: any) => api.clients.create(data),
    onSuccess: (res: any) => {
      queryClient.invalidateQueries({ queryKey: ["clients"] })
      setIsCreating(false)
      setFormError(null)
      setNewName("")
      setNewDob("")
      setNewPhone("")
      setNewEmail("")
      setNewNotes("")
      setDedupNotice(`Client profile for '${res.name}' saved and verified against database.`)
      setTimeout(() => setDedupNotice(null), 5000)
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || err.message || "Failed to create client."
      setFormError(typeof msg === "string" ? msg : JSON.stringify(msg))
    },
  })

  const dedupMutation = useMutation({
    mutationFn: () => api.clients.deduplicate(),
    onSuccess: (res: any) => {
      queryClient.invalidateQueries({ queryKey: ["clients"] })
      queryClient.invalidateQueries({ queryKey: ["cases"] })
      queryClient.invalidateQueries({ queryKey: ["vouchers"] })
      setDedupNotice(res.message || "Database deduplication complete: All duplicate profiles consolidated into canonical records.")
      setTimeout(() => setDedupNotice(null), 7000)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.clients.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clients"] })
    },
  })

  const filteredClients = clients?.filter((cl: any) =>
    cl.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    cl.phone?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    cl.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    cl.address?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    cl.case_numbers?.some((cn: string) => cn?.toLowerCase().includes(searchTerm.toLowerCase()))
  )

  const handleCreateClient = (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    if (!newName.trim()) {
      setFormError("Client name cannot be empty.")
      return
    }

    let cleanedPhone: string | null = null
    if (newPhone.trim()) {
      const digits = newPhone.replace(/\D/g, "")
      const norm = digits.length === 11 && digits.startsWith("1") ? digits.slice(1) : digits
      if (norm.length !== 10) {
        setFormError("Phone number must have exactly 10 digits in format (XXX) XXX-XXXX.")
        return
      }
      cleanedPhone = `(${norm.slice(0, 3)}) ${norm.slice(3, 6)}-${norm.slice(6, 10)}`
    }

    let cleanedEmail: string | null = null
    if (newEmail.trim()) {
      if (!isValidEmail(newEmail)) {
        setFormError("Please enter a valid email address (e.g. client@gmail.com).")
        return
      }
      cleanedEmail = newEmail.trim().toLowerCase()
    }

    createMutation.mutate({
      name: newName.trim(),
      dob: newDob || null,
      phone: cleanedPhone,
      email: cleanedEmail,
      address: newAddress || null,
      notes: newNotes || null,
    })
  }

  const handleDeleteClient = (id: number, name: string) => {
    if (window.confirm(`Are you sure you want to remove client profile '${name}'? Associated cases will be unlinked.`)) {
      deleteMutation.mutate(id)
    }
  }

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Users className="h-6 w-6 text-primary" />
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Client Profiles &amp; Contacts
            </h1>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Defendant roster, contact information, and linked South Texas criminal court files.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => dedupMutation.mutate()}
            disabled={dedupMutation.isPending}
            className="gap-1.5 border-primary/40 hover:bg-primary/10 text-primary text-xs"
          >
            <Sparkles className="h-4 w-4" />
            {dedupMutation.isPending ? "Consolidating..." : "Reconcile & Deduplicate"}
          </Button>

          <Button
            size="sm"
            onClick={() => {
              setFormError(null)
              setIsCreating(!isCreating)
            }}
            className="gap-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs"
          >
            <Plus className="h-4 w-4" />
            {isCreating ? "Cancel" : "Add New Client"}
          </Button>
        </div>
      </div>

      {/* Deduplication & Action Notice Banner */}
      {dedupNotice && (
        <div className="p-3.5 bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 rounded-lg text-xs flex items-center justify-between animate-fadeIn">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
            <span>{dedupNotice}</span>
          </div>
          <Button size="sm" variant="ghost" onClick={() => setDedupNotice(null)} className="h-6 text-xs text-emerald-200">
            Dismiss
          </Button>
        </div>
      )}

      {/* New Client Form */}
      {isCreating && (
        <Card className="border-primary/40 bg-card animate-fadeIn">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <User className="h-4 w-4 text-primary" />
              Create Client Profile
            </CardTitle>
            <CardDescription className="text-xs">
              If a client with this legal name already exists, the record will be automatically reconciled and updated without creating duplicates.
            </CardDescription>
          </CardHeader>
          <form onSubmit={handleCreateClient}>
            <CardContent className="space-y-4 text-xs">
              {/* Form Error Banner */}
              {formError && (
                <div className="p-3 rounded-lg bg-red-500/15 border border-red-500/40 text-red-300 text-xs flex items-center gap-2 animate-fadeIn">
                  <AlertTriangle className="h-4 w-4 shrink-0 text-red-400" />
                  <span>{formError}</span>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                <div className="space-y-1.5">
                  <Label>Full Legal Name *</Label>
                  <Input
                    placeholder="e.g. Myles Jordan"
                    value={newName}
                    onChange={(e) => {
                      setFormError(null)
                      setNewName(e.target.value)
                    }}
                    required
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>Date of Birth</Label>
                  <Input
                    type="text"
                    placeholder="MM/DD/YYYY or YYYY-MM-DD"
                    value={newDob}
                    onChange={(e) => setNewDob(e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <Label>Phone Number</Label>
                    <span className="text-[10px] text-muted-foreground">(XXX) XXX-XXXX</span>
                  </div>
                  <Input
                    placeholder="(361) 555-0100"
                    value={newPhone}
                    onChange={(e) => {
                      setFormError(null)
                      setNewPhone(formatPhoneNumber(e.target.value))
                    }}
                    maxLength={14}
                    className="font-mono text-xs"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>Client Email</Label>
                  <Input
                    placeholder="client@gmail.com"
                    value={newEmail}
                    onChange={(e) => {
                      setFormError(null)
                      setNewEmail(e.target.value)
                    }}
                    className={`font-mono text-xs ${
                      newEmail.trim() && !isValidEmail(newEmail) ? "border-red-500/80 focus:ring-red-500/50" : ""
                    }`}
                  />
                  {newEmail.trim() && !isValidEmail(newEmail) && (
                    <p className="text-[10px] text-red-400">Invalid email syntax (must be name@domain.tld)</p>
                  )}
                </div>
                <div className="sm:col-span-2 space-y-1.5">
                  <Label>Residential Address</Label>
                  <Input
                    placeholder="Address in Corpus Christi / Nueces County"
                    value={newAddress}
                    onChange={(e) => setNewAddress(e.target.value)}
                  />
                </div>
                <div className="sm:col-span-3 space-y-1.5">
                  <Label>Attorney Confidential Notes</Label>
                  <Input
                    placeholder="Bilingual preferences, bond contact info, emergency contacts..."
                    value={newNotes}
                    onChange={(e) => setNewNotes(e.target.value)}
                  />
                </div>
              </div>
            </CardContent>
            <div className="p-4 border-t border-border flex justify-end gap-2">
              <Button type="button" variant="ghost" size="sm" onClick={() => setIsCreating(false)}>
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={createMutation.isPending}>
                Save Client Record
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* Search Bar */}
      <div className="relative">
        <Search className="h-4 w-4 text-muted-foreground absolute left-3 top-2.5" />
        <Input
          placeholder="Search by client name, cause number, phone, or address..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-9 text-xs"
        />
      </div>

      {/* Clients Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 text-center text-muted-foreground text-xs">Loading clients...</div>
          ) : filteredClients && filteredClients.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-muted/40 text-muted-foreground border-b border-border">
                  <tr>
                    <th className="py-3 px-4 font-semibold">Client Name</th>
                    <th className="py-3 px-4 font-semibold">Linked Court Cases</th>
                    <th className="py-3 px-4 font-semibold">Date of Birth</th>
                    <th className="py-3 px-4 font-semibold">Contact Information</th>
                    <th className="py-3 px-4 font-semibold">Address</th>
                    <th className="py-3 px-4 font-semibold">Client Notes</th>
                    <th className="py-3 px-4 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {filteredClients.map((cl: any) => (
                    <tr key={cl.id} className="hover:bg-muted/30 transition-colors">
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <Link to={`/clients/${cl.id}`} className="font-bold text-primary text-sm hover:underline flex items-center gap-1.5">
                            <User className="h-3.5 w-3.5" />
                            {cl.name}
                          </Link>
                          {cl.is_in_custody && (
                            <Badge variant="destructive" className="bg-red-500/20 text-red-300 border-red-500/40 text-[10px] font-bold px-1.5 py-0 flex items-center gap-1">
                              <Lock className="h-2.5 w-2.5" />
                              IN JAIL
                            </Badge>
                          )}
                          <Badge variant="outline" className="text-[10px] font-mono px-1.5 py-0 text-muted-foreground">
                            ID #{cl.id}
                          </Badge>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        {cl.case_numbers && cl.case_numbers.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {cl.case_numbers.map((cn: string) => (
                              <Badge key={cn} variant="purple" className="text-[10px] font-mono flex items-center gap-1">
                                <Scale className="h-2.5 w-2.5" />
                                {cn}
                              </Badge>
                            ))}
                          </div>
                        ) : (
                          <span className="text-muted-foreground italic text-[11px]">No active cases</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {cl.dob || "—"}
                      </td>
                      <td className="py-3 px-4">
                        <div className="space-y-0.5 font-mono">
                          {cl.phone && (
                            <div className="flex items-center gap-1.5 text-foreground">
                              <Phone className="h-3 w-3 text-primary/70 shrink-0" />
                              <span>{cl.phone}</span>
                            </div>
                          )}
                          {cl.email && (
                            <div className="flex items-center gap-1.5 text-muted-foreground text-[11px]">
                              <Mail className="h-3 w-3 text-blue-400/70 shrink-0" />
                              <span className="truncate max-w-[170px]" title={cl.email}>{cl.email}</span>
                            </div>
                          )}
                          {!cl.phone && !cl.email && (
                            <span className="text-muted-foreground italic font-sans">—</span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {cl.address || "Corpus Christi, TX"}
                      </td>
                      <td className="py-3 px-4 text-muted-foreground max-w-xs truncate" title={cl.notes}>
                        {cl.notes || "—"}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button asChild variant="ghost" size="sm" className="h-7 text-xs px-2 text-primary">
                            <Link to={`/clients/${cl.id}`}>
                              View Profile <ArrowRight className="h-3.5 w-3.5 ml-1" />
                            </Link>
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 text-xs px-2 text-muted-foreground hover:text-red-400"
                            onClick={() => handleDeleteClient(cl.id, cl.name)}
                            title="Delete Client Profile"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-8 text-center text-muted-foreground text-xs">
              No clients found matching your search.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
