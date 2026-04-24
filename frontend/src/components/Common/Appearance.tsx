import { Sun } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"

export const SidebarAppearance = () => {
  return (
    <SidebarMenuItem>
      <SidebarMenuButton tooltip="Appearance" data-testid="theme-button">
        <Sun className="size-4 text-muted-foreground" />
        <span>Light mode</span>
      </SidebarMenuButton>
    </SidebarMenuItem>
  )
}

export const Appearance = () => {
  return (
    <div className="flex items-center justify-center">
      <Button data-testid="theme-button" variant="outline" size="icon" disabled>
        <Sun className="h-[1.2rem] w-[1.2rem]" />
        <span className="sr-only">Light mode</span>
      </Button>
    </div>
  )
}
