import { Home, Users } from "lucide-react"

import { Logo } from "@/components/Common/Logo"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarRail,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar"
import useAuth from "@/hooks/useAuth"
import { type Item, Main } from "./Main"
import { User } from "./User"

const baseItems: Item[] = [
  { icon: Home, title: "Dashboard", path: "/" },
]

export function AppSidebar() {
  const { user: currentUser } = useAuth()
  const { isMobile } = useSidebar()

  const items = currentUser?.is_superuser
    ? [...baseItems, { icon: Users, title: "Admin", path: "/admin" }]
    : baseItems

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="flex-row items-center justify-between px-3 py-4 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-2">
        <Logo variant="responsive" />
        <div className="hidden items-center md:flex">
          <SidebarTrigger className="text-muted-foreground group-data-[collapsible=icon]:hidden" />
        </div>
        <div className="flex items-center md:hidden">
          <SidebarTrigger className="text-muted-foreground" />
        </div>
      </SidebarHeader>
      <SidebarContent>
        <Main items={items} />
      </SidebarContent>
      {!isMobile && (
        <SidebarFooter>
          <User user={currentUser} />
        </SidebarFooter>
      )}
      <SidebarRail />
    </Sidebar>
  )
}

export default AppSidebar
