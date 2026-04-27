import { createFileRoute, Link } from "@tanstack/react-router"

import { BranchWizard } from "@/components/branches/BranchWizard"

export const Route = createFileRoute("/_layout/branches/$branchId")({
  component: EditBranchRoute,
})

function EditBranchRoute() {
  const { branchId } = Route.useParams()
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Edit Branch</h1>
          <p className="text-muted-foreground">Reuse same wizard layout to update branch and mappings.</p>
        </div>
        <Link to="/branches" className="text-sm underline">
          Back to Branches
        </Link>
      </div>
      <BranchWizard branchId={branchId} />
    </div>
  )
}
