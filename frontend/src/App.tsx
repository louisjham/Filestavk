import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { AuthProvider } from "@/lib/auth"
import { AppLayout } from "./components/layout/AppLayout"

// Pages
import { Login } from "./pages/Login"
import { Dashboard } from "./pages/Dashboard"
import { Vouchers } from "./pages/Vouchers"
import { Clients } from "./pages/Clients"
import { ClientDetail } from "./pages/ClientDetail"
import { Cases } from "./pages/Cases"
import { CaseDetail } from "./pages/CaseDetail"
import { Documents } from "./pages/Documents"
import { Ingestion } from "./pages/Ingestion"
import { PortalAssist } from "./pages/PortalAssist"
import { SpreadsheetQueue } from "./pages/SpreadsheetQueue"
import { LegalResearch } from "./pages/LegalResearch"
import { Search } from "./pages/Search"
import { Analytics } from "./pages/Analytics"
import { Settings } from "./pages/Settings"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    }
  }
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            
            <Route element={<AppLayout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/spreadsheet" element={<SpreadsheetQueue />} />
              <Route path="/vouchers" element={<Vouchers />} />
              <Route path="/clients" element={<Clients />} />
              <Route path="/clients/:id" element={<ClientDetail />} />
              <Route path="/cases" element={<Cases />} />
              <Route path="/cases/:id" element={<CaseDetail />} />
              <Route path="/documents" element={<Documents />} />
              <Route path="/ingestion" element={<Ingestion />} />
              <Route path="/ingestion/portal" element={<PortalAssist />} />
              <Route path="/research" element={<LegalResearch />} />
              <Route path="/search" element={<Search />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/settings" element={<Settings />} />
              {/* Catch-all: redirect unknown paths to dashboard */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}
