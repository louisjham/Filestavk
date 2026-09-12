import { useState, useEffect } from "react"
import { useQuery, useMutation } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  ShieldCheck,
  Globe,
  Mail,
  Building,
  User,
  CheckCircle2,
  FileCheck2,
  ExternalLink,
  Lock,
  Scale,
  Save,
  PenTool,
} from "lucide-react"
import { OctopusIcon } from "@/components/icons/OctopusIcon"

export function Settings() {
  const { data: profile, refetch } = useQuery({
    queryKey: ["attorney-profile"],
    queryFn: () => api.settings.getProfile(),
  })

  const [savedNotice, setSavedNotice] = useState(false)

  // Controlled form state — populated once profile loads from API
  const [formData, setFormData] = useState({
    name: "",
    firm_name: "",
    bar_number: "",
    vendor_number: "",
    intake_email: "",
    business_email: "",
    website: "",
    phone: "",
    address: "",
  })

  // Sync form state whenever the profile query resolves
  useEffect(() => {
    if (profile) {
      setFormData({
        name: profile.name || "",
        firm_name: profile.firm_name || "",
        bar_number: profile.bar_number || "",
        vendor_number: profile.vendor_number || "",
        intake_email: profile.intake_email || "",
        business_email: profile.business_email || "",
        website: profile.website || "",
        phone: profile.phone || "",
        address: profile.address || "",
      })
    }
  }, [profile])

  const updateMutation = useMutation({
    mutationFn: (data: any) => api.settings.updateProfile(data),
    onSuccess: () => {
      refetch()
      setSavedNotice(true)
      setTimeout(() => setSavedNotice(false), 4000)
    },
  })

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    updateMutation.mutate(formData)
  }

  const handleChange = (field: keyof typeof formData) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({ ...prev, [field]: e.target.value }))
  }


  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Attorney Profile &amp; Practice Credentials
        </h1>
        <p className="text-xs text-muted-foreground mt-1">
          Manage your State Bar, Nueces County vendor credentials, digital signature, and automated voucher defaults.
        </p>
      </div>

      {savedNotice && (
        <div className="p-3.5 bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 rounded-lg text-xs font-medium flex items-center gap-2 animate-fadeIn">
          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          Credentials updated successfully. Auto-voucher builder will apply these defaults.
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Profile & Voucher Credentials Form */}
        <div className="lg:col-span-8 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <User className="h-4 w-4 text-primary" />
                Voucher Submission Profile
              </CardTitle>
              <CardDescription className="text-xs">
                These credentials are automatically populated on all Texas Art. 26.05 Fair Defense Act vouchers.
              </CardDescription>
            </CardHeader>
            <form onSubmit={handleSubmit}>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label htmlFor="name" className="text-xs">Attorney Name</Label>
                    <Input id="name" name="name" value={formData.name} onChange={handleChange("name")} required />
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="firm_name" className="text-xs">Law Firm / Entity</Label>
                    <Input id="firm_name" name="firm_name" value={formData.firm_name} onChange={handleChange("firm_name")} required />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label htmlFor="bar_number" className="text-xs">Texas State Bar No.</Label>
                    <Input id="bar_number" name="bar_number" value={formData.bar_number} onChange={handleChange("bar_number")} required />
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="vendor_number" className="text-xs">Nueces County Vendor ID</Label>
                    <Input id="vendor_number" name="vendor_number" value={formData.vendor_number} onChange={handleChange("vendor_number")} required />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label htmlFor="intake_email" className="text-xs">Client Intake Email</Label>
                    <Input id="intake_email" name="intake_email" value={formData.intake_email} onChange={handleChange("intake_email")} required />
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="business_email" className="text-xs">Direct Business Email (Gmail Sync)</Label>
                    <Input id="business_email" name="business_email" value={formData.business_email} onChange={handleChange("business_email")} required />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label htmlFor="website" className="text-xs">Website URL</Label>
                    <Input id="website" name="website" value={formData.website} onChange={handleChange("website")} />
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="phone" className="text-xs">Office Phone</Label>
                    <Input id="phone" name="phone" value={formData.phone} onChange={handleChange("phone")} />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="address" className="text-xs">Physical / Billing Address</Label>
                  <Input id="address" name="address" value={formData.address} onChange={handleChange("address")} />
                </div>
              </CardContent>

              <CardFooter className="flex justify-end gap-2 border-t border-border pt-4">
                <Button type="submit" disabled={updateMutation.isPending} className="text-xs gap-1.5 bg-primary">
                  <Save className="h-3.5 w-3.5" />
                  Save Credentials
                </Button>
              </CardFooter>
            </form>
          </Card>

          {/* Digital Signature Representation */}
          <Card className="border-cyan-500/30">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <PenTool className="h-4 w-4 text-cyan-400" />
                Verified Digital Signature Representation
              </CardTitle>
              <CardDescription className="text-xs">
                Attached to itemized fee claims generated for Nueces County District and County Courts.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="p-4 rounded-lg bg-cyan-950/20 border border-cyan-500/30 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Digital Certificate Stamp</span>
                  <Badge variant="success" className="text-[10px] gap-1">
                    <ShieldCheck className="h-3 w-3" /> VERIFIED ACTIVE
                  </Badge>
                </div>
                <div className="font-serif italic text-xl text-cyan-300 py-1 font-semibold tracking-wide">
                  /s/ Kimbel Brandon, Esq.
                </div>
                <div className="text-[10px] text-muted-foreground font-mono">
                  Cert Hash: {profile?.digital_signature_hash || "SHA256-NUE-84920-KB-2024"} &bull; Bar #24098742
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Firm & Practice Card */}
        <div className="lg:col-span-4 space-y-6">
          <Card className="bg-gradient-to-b from-slate-900 via-cyan-950/30 to-slate-900 border-cyan-500/30">
            <CardHeader className="text-center pb-2">
              <div className="h-16 w-16 mx-auto rounded-full bg-cyan-950/60 border border-cyan-500/40 flex items-center justify-center shadow-md mb-2">
                <OctopusIcon size={36} className="text-cyan-400" />
              </div>
              <CardTitle className="text-base font-bold text-foreground">
                Hemocyanin Law
              </CardTitle>
              <CardDescription className="text-xs text-cyan-300/80">
                Corpus Christi Criminal Defense
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div className="p-3 rounded-lg bg-card/60 border border-border/80 space-y-1.5 text-muted-foreground">
                <div className="flex items-center gap-2 text-foreground font-medium">
                  <Globe className="h-3.5 w-3.5 text-cyan-400" />
                  <a
                    href="https://www.hemocyaninlaw.com/"
                    target="_blank"
                    rel="noreferrer"
                    className="hover:underline text-cyan-300 flex items-center gap-1"
                  >
                    hemocyaninlaw.com <ExternalLink className="h-2.5 w-2.5" />
                  </a>
                </div>
                <div className="flex items-center gap-2">
                  <Mail className="h-3.5 w-3.5 text-cyan-400" />
                  <span>info@hemocyaninlaw.com</span>
                </div>
                <div className="flex items-center gap-2">
                  <Building className="h-3.5 w-3.5 text-cyan-400" />
                  <span>Nueces County &bull; State Bar #24098742</span>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-secondary/40 border border-border/60 text-[11px] text-muted-foreground space-y-1">
                <span className="font-semibold text-foreground block">About the Identity:</span>
                <p className="leading-relaxed">
                  Hemocyanin is the blue respiratory protein of octopuses—symbolizing high-capacity intellect, multidirectional defense, and calm precision in the courtroom.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
