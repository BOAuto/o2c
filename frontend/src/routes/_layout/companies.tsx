import { useQuery } from "@tanstack/react-query"
import { Outlet, createFileRoute, useLocation, useNavigate } from "@tanstack/react-router"
import { useMemo, useState } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ClientsApi } from "@/lib/api/clientsApi"

export const Route = createFileRoute("/_layout/companies")({ component: CompaniesListPage })

function CompaniesListPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const [search, setSearch] = useState("")
  const [companyPage, setCompanyPage] = useState(1)
  const { data: companies } = useQuery({ queryKey: ["companies"], queryFn: ClientsApi.listCompanies })

  const companyList = (companies as { data?: Array<{ id: string; name: string; payment_term?: number; aka_names?: string[] }> } | undefined)?.data ?? []
  const filteredCompanies = useMemo(() => {
    if (!search.trim()) return companyList
    const q = search.toLowerCase()
    return companyList.filter((c) => {
      const aka = (c.aka_names ?? []).join(", ").toLowerCase()
      return c.name.toLowerCase().includes(q) || aka.includes(q)
    })
  }, [companyList, search])
  const pageSize = 8
  const totalCompanyPages = Math.max(1, Math.ceil(filteredCompanies.length / pageSize))
  const pagedCompanies = filteredCompanies.slice((companyPage - 1) * pageSize, companyPage * pageSize)

  if (location.pathname !== "/companies") {
    return <Outlet />
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Companies</h1>
          <p className="text-muted-foreground">List-first view. Open a company to manage full wizard steps.</p>
        </div>
        <Button onClick={() => navigate({ to: "/companies/$companyId", params: { companyId: "new" } })}>
          Create Company
        </Button>
      </div>
      <section className="space-y-3 rounded-lg border p-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-semibold">Companies</h2>
          <Input
            className="max-w-xs"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setCompanyPage(1)
            }}
            placeholder="Search company or a.k.a."
          />
        </div>
        <div className="text-muted-foreground flex items-center justify-between text-sm">
          <span>Total companies: {filteredCompanies.length}</span>
          <span>Click a company to open wizard</span>
        </div>
        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {pagedCompanies.map((company) => (
            <button
              type="button"
              key={company.id}
              className="hover:bg-muted/40 rounded-md border px-3 py-3 text-left transition-colors"
              onClick={() => navigate({ to: "/companies/$companyId", params: { companyId: company.id } })}
            >
              <p className="font-medium">{company.name}</p>
              <p className="text-muted-foreground text-sm">Payment term: {company.payment_term ?? "-"} days</p>
              <p className="text-muted-foreground mt-1 text-xs">AKA: {(company.aka_names ?? []).join(", ") || "-"}</p>
            </button>
          ))}
        </div>
        <div className="flex items-center justify-between">
          <Button size="sm" variant="outline" onClick={() => setCompanyPage((p) => Math.max(1, p - 1))} disabled={companyPage === 1}>Prev</Button>
          <span className="text-muted-foreground text-sm">Page {companyPage} / {totalCompanyPages}</span>
          <Button size="sm" variant="outline" onClick={() => setCompanyPage((p) => Math.min(totalCompanyPages, p + 1))} disabled={companyPage >= totalCompanyPages}>Next</Button>
        </div>
      </section>
    </div>
  )
}
