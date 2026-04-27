import { callApi } from "./http"

export const BranchesApi = {
  listBranches: () => callApi("/api/v1/branches/", "GET"),
  createBranch: (payload: { name: string; slug: string; branch_gstin: string }) =>
    callApi("/api/v1/branches/", "POST", payload),
  updateBranch: (
    branchId: string,
    payload: {
      name?: string
      slug?: string
      branch_gstin?: string
      is_active?: boolean
    },
  ) => callApi(`/api/v1/branches/${branchId}`, "PATCH", payload),
  deleteBranch: (branchId: string) => callApi(`/api/v1/branches/${branchId}`, "DELETE"),
  listGstStates: () => callApi("/api/v1/branches/gst-states", "GET"),
  listBranchStates: (branchId: string) =>
    callApi(`/api/v1/branches/${branchId}/gst-states`, "GET"),
  attachBranchState: (branchId: string, gst_state_code_id: string) =>
    callApi(`/api/v1/branches/${branchId}/gst-states`, "POST", {
      branch_id: branchId,
      gst_state_code_id,
    }),
  detachBranchState: (branchId: string, mappingId: string) =>
    callApi(`/api/v1/branches/${branchId}/gst-states/${mappingId}`, "DELETE"),
}
