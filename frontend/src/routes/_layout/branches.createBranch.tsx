import { createFileRoute, Link } from "@tanstack/react-router"

import { BranchWizard } from "@/components/branches/BranchWizard"

export const Route = createFileRoute("/_layout/branches/createBranch")({
  component: CreateBranchRoute,
})

function CreateBranchRoute() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Create Branch</h1>
          <p className="text-muted-foreground">Create a branch, map GST states, and save in one flow.</p>
        </div>
        <Link to="/branches" className="text-sm underline">
          Back to Branches
        </Link>
      </div>
      <BranchWizard />
    </div>
  )
}
