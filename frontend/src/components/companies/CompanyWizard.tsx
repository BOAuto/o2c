import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import Papa from "papaparse"
import { useEffect, useMemo, useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import useCustomToast from "@/hooks/useCustomToast"
import { ClientsApi } from "@/lib/api/clientsApi"
import { handleError } from "@/utils"

type ContractRow = {
  row_id: string
  product_name: string
  sku: string
  agreed_rate: string
  gst_rate: string
}

export function CompanyWizard({ companyId }: { companyId?: string }) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const csvFileRef = useRef<HTMLInputElement | null>(null)
  const [wizardStep, setWizardStep] = useState(1)
  const [companyName, setCompanyName] = useState("")
  const [paymentTerm, setPaymentTerm] = useState("")
  const [akaNames, setAkaNames] = useState("")
  const [domainPattern, setDomainPattern] = useState("")
  const [rows, setRows] = useState<ContractRow[]>([
    { row_id: crypto.randomUUID(), product_name: "", sku: "", agreed_rate: "", gst_rate: "" },
  ])
  const [pendingMissingContracts, setPendingMissingContracts] = useState<
    Array<{ id: string; sku: string; product_name: string }>
  >([])
  const [selectedContractIdsForDeactivate, setSelectedContractIdsForDeactivate] = useState<string[]>([])
  const [isMissingDialogOpen, setIsMissingDialogOpen] = useState(false)

  const { data: companies } = useQuery({ queryKey: ["companies"], queryFn: ClientsApi.listCompanies })
  const selectedCompany = (
    companies as
      | { data?: Array<{ id: string; name: string; payment_term?: number; aka_names?: string[] }> }
      | undefined
  )?.data?.find((c) => c.id === companyId)

  const effectiveCompanyId = selectedCompany?.id
  const { data: domains } = useQuery({
    queryKey: ["companyDomains", effectiveCompanyId],
    queryFn: () => ClientsApi.listCompanyDomains(effectiveCompanyId as string),
    enabled: !!effectiveCompanyId,
  })
  const { data: contracts } = useQuery({
    queryKey: ["rateContracts", effectiveCompanyId],
    queryFn: () => ClientsApi.listRateContracts(effectiveCompanyId || undefined),
  })
  const { data: rules } = useQuery({ queryKey: ["validationRules"], queryFn: ClientsApi.listValidationRules })
  const { data: assignments } = useQuery({
    queryKey: ["validationAssignments", effectiveCompanyId],
    queryFn: () => ClientsApi.listValidationAssignments(effectiveCompanyId || undefined),
  })

  const domainList = (domains as { data?: Array<{ id: string; domain_pattern: string }> } | undefined)?.data ?? []
  const contractList = (contracts as { data?: Array<{ id: string; product_name: string; sku: string; agreed_rate: number; gst_rate: number; is_active: boolean }> } | undefined)?.data ?? []
  const ruleList = (rules as { data?: Array<{ id: string; key: string; label: string; is_active: boolean }> } | undefined)?.data ?? []
  const assignmentList = (assignments as { data?: Array<{ id: string; validation_rule_id: string; is_enabled: boolean }> } | undefined)?.data ?? []

  const assignmentByRuleId = useMemo(() => {
    const map = new Map<string, { id: string; is_enabled: boolean }>()
    assignmentList.forEach((a) => {
      map.set(a.validation_rule_id, { id: a.id, is_enabled: a.is_enabled })
    })
    return map
  }, [assignmentList])

  useEffect(() => {
    setCompanyName(selectedCompany?.name ?? "")
    setPaymentTerm(selectedCompany?.payment_term ? String(selectedCompany.payment_term) : "")
    setAkaNames(selectedCompany?.aka_names?.join(", ") ?? "")
  }, [selectedCompany?.aka_names, selectedCompany?.name, selectedCompany?.payment_term])

  const createOrUpdateCompany = useMutation({
    mutationFn: () => {
      const payload = {
        name: companyName,
        payment_term: paymentTerm ? Number(paymentTerm) : undefined,
        aka_names: akaNames.split(",").map((item) => item.trim()).filter(Boolean),
      }
      return effectiveCompanyId ? ClientsApi.updateCompany(effectiveCompanyId, payload) : ClientsApi.createCompany(payload)
    },
    onSuccess: async () => {
      showSuccessToast(effectiveCompanyId ? "Company updated" : "Company created")
      await queryClient.invalidateQueries({ queryKey: ["companies"] })
      setWizardStep(2)
    },
    onError: handleError.bind(showErrorToast),
  })
  const addDomain = useMutation({
    mutationFn: () => ClientsApi.createCompanyDomain(effectiveCompanyId as string, domainPattern),
    onSuccess: () => {
      showSuccessToast("Domain added")
      setDomainPattern("")
      queryClient.invalidateQueries({ queryKey: ["companyDomains", effectiveCompanyId] })
    },
    onError: handleError.bind(showErrorToast),
  })
  const deleteDomain = useMutation({
    mutationFn: (domainId: string) => ClientsApi.deleteCompanyDomain(domainId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["companyDomains", effectiveCompanyId] }),
    onError: handleError.bind(showErrorToast),
  })
  const assignRule = useMutation({
    mutationFn: (ruleId: string) =>
      ClientsApi.createValidationAssignment({ company_id: effectiveCompanyId as string, validation_rule_id: ruleId }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["validationAssignments", effectiveCompanyId] }),
    onError: handleError.bind(showErrorToast),
  })
  const removeRuleAssignment = useMutation({
    mutationFn: (assignmentId: string) => ClientsApi.deleteValidationAssignment(assignmentId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["validationAssignments", effectiveCompanyId] }),
    onError: handleError.bind(showErrorToast),
  })

  const persistRows = async (incomingRows: ContractRow[]) => {
    const normalized = incomingRows
      .map((row) => ({
        product_name: row.product_name.trim(),
        sku: row.sku.trim(),
        agreed_rate: Number(row.agreed_rate),
        gst_rate: Number(row.gst_rate),
      }))
      .filter((row) => row.product_name && row.sku && !Number.isNaN(row.agreed_rate) && !Number.isNaN(row.gst_rate))
    const existingBySku = new Map(contractList.map((c) => [c.sku.toLowerCase(), c]))
    for (const row of normalized) {
      const existing = existingBySku.get(row.sku.toLowerCase())
      if (!existing) {
        await ClientsApi.createRateContract({ company_id: effectiveCompanyId as string, ...row })
      }
    }
    const importedSkus = new Set(normalized.map((row) => row.sku.toLowerCase()))
    const missingExisting = contractList.filter((c) => !importedSkus.has(c.sku.toLowerCase())).map((c) => ({ id: c.id, sku: c.sku, product_name: c.product_name }))
    if (missingExisting.length) {
      setPendingMissingContracts(missingExisting)
      setSelectedContractIdsForDeactivate([])
      setIsMissingDialogOpen(true)
    }
    showSuccessToast("Import done: existing SKUs skipped, new SKUs added")
    await queryClient.invalidateQueries({ queryKey: ["rateContracts", effectiveCompanyId] })
  }

  const exportCsv = () => {
    const activeContracts = contractList.filter((row) => row.is_active)
    const csvText = Papa.unparse(
      activeContracts.map((row) => ({
        product_name: row.product_name,
        sku: row.sku,
        agreed_rate: row.agreed_rate,
        gst_rate: row.gst_rate,
      })),
      { columns: ["product_name", "sku", "agreed_rate", "gst_rate"] },
    )
    const blob = new Blob([csvText], { type: "text/csv;charset=utf-8" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = `${companyName || "company"}-rate-contracts.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <section className="space-y-4 rounded-lg border p-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">Company Wizard</h2>
        <div className="text-muted-foreground text-sm">Step {wizardStep} / 4</div>
      </div>
      <div className="grid grid-cols-4 gap-2">
        {["Master Data", "Domains", "Rate Contracts", "Validations"].map((step, index) => (
          <button
            key={step}
            type="button"
            className={`rounded-md border px-3 py-2 text-xs sm:text-sm ${
              wizardStep === index + 1 ? "border-primary bg-muted/40 font-medium" : "text-muted-foreground"
            }`}
            onClick={() => setWizardStep(index + 1)}
          >
            {index + 1}. {step}
          </button>
        ))}
      </div>
      <div className="max-h-[65vh] space-y-4 overflow-auto pr-1">
        {wizardStep === 1 && (
          <div className="space-y-3">
            <h3 className="font-medium">Step 1: Client Master Data</h3>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="space-y-1"><Label>Company Name</Label><Input value={companyName} onChange={(e) => setCompanyName(e.target.value)} /></div>
              <div className="space-y-1"><Label>Payment Term (number)</Label><Input value={paymentTerm} onChange={(e) => setPaymentTerm(e.target.value.replace(/[^0-9]/g, ""))} /></div>
              <div className="space-y-1"><Label>a.k.a. (comma-separated)</Label><Input value={akaNames} onChange={(e) => setAkaNames(e.target.value)} /></div>
            </div>
            <Button onClick={() => createOrUpdateCompany.mutate()} disabled={!companyName}>Save and continue</Button>
          </div>
        )}
        {wizardStep === 2 && (
          <div className="space-y-3">
            <h3 className="font-medium">Step 2: Email Domains</h3>
            <div className="flex gap-2">
              <Input value={domainPattern} onChange={(e) => setDomainPattern(e.target.value)} placeholder="example.com" />
              <Button onClick={() => addDomain.mutate()} disabled={!effectiveCompanyId || !domainPattern}>Add</Button>
            </div>
            <div className="space-y-2">
              {domainList.map((domain) => (
                <div key={domain.id} className="flex items-center justify-between rounded-md border px-3 py-2">
                  <span>{domain.domain_pattern}</span>
                  <Button size="sm" variant="destructive" onClick={() => deleteDomain.mutate(domain.id)}>Remove</Button>
                </div>
              ))}
            </div>
          </div>
        )}
        {wizardStep === 3 && (
          <>
            <div className="space-y-3">
              <h3 className="font-medium">Step 3: Rate Contracts</h3>
              <div className="space-y-2">
                {rows.map((row, idx) => (
                  <div key={row.row_id} className="grid gap-2 sm:grid-cols-4">
                    <Input value={row.product_name} placeholder="Product" onChange={(e) => setRows((prev) => prev.map((p, i) => i === idx ? { ...p, product_name: e.target.value } : p))} />
                    <Input value={row.sku} placeholder="SKU" onChange={(e) => setRows((prev) => prev.map((p, i) => i === idx ? { ...p, sku: e.target.value } : p))} />
                    <Input value={row.agreed_rate} placeholder="Agreed Rate" onChange={(e) => setRows((prev) => prev.map((p, i) => i === idx ? { ...p, agreed_rate: e.target.value } : p))} />
                    <Input value={row.gst_rate} placeholder="GST Rate" onChange={(e) => setRows((prev) => prev.map((p, i) => i === idx ? { ...p, gst_rate: e.target.value } : p))} />
                  </div>
                ))}
              </div>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" onClick={() => setRows((prev) => [...prev, { row_id: crypto.randomUUID(), product_name: "", sku: "", agreed_rate: "", gst_rate: "" }])}>Add row</Button>
                <Button onClick={() => persistRows(rows)} disabled={!effectiveCompanyId}>Import from rows</Button>
                <Button variant="outline" onClick={exportCsv} disabled={!contractList.some((row) => row.is_active)}>Export CSV</Button>
                <Button variant="outline" onClick={() => csvFileRef.current?.click()} disabled={!effectiveCompanyId}>Import CSV</Button>
                <input
                  ref={csvFileRef}
                  type="file"
                  accept=".csv,text/csv"
                  className="hidden"
                  onChange={async (e) => {
                    const file = e.target.files?.[0]
                    if (!file) return
                    const text = await file.text()
                    const parsed = Papa.parse<{ product_name?: string; sku?: string; agreed_rate?: string; gst_rate?: string }>(text, { header: true, skipEmptyLines: "greedy", transformHeader: (header) => header.trim().toLowerCase() })
                    if (parsed.errors.length) {
                      showErrorToast(`CSV parse error: ${parsed.errors[0]?.message ?? "Invalid CSV"}`)
                      e.target.value = ""
                      return
                    }
                    const importedRows: ContractRow[] = parsed.data.map((row) => ({
                      row_id: crypto.randomUUID(),
                      product_name: (row.product_name ?? "").trim(),
                      sku: (row.sku ?? "").trim(),
                      agreed_rate: (row.agreed_rate ?? "").trim(),
                      gst_rate: (row.gst_rate ?? "").trim(),
                    }))
                    await persistRows(importedRows)
                    e.target.value = ""
                  }}
                />
              </div>
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">Existing contracts</p>
              {contractList.length ? (
                contractList.map((contract) => (
                  <div key={contract.id} className="rounded-md border px-3 py-2 text-sm">
                    {contract.product_name} ({contract.sku}) • Rate {contract.agreed_rate} • GST {contract.gst_rate}% • {contract.is_active ? "Active" : "Inactive"}
                  </div>
                ))
              ) : (
                <p className="text-muted-foreground text-sm">No contracts available yet.</p>
              )}
            </div>
          </>
        )}
        {wizardStep === 4 && (
          <div className="space-y-3">
            <h3 className="font-medium">Step 4: Apply Validations</h3>
            {ruleList.map((rule) => {
              const assignment = assignmentByRuleId.get(rule.id)
              return (
                <div key={rule.id} className="flex items-center justify-between rounded-md border px-3 py-2">
                  <div>
                    <p className="font-medium">{rule.key} - {rule.label}</p>
                    <p className="text-muted-foreground text-sm">{assignment?.is_enabled ? "Applied" : "Not applied"}</p>
                  </div>
                  <Button size="sm" variant="outline" onClick={() => assignment ? removeRuleAssignment.mutate(assignment.id) : assignRule.mutate(rule.id)}>
                    {assignment ? "Remove" : "Apply"}
                  </Button>
                </div>
              )
            })}
          </div>
        )}
      </div>
      <div className="bg-background sticky bottom-0 border-t pt-3">
        <div className="flex justify-between">
          <Button variant="outline" onClick={() => setWizardStep((s) => Math.max(1, s - 1))} disabled={wizardStep === 1}>Back</Button>
          <Button variant="outline" onClick={() => setWizardStep((s) => Math.min(4, s + 1))} disabled={wizardStep === 4}>Next</Button>
        </div>
      </div>

      <Dialog open={isMissingDialogOpen} onOpenChange={setIsMissingDialogOpen}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Select contracts to deactivate</DialogTitle>
            <DialogDescription>These contracts were not present in import. Choose what to deactivate.</DialogDescription>
          </DialogHeader>
          <div className="max-h-80 space-y-2 overflow-auto">
            {pendingMissingContracts.map((contract) => (
              <div key={contract.id} className="flex items-center gap-3 rounded-md border px-3 py-2 text-sm">
                <Checkbox
                  checked={selectedContractIdsForDeactivate.includes(contract.id)}
                  onCheckedChange={(checked) => {
                    setSelectedContractIdsForDeactivate((prev) => checked ? [...prev, contract.id] : prev.filter((id) => id !== contract.id))
                  }}
                />
                <span>{contract.product_name} ({contract.sku})</span>
              </div>
            ))}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsMissingDialogOpen(false)}>Keep all</Button>
            <Button
              onClick={async () => {
                for (const id of selectedContractIdsForDeactivate) await ClientsApi.updateRateContract(id, { is_active: false })
                await queryClient.invalidateQueries({ queryKey: ["rateContracts", effectiveCompanyId] })
                setIsMissingDialogOpen(false)
                showSuccessToast("Selected contracts deactivated")
              }}
              disabled={!selectedContractIdsForDeactivate.length}
            >
              Deactivate selected
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  )
}
