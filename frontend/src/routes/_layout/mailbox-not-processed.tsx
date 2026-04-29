import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { IngestionApi } from "@/lib/api/ingestionApi"

export const Route = createFileRoute("/_layout/mailbox-not-processed")({
  component: MailboxNotProcessedPage,
})

function MailboxNotProcessedPage() {
  const [searchQuery, setSearchQuery] = useState("")
  const [reasonFilter, setReasonFilter] = useState<string>("all")

  const rejected = useQuery({
    queryKey: ["ingestion", "rejected-central", "not-processed"],
    queryFn: () => IngestionApi.listRejectedCentral({ limit: 300 }),
  })
  const unmapped = useQuery({
    queryKey: ["ingestion", "internal-unmapped", "not-processed"],
    queryFn: () => IngestionApi.listInternalUnmapped({ limit: 300 }),
  })

  const rejectedRows = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    return (rejected.data?.data ?? []).filter((row) => {
      if (reasonFilter !== "all" && row.rejection_reason !== reasonFilter) return false
      if (!q) return true
      const hay = [row.subject ?? "", row.from_address, row.message_id_norm ?? "", row.rejection_reason]
        .join(" ")
        .toLowerCase()
      return hay.includes(q)
    })
  }, [rejected.data?.data, reasonFilter, searchQuery])

  const unmappedRows = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    return (unmapped.data?.data ?? []).filter((row) => {
      if (!q) return true
      const hay = [row.subject ?? "", row.from_address, row.message_id_norm ?? ""].join(" ").toLowerCase()
      return hay.includes(q)
    })
  }, [unmapped.data?.data, searchQuery])

  const rejectionReasons = useMemo(() => {
    return Array.from(new Set((rejected.data?.data ?? []).map((row) => row.rejection_reason))).sort()
  }, [rejected.data?.data])

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Mailbox Not Processed</h1>
        <p className="text-sm text-muted-foreground">
          Review not-processed messages split by rejected central and internal unmapped.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-2 rounded-md border p-3 md:grid-cols-[2fr_1fr]">
        <input
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search subject, from, message-id..."
          className="h-9 rounded-md border px-3 text-sm"
        />
        <select
          value={reasonFilter}
          onChange={(e) => setReasonFilter(e.target.value)}
          className="h-9 rounded-md border px-2 text-sm"
        >
          <option value="all">All rejection reasons</option>
          {rejectionReasons.map((reason) => (
            <option key={reason} value={reason}>
              {reason}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-md border">
          <div className="border-b px-3 py-2 text-sm font-medium">
            Rejected central ({rejectedRows.length})
          </div>
          <div className="max-h-[560px] overflow-auto p-2 text-xs">
            {rejectedRows.map((r) => (
              <div key={r.id} className="border-b py-2">
                <div className="truncate font-medium">{r.subject || "(No subject)"}</div>
                <div className="truncate text-muted-foreground">{r.from_address}</div>
                <div className="text-muted-foreground">Reason: {r.rejection_reason}</div>
                {r.message_id_norm && (
                  <div className="truncate font-mono text-[11px] text-muted-foreground">{r.message_id_norm}</div>
                )}
              </div>
            ))}
            {rejectedRows.length === 0 && (
              <p className="p-2 text-muted-foreground">No rejected central messages for current filters.</p>
            )}
          </div>
        </div>

        <div className="rounded-md border">
          <div className="border-b px-3 py-2 text-sm font-medium">
            Internal unmapped ({unmappedRows.length})
          </div>
          <div className="max-h-[560px] overflow-auto p-2 text-xs">
            {unmappedRows.map((r) => (
              <div key={r.id} className="border-b py-2">
                <div className="truncate font-medium">{r.subject || "(No subject)"}</div>
                <div className="truncate text-muted-foreground">{r.from_address}</div>
                {r.message_id_norm && (
                  <div className="truncate font-mono text-[11px] text-muted-foreground">{r.message_id_norm}</div>
                )}
              </div>
            ))}
            {unmappedRows.length === 0 && (
              <p className="p-2 text-muted-foreground">No internal unmapped messages for current filters.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
