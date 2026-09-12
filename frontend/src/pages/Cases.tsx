import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Scale, Plus, Search, Filter, ArrowRight, User, Lock } from "lucide-react"
import { formatDate } from "@/lib/utils"

export function Cases() {
  const [searchTerm, setSearchTerm] = useState("")
  const [filterCja, setFilterCja] = useState<string>("ALL")
  const [filterStage, setFilterStage] = useState<string>("ALL")

  const { data: cases, isLoading } = useQuery({
    queryKey: ["cases"],
    queryFn: () => api.cases.list(),
  })

  const filteredCases = cases?.filter((c: any) => {
    const matchSearch =
      c.case_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.court?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.client?.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.charge_description?.toLowerCase().includes(searchTerm.toLowerCase())

    const matchCja =
      filterCja === "ALL" ? true : filterCja === "CJA" ? c.is_cja : !c.is_cja

    const matchStage = filterStage === "ALL" ? true : c.stage === filterStage

    return matchSearch && matchCja && matchStage
  })

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Scale className="h-6 w-6 text-primary" />
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Court Cases Docket
            </h1>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Nueces County District &amp; County Courts at Law case roster with Texas criminal defense lifecycle tracking.
          </p>
        </div>

        <Button asChild size="sm" className="gap-1.5 bg-blue-600 hover:bg-blue-700 text-white">
          <Link to="/ingestion/portal">
            <Plus className="h-4 w-4" />
            Import from Odyssey Portal
          </Link>
        </Button>
      </div>

      {/* Search & Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="h-4 w-4 text-muted-foreground absolute left-3 top-2.5" />
          <Input
            placeholder="Search by case #, client name, charge, or court..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9 text-xs"
          />
        </div>

        <div className="flex items-center gap-2">
          <select
            className="h-9 rounded-md border border-input bg-card px-3 text-xs shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
            value={filterCja}
            onChange={(e) => setFilterCja(e.target.value)}
          >
            <option value="ALL">All Representation (CJA &amp; Retained)</option>
            <option value="CJA">Appointed (CJA Only)</option>
            <option value="RETAINED">Retained Private Counsel</option>
          </select>

          <select
            className="h-9 rounded-md border border-input bg-card px-3 text-xs shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
            value={filterStage}
            onChange={(e) => setFilterStage(e.target.value)}
          >
            <option value="ALL">All Lifecycle Stages</option>
            <option value="ARREST">Arrest &amp; Booking</option>
            <option value="BOND">Bond &amp; Bail</option>
            <option value="INDICTMENT">Indictment / Information</option>
            <option value="DISCOVERY">Morton Discovery</option>
            <option value="PRE_TRIAL">Pre-Trial &amp; Motions</option>
            <option value="TRIAL">Trial</option>
            <option value="DISPOSED">Disposed / Vouchers</option>
            <option value="PROBATION">Probation / Supervision</option>
          </select>
        </div>
      </div>

      {/* Cases Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 text-center text-muted-foreground text-xs">Loading cases...</div>
          ) : filteredCases && filteredCases.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-muted/40 text-muted-foreground border-b border-border">
                  <tr>
                    <th className="py-3 px-4 font-semibold">Case Number</th>
                    <th className="py-3 px-4 font-semibold">Client Name</th>
                    <th className="py-3 px-4 font-semibold">Court &amp; Judge</th>
                    <th className="py-3 px-4 font-semibold">Charge Description</th>
                    <th className="py-3 px-4 font-semibold">Stage</th>
                    <th className="py-3 px-4 font-semibold">Type</th>
                    <th className="py-3 px-4 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {filteredCases.map((c: any) => (
                    <tr key={c.id} className="hover:bg-muted/30 transition-colors">
                      <td className="py-3 px-4 font-mono font-bold text-primary">
                        <div className="flex items-center gap-1.5">
                          <Link to={`/cases/${c.id}`} className="hover:underline">
                            {c.case_number}
                          </Link>
                          {c.in_custody && (
                            <Badge variant="destructive" className="bg-red-500/20 text-red-300 border-red-500/40 text-[9px] font-bold px-1.5 py-0 flex items-center gap-0.5">
                              <Lock className="h-2.5 w-2.5" />
                              IN JAIL
                            </Badge>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-semibold text-foreground flex items-center gap-1.5">
                          <User className="h-3.5 w-3.5 text-muted-foreground" />
                          {c.client?.name || "Client #" + c.client_id}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="text-foreground">{c.court}</div>
                        {c.judge && <div className="text-[10px] text-muted-foreground">{c.judge}</div>}
                      </td>
                      <td className="py-3 px-4">
                        <div className="text-foreground font-medium max-w-xs truncate" title={c.charge_description}>
                          {c.charge_description || c.case_type}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant={c.status === "OPEN" ? "info" : c.status === "DISPOSED" ? "warning" : "success"}>
                          {c.stage || c.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        {c.is_cja ? (
                          <Badge variant="purple">CJA Appointed</Badge>
                        ) : (
                          <Badge variant="teal">Retained</Badge>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Button asChild variant="ghost" size="sm" className="h-7 text-xs px-2 text-primary">
                          <Link to={`/cases/${c.id}`}>
                            View File <ArrowRight className="h-3.5 w-3.5 ml-1" />
                          </Link>
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-8 text-center text-muted-foreground text-xs">
              No cases found matching your filters.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
