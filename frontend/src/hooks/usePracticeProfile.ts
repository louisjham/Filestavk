import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"

export interface PracticeProfile {
  name: string
  title: string
  firm_name: string
  website: string
  intake_email: string
  business_email: string
  bar_number: string
  vendor_number: string
  address: string
  phone: string
  digital_signature_name: string
  digital_signature_hash: string
  digital_signature_status: string
  hourly_rate_standard: number
  statutory_jurisdiction: string
  is_demo?: boolean
}

export function usePracticeProfile() {
  const { data: profile, isLoading, refetch } = useQuery<PracticeProfile>({
    queryKey: ["attorney-profile"],
    queryFn: () => api.settings.getProfile(),
    staleTime: 60000,
  })

  const isDemo = Boolean(profile?.is_demo)
  const firmName = profile?.firm_name || (isDemo ? "Coastal Operations & Practice" : "Hemocyanin Law")
  const attorneyName = profile?.name
    ? (isDemo ? profile.name : `${profile.name}, Esq.`)
    : (isDemo ? "Kimbel B." : "Kimbel Brandon, Esq.")
  const barNumber = profile?.bar_number || (isDemo ? "24000000" : "24098742")
  const email = profile?.intake_email || (isDemo ? "records@coastalpractice.example" : "info@hemocyaninlaw.com")

  return {
    profile,
    isLoading,
    isDemo,
    firmName,
    attorneyName,
    barNumber,
    email,
    refetch,
  }
}
