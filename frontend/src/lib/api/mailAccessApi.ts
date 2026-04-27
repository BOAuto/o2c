import { callApi } from "./http"

export const MailAccessApi = {
  getCentralMailbox: () =>
    callApi("/api/v1/mail-access/central", "GET") as Promise<
      { email?: string; ingestion_retrieval_period?: string | null } | null
    >,
  upsertCentralMailbox: (payload: {
    email: string
    app_password: string
    ingestion_retrieval_period?: string
  }) =>
    callApi("/api/v1/mail-access/central", "PUT", payload),
  updateCentralMailbox: (payload: {
    email?: string
    app_password?: string
    ingestion_retrieval_period?: string
    is_active?: boolean
  }) => callApi("/api/v1/mail-access/central", "PATCH", payload),
  listUserMailAccesses: () => callApi("/api/v1/mail-access/users", "GET"),
  grantUserMailAccess: (payload: {
    user_id: string
    access_type: "OrderUser" | "OrderInternalUser"
    app_password: string
  }) => callApi("/api/v1/mail-access/users", "POST", payload),
  updateUserMailAccess: (
    userId: string,
    payload: {
      access_type?: "OrderUser" | "OrderInternalUser"
      app_password?: string
      is_active?: boolean
    },
  ) => callApi(`/api/v1/mail-access/users/${userId}`, "PATCH", payload),
  revokeUserMailAccess: (userId: string) =>
    callApi(`/api/v1/mail-access/users/${userId}`, "DELETE"),
}
