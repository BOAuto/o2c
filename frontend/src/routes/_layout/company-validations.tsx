import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ClientsApi } from "@/lib/api/clientsApi"
import { handleError } from "@/utils"
import useCustomToast from "@/hooks/useCustomToast"

export const Route = createFileRoute("/_layout/company-validations")({
  component: CompanyValidationsPage,
})

function CompanyValidationsPage() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [key, setKey] = useState("")
  const [label, setLabel] = useState("")
  const [selectedCompanyId, setSelectedCompanyId] = useState("")
  const [selectedRuleId, setSelectedRuleId] = useState("")

  const { data: rules } = useQuery({
    queryKey: ["validationRules"],
    queryFn: ClientsApi.listValidationRules,
  })
  const { data: companies } = useQuery({
    queryKey: ["companies"],
    queryFn: ClientsApi.listCompanies,
  })
  const { data: assignments } = useQuery({
    queryKey: ["validationAssignments", selectedCompanyId],
    queryFn: () => ClientsApi.listValidationAssignments(selectedCompanyId || undefined),
  })

  const createRule = useMutation({
    mutationFn: () => ClientsApi.createValidationRule({ key, label }),
    onSuccess: () => {
      showSuccessToast("Validation rule created")
      setKey("")
      setLabel("")
      queryClient.invalidateQueries({ queryKey: ["validationRules"] })
    },
    onError: handleError.bind(showErrorToast),
  })
  const assignRule = useMutation({
    mutationFn: () =>
      ClientsApi.createValidationAssignment({
        company_id: selectedCompanyId,
        validation_rule_id: selectedRuleId,
      }),
    onSuccess: () => {
      showSuccessToast("Validation assigned")
      queryClient.invalidateQueries({ queryKey: ["validationAssignments", selectedCompanyId] })
    },
    onError: handleError.bind(showErrorToast),
  })
  const removeAssignment = useMutation({
    mutationFn: (assignmentId: string) => ClientsApi.deleteValidationAssignment(assignmentId),
    onSuccess: () => {
      showSuccessToast("Validation removed")
      queryClient.invalidateQueries({ queryKey: ["validationAssignments", selectedCompanyId] })
    },
    onError: handleError.bind(showErrorToast),
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Company Validations</h1>
        <p className="text-muted-foreground">Global validation catalog and company assignments.</p>
      </div>

      <section className="space-y-3 rounded-lg border p-4">
        <h2 className="font-semibold">Global Rules</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <Input value={key} onChange={(e) => setKey(e.target.value)} placeholder="Validation key" />
          <Input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="Validation label"
          />
        </div>
        <Button onClick={() => createRule.mutate()} disabled={!key || !label}>
          Create rule
        </Button>
      </section>

      <section className="space-y-3 rounded-lg border p-4">
        <h2 className="font-semibold">Apply to Company</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <select
            className="h-11 w-full rounded-md border bg-transparent px-3 py-1 text-base sm:h-9 sm:text-sm"
            value={selectedCompanyId}
            onChange={(e) => setSelectedCompanyId(e.target.value)}
          >
            <option value="">Select company</option>
            {(companies as { data?: Array<{ id: string; name: string }> } | undefined)?.data?.map(
              (company) => (
                <option key={company.id} value={company.id}>
                  {company.name}
                </option>
              ),
            )}
          </select>
          <select
            className="h-11 w-full rounded-md border bg-transparent px-3 py-1 text-base sm:h-9 sm:text-sm"
            value={selectedRuleId}
            onChange={(e) => setSelectedRuleId(e.target.value)}
          >
            <option value="">Select rule</option>
            {(rules as { data?: Array<{ id: string; key: string; label: string }> } | undefined)?.data?.map(
              (rule) => (
                <option key={rule.id} value={rule.id}>
                  {rule.key} - {rule.label}
                </option>
              ),
            )}
          </select>
        </div>
        <Button onClick={() => assignRule.mutate()} disabled={!selectedCompanyId || !selectedRuleId}>
          Assign
        </Button>
        <div className="space-y-2">
          {(assignments as { data?: Array<{ id: string; validation_rule_id: string; is_enabled: boolean }> } | undefined)
            ?.data?.map((assignment) => (
              <div key={assignment.id} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
                <span>
                  Rule ID: {assignment.validation_rule_id} • {assignment.is_enabled ? "Enabled" : "Disabled"}
                </span>
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => removeAssignment.mutate(assignment.id)}
                >
                  Remove
                </Button>
              </div>
            )) ?? <p className="text-muted-foreground text-sm">No assignments for selected company.</p>}
        </div>
      </section>
    </div>
  )
}
