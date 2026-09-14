import { Outlet, Navigate } from "react-router-dom"
import { Sidebar } from "./Sidebar"
import { Topbar } from "./Topbar"
import { useAuth } from "@/lib/auth"

export function AppLayout() {
  const { token, isLoading } = useAuth()

  if (isLoading) {
    return <div className="min-h-screen bg-slate-950 flex items-center justify-center text-white">Loading...</div>
  }

  if (!token) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="flex h-screen bg-slate-950 text-slate-200 overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
