import { Link } from "@tanstack/react-router"

import { cn } from "@/lib/utils"
import icon from "/assets/images/bos-icon.png"
import logo from "/assets/images/bos-logo.png"

interface LogoProps {
  variant?: "full" | "icon" | "responsive"
  className?: string
  asLink?: boolean
}

export function Logo({
  variant = "full",
  className,
  asLink = true,
}: LogoProps) {
  const content =
    variant === "responsive" ? (
      <>
        <img
          src={logo}
          alt="Brilliant Office Solutions"
          className={cn(
            "h-6 w-auto sm:h-7 lg:h-6 group-data-[collapsible=icon]:hidden",
            className,
          )}
        />
        <img
          src={icon}
          alt="Brilliant Office Solutions"
          className={cn(
            "hidden h-6 w-auto sm:h-7 lg:h-6 group-data-[collapsible=icon]:block",
            className,
          )}
        />
      </>
    ) : (
      <img
        src={variant === "full" ? logo : icon}
        alt="Brilliant Office Solutions"
        className={cn(
          variant === "full"
            ? "h-6 w-auto sm:h-7 lg:h-6"
            : "h-6 w-auto sm:h-7 lg:h-6",
          className,
        )}
      />
    )

  if (!asLink) {
    return content
  }

  return <Link to="/">{content}</Link>
}
