import { callApi } from "./http"

export type RejectedCentralRow = {
  id: string
  central_mailbox_config_id: string
  from_address: string
  subject: string | null
  message_id_norm: string | null
  imap_uid: string
  rejection_reason: string
  created_at: string | null
}

export type RejectedCentralList = {
  data: RejectedCentralRow[]
  count: number
}

export type InternalUnmappedRow = {
  id: string
  central_mailbox_config_id: string
  from_address: string
  subject: string | null
  message_id_norm: string | null
  imap_uid: string
  created_at: string | null
}

export type InternalUnmappedList = {
  data: InternalUnmappedRow[]
  count: number
}

export type MailboxRunRow = {
  run: {
    id: string
    source_message_id_norm: string
    order_user_message_id_raw: string | null
    order_user_message_id_normalized: string | null
    order_user_email: string | null
    source_from: string | null
    source_subject: string | null
    source_received_at: string | null
    no_attachment_order: boolean
    status: string
    external_correspondent_from: string | null
    external_correspondent_cc: string | null
    external_correspondent_domain: string | null
    external_correspondent_at: string | null
    created_at: string | null
    updated_at: string | null
  }
  html_artifact_id: string | null
  html_file_name: string | null
}

export type MailboxRunList = {
  data: MailboxRunRow[]
  count: number
}

export type IngestionStorageSummary = {
  runs: number
  artifacts: number
  rejected_central: number
  internal_unmapped: number
}

export type RunArtifact = {
  id: string
  order_ingestion_id: string
  artifact_kind: string
  object_key: string
  file_name: string
  mime_type: string | null
  size_bytes: number
}

export type RunDetail = {
  run: MailboxRunRow["run"]
  artifacts: RunArtifact[]
}

export type IngestionMessageComprehensive = {
  message_id_norm: string
  "Order Ingestion": Array<{
    "processed order": Omit<MailboxRunRow["run"], "id">
    artifacts: Array<{
      artifact_kind: string
      object_key: string
      file_name: string
      mime_type: string | null
      size_bytes: number
    }>
  }>
  rejected_central: RejectedCentralRow[]
  internal_unmapped: InternalUnmappedRow[]
}

export const IngestionApi = {
  listRejectedCentral: (params?: { skip?: number; limit?: number }) => {
    const q = new URLSearchParams()
    if (params?.skip != null) q.set("skip", String(params.skip))
    if (params?.limit != null) q.set("limit", String(params.limit))
    const suffix = q.toString() ? `?${q}` : ""
    return callApi(`/api/v1/ingestion/rejected-central${suffix}`, "GET") as Promise<RejectedCentralList>
  },
  listInternalUnmapped: (params?: { skip?: number; limit?: number }) => {
    const q = new URLSearchParams()
    if (params?.skip != null) q.set("skip", String(params.skip))
    if (params?.limit != null) q.set("limit", String(params.limit))
    const suffix = q.toString() ? `?${q}` : ""
    return callApi(`/api/v1/ingestion/internal-unmapped${suffix}`, "GET") as Promise<InternalUnmappedList>
  },
  listMailboxRuns: (params?: { skip?: number; limit?: number }) => {
    const q = new URLSearchParams()
    if (params?.skip != null) q.set("skip", String(params.skip))
    if (params?.limit != null) q.set("limit", String(params.limit))
    const suffix = q.toString() ? `?${q}` : ""
    return callApi(`/api/v1/ingestion/mailbox${suffix}`, "GET") as Promise<MailboxRunList>
  },
  getMailboxRunHtmlUrl: (runId: string) => `/api/v1/ingestion/runs/${runId}/html`,
  getRunArtifactUrl: (runId: string, artifactId: string, disposition: "inline" | "attachment") =>
    `/api/v1/ingestion/runs/${runId}/artifacts/${artifactId}?disposition=${disposition}`,
  getStorageSummary: () =>
    callApi("/api/v1/ingestion/storage-summary", "GET") as Promise<IngestionStorageSummary>,
  getRunDetail: (runId: string) =>
    callApi(`/api/v1/ingestion/runs/${runId}`, "GET") as Promise<RunDetail>,
  getByMessageId: (messageId: string) =>
    callApi(
      `/api/v1/ingestion/by-message-id/${encodeURIComponent(messageId)}`,
      "GET",
    ) as Promise<IngestionMessageComprehensive>,

  /** Signal Temporal scheduler to poll central unread (skips countdown; ~15s granularity). */
  requestO2cPollNow: () =>
    callApi("/api/v1/temporal/o2c/scheduler/poll-now", "POST") as Promise<{ message: string }>,
}
