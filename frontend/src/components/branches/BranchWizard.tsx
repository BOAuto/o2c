import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect, useMemo, useState } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import useCustomToast from "@/hooks/useCustomToast"
import { BranchesApi } from "@/lib/api/branchesApi"
import { handleError } from "@/utils"

export function BranchWizard({ branchId }: { branchId?: string }) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [step, setStep] = useState(1)
  const [name, setName] = useState("")
  const [slug, setSlug] = useState("")
  const [gstin, setGstin] = useState("")
  const [selectedStateId, setSelectedStateId] = useState("")

  const { data: branches } = useQuery({ queryKey: ["branches"], queryFn: BranchesApi.listBranches })
  const { data: states } = useQuery({ queryKey: ["gstStates"], queryFn: BranchesApi.listGstStates })
  const branch = (branches as { data?: Array<{ id: string; name: string; slug: string; branch_gstin: string }> } | undefined)?.data?.find((item) => item.id === branchId)
  const effectiveBranchId = branch?.id
  const { data: branchStates } = useQuery({
    queryKey: ["branchStates", effectiveBranchId],
    queryFn: () => BranchesApi.listBranchStates(effectiveBranchId as string),
    enabled: !!effectiveBranchId,
  })

  useEffect(() => {
    setName(branch?.name ?? "")
    setSlug(branch?.slug ?? "")
    setGstin(branch?.branch_gstin ?? "")
  }, [branch?.branch_gstin, branch?.name, branch?.slug])

  const createBranch = useMutation({
    mutationFn: () => BranchesApi.createBranch({ name, slug, branch_gstin: gstin }),
    onSuccess: async () => {
      showSuccessToast("Branch created")
      await queryClient.invalidateQueries({ queryKey: ["branches"] })
      setStep(2)
    },
    onError: handleError.bind(showErrorToast),
  })
  const updateBranch = useMutation({
    mutationFn: () => BranchesApi.updateBranch(effectiveBranchId as string, { name, slug, branch_gstin: gstin }),
    onSuccess: async () => {
      showSuccessToast("Branch updated")
      await queryClient.invalidateQueries({ queryKey: ["branches"] })
    },
    onError: handleError.bind(showErrorToast),
  })
  const attachState = useMutation({
    mutationFn: () => BranchesApi.attachBranchState(effectiveBranchId as string, selectedStateId),
    onSuccess: async () => {
      showSuccessToast("State mapped")
      setSelectedStateId("")
      await queryClient.invalidateQueries({ queryKey: ["branchStates", effectiveBranchId] })
      await queryClient.invalidateQueries({ queryKey: ["branches"] })
    },
    onError: handleError.bind(showErrorToast),
  })
  const detachState = useMutation({
    mutationFn: (mappingId: string) => BranchesApi.detachBranchState(effectiveBranchId as string, mappingId),
    onSuccess: async () => {
      showSuccessToast("State removed")
      await queryClient.invalidateQueries({ queryKey: ["branchStates", effectiveBranchId] })
      await queryClient.invalidateQueries({ queryKey: ["branches"] })
    },
    onError: handleError.bind(showErrorToast),
  })

  const stateById = useMemo(() => {
    const map = new Map<string, string>()
    ;(states as { data?: Array<{ id: string; code: string; description: string }> } | undefined)?.data?.forEach((s) => {
      map.set(s.id, `${s.code} - ${s.description}`)
    })
    return map
  }, [states])

  const mappings = (branchStates as { data?: Array<{ id: string; gst_state_code_id: string }> } | undefined)?.data ?? []

  return (
    <section className="space-y-4 rounded-lg border p-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">{effectiveBranchId ? "Edit Branch" : "Create Branch"}</h2>
        <span className="text-muted-foreground text-sm">Step {step} / 2</span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {["Branch Details", "Map GST States"].map((stepName, idx) => (
          <button
            key={stepName}
            type="button"
            className={`rounded-md border px-3 py-2 text-sm ${step === idx + 1 ? "border-primary bg-muted/40 font-medium" : "text-muted-foreground"}`}
            onClick={() => setStep(idx + 1)}
          >
            {idx + 1}. {stepName}
          </button>
        ))}
      </div>

      {step === 1 ? (
        <div className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-1"><Label>Branch Name</Label><Input value={name} onChange={(e) => setName(e.target.value)} /></div>
            <div className="space-y-1"><Label>Slug</Label><Input value={slug} onChange={(e) => setSlug(e.target.value)} /></div>
            <div className="space-y-1"><Label>Branch GSTIN</Label><Input value={gstin} onChange={(e) => setGstin(e.target.value.toUpperCase())} /></div>
          </div>
          <Button onClick={() => (effectiveBranchId ? updateBranch.mutate() : createBranch.mutate())} disabled={!name || !slug || !gstin}>
            {effectiveBranchId ? "Save Branch" : "Create Branch"}
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-3">
            <select
              className="h-11 w-full rounded-md border bg-transparent px-3 py-1 text-base sm:h-9 sm:text-sm"
              value={selectedStateId}
              onChange={(e) => setSelectedStateId(e.target.value)}
            >
              <option value="">Select GST state code</option>
              {(states as { data?: Array<{ id: string; code: string; description: string }> } | undefined)?.data?.map(
                (state) => (
                  <option key={state.id} value={state.id}>{state.code} - {state.description}</option>
                ),
              )}
            </select>
            <Button variant="outline" onClick={() => attachState.mutate()} disabled={!effectiveBranchId || !selectedStateId}>
              Save mapping
            </Button>
          </div>
          <div className="space-y-2">
            {mappings.length ? mappings.map((mapping) => (
              <div key={mapping.id} className="flex items-center justify-between rounded-md border px-3 py-2">
                <span>{stateById.get(mapping.gst_state_code_id) ?? mapping.gst_state_code_id}</span>
                <Button size="sm" variant="destructive" onClick={() => detachState.mutate(mapping.id)}>Remove</Button>
              </div>
            )) : <p className="text-muted-foreground text-sm">No states mapped yet.</p>}
          </div>
        </div>
      )}

      <div className="flex justify-between border-t pt-3">
        <Button variant="outline" onClick={() => setStep((s) => Math.max(1, s - 1))} disabled={step === 1}>Back</Button>
        <Button variant="outline" onClick={() => setStep((s) => Math.min(2, s + 1))} disabled={step === 2}>Next</Button>
      </div>
    </section>
  )
}
