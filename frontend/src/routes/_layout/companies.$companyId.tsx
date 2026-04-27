import { createFileRoute, Link } from "@tanstack/react-router"

import { CompanyWizard } from "@/components/companies/CompanyWizard"

export const Route = createFileRoute("/_layout/companies/$companyId")({
  component: CompanyWizardRoute,
})

function CompanyWizardRoute() {
  const { companyId } = Route.useParams()
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Company Wizard</h1>
          <p className="text-muted-foreground">
            {companyId === "new" ? "Create a new company and configure all steps." : "Manage company master data, domains, contracts and validations."}
          </p>
        </div>
        <Link to="/companies" className="text-sm underline">
          Back to Companies
        </Link>
      </div>
      <CompanyWizard companyId={companyId === "new" ? undefined : companyId} />
    </div>
  )
}
