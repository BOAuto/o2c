import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"

import { Footer } from "@/components/Common/Footer"
import { Logo } from "@/components/Common/Logo"
import AppSidebar from "@/components/Sidebar/AppSidebar"
import { UserCompactMenu } from "@/components/Sidebar/User"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout")({
  component: Layout,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({
        to: "/login",
      })
    }
  },
})

function Layout() {
  const { user } = useAuth()

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center justify-between border-b bg-background/95 px-3 backdrop-blur md:hidden">
          <div className="flex w-10 items-center justify-start">
            <SidebarTrigger className="-ml-1 text-muted-foreground" />
          </div>
          <div className="flex flex-1 items-center justify-center self-stretch">
            <Logo variant="full" className="h-6 w-auto sm:h-7" />
          </div>
          <div className="flex w-10 items-center justify-end">
            <UserCompactMenu user={user} />
          </div>
        </header>
        <main className="flex-1 p-4 md:p-8">
          <div className="mx-auto min-w-0 max-w-7xl">
            <Outlet />
          </div>
        </main>
        <Footer />
      </SidebarInset>
    </SidebarProvider>
  )
}

export default Layout
