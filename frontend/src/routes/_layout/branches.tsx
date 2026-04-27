import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Outlet, createFileRoute, useLocation, useNavigate } from "@tanstack/react-router"
import { useMemo, useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import useCustomToast from "@/hooks/useCustomToast"
import { BranchesApi } from "@/lib/api/branchesApi"
import { handleError } from "@/utils"

export const Route = createFileRoute("/_layout/branches")({
  component: BranchesPage,
})

function BranchesPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [search, setSearch] = useState("")
  const [branchPage, setBranchPage] = useState(1)
  const [deleteCandidate, setDeleteCandidate] = useState<{ id: string; name: string } | null>(null)

  const { data: branches } = useQuery({
    queryKey: ["branches"],
    queryFn: BranchesApi.listBranches,
  })
  const { data: states } = useQuery({
    queryKey: ["gstStates"],
    queryFn: BranchesApi.listGstStates,
  })
  const branchIds = (
    branches as { data?: Array<{ id: string }> } | undefined
  )?.data?.map((b) => b.id)

  const { data: allBranchMappings } = useQuery({
    queryKey: ["allBranchStates", branchIds],
    queryFn: async () => {
      const ids = branchIds ?? []
      const results = await Promise.all(ids.map((id) => BranchesApi.listBranchStates(id)))
      return results.flatMap(
        (result) =>
          (result as { data?: Array<{ id: string; branch_id: string; gst_state_code_id: string }> })
            .data ?? [],
      )
    },
    enabled: Boolean(branchIds?.length),
  })

  const updateBranchInline = useMutation({
    mutationFn: (payload: { branchId: string; is_active: boolean }) =>
      BranchesApi.updateBranch(payload.branchId, {
        is_active: payload.is_active,
      }),
    onSuccess: () => {
      showSuccessToast("Branch status updated")
      queryClient.invalidateQueries({ queryKey: ["branches"] })
    },
    onError: handleError.bind(showErrorToast),
  })

  const deleteBranch = useMutation({
    mutationFn: (branchId: string) => BranchesApi.deleteBranch(branchId),
    onSuccess: () => {
      showSuccessToast("Branch deleted")
      queryClient.invalidateQueries({ queryKey: ["branches"] })
    },
    onError: handleError.bind(showErrorToast),
  })

  const branchList = (
    branches as
      | { data?: Array<{ id: string; name: string; slug: string; branch_gstin: string; is_active: boolean }> }
      | undefined
  )?.data
  const stateList = (states as { data?: Array<{ id: string; code: string; description: string }> } | undefined)?.data
  const stateById = useMemo(() => {
    const map = new Map<string, string>()
    stateList?.forEach((state) => {
      map.set(state.id, `${state.code} - ${state.description}`)
    })
    return map
  }, [stateList])
  const mappingsByBranch = useMemo(() => {
    const map = new Map<string, string[]>()
    ;(
      allBranchMappings as Array<{ id: string; branch_id: string; gst_state_code_id: string }> | undefined
    )?.forEach((mapping) => {
      const label = stateById.get(mapping.gst_state_code_id) ?? mapping.gst_state_code_id
      const existing = map.get(mapping.branch_id) ?? []
      existing.push(label)
      map.set(mapping.branch_id, existing)
    })
    return map
  }, [allBranchMappings, stateById])
  const filteredBranches = useMemo(() => {
    if (!search.trim()) {
      return branchList ?? []
    }
    const q = search.trim().toLowerCase()
    return (branchList ?? []).filter(
      (branch) =>
        branch.name.toLowerCase().includes(q) ||
        branch.slug.toLowerCase().includes(q) ||
        branch.branch_gstin.toLowerCase().includes(q),
    )
  }, [branchList, search])
  const branchPageSize = 10
  const totalBranchPages = Math.max(1, Math.ceil(filteredBranches.length / branchPageSize))
  const pagedBranches = filteredBranches.slice(
    (branchPage - 1) * branchPageSize,
    branchPage * branchPageSize,
  )

  if (location.pathname !== "/branches") {
    return <Outlet />
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Internal Branches</h1>
        <p className="text-muted-foreground">
          Manage internal branches, GSTIN, and branch-to-GST-state mapping.
        </p>
      </div>

      <section className="space-y-2 rounded-lg border p-4 text-sm">
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-semibold">Existing Branches</h2>
          <Button onClick={() => navigate({ to: "/branches/createBranch" })}>New Branch</Button>
          <Input
            className="max-w-xs"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setBranchPage(1)
            }}
            placeholder="Search by name, slug, GSTIN"
          />
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Slug</TableHead>
              <TableHead>GSTIN</TableHead>
              <TableHead>Mapped States</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {pagedBranches.length ? (
              pagedBranches.map((branch) => (
                <TableRow key={branch.id}>
                  <TableCell>{branch.name}</TableCell>
                  <TableCell>{branch.slug}</TableCell>
                  <TableCell>{branch.branch_gstin}</TableCell>
                  <TableCell className="max-w-md align-top whitespace-normal">
                    {(mappingsByBranch.get(branch.id) ?? []).length ? (
                      <div className="space-y-1">
                        {(mappingsByBranch.get(branch.id) ?? []).map((label) => (
                          <p key={`${branch.id}-${label}`} className="text-sm leading-5">
                            {label}
                          </p>
                        ))}
                      </div>
                    ) : (
                      "-"
                    )}
                  </TableCell>
                  <TableCell>{branch.is_active ? "Active" : "Inactive"}</TableCell>
                  <TableCell className="space-x-2 text-right">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => navigate({ to: "/branches/$branchId", params: { branchId: branch.id } })}
                    >
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        updateBranchInline.mutate({
                          branchId: branch.id,
                          is_active: !branch.is_active,
                        })
                      }
                    >
                      {branch.is_active ? "Deactivate" : "Activate"}
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() =>
                        setDeleteCandidate({
                          id: branch.id,
                          name: branch.name,
                        })
                      }
                    >
                      Delete
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={6} className="text-muted-foreground text-center">
                  No branches found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        <div className="flex items-center justify-between pt-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setBranchPage((p) => Math.max(1, p - 1))}
            disabled={branchPage === 1}
          >
            Prev
          </Button>
          <span className="text-muted-foreground text-sm">
            Page {branchPage} of {totalBranchPages}
          </span>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setBranchPage((p) => Math.min(totalBranchPages, p + 1))}
            disabled={branchPage >= totalBranchPages}
          >
            Next
          </Button>
        </div>
      </section>
      <Dialog open={!!deleteCandidate} onOpenChange={(open) => !open && setDeleteCandidate(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Delete branch</DialogTitle>
            <DialogDescription>
              This will remove `{deleteCandidate?.name}` and its mappings.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteCandidate(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                if (!deleteCandidate) return
                deleteBranch.mutate(deleteCandidate.id)
                setDeleteCandidate(null)
              }}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
