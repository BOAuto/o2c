import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { IngestionApi } from "@/lib/api/ingestionApi"

export const Route = createFileRoute("/_layout/mailbox-message-ids")({
  component: MailboxMessageIdsPage,
})

function MailboxMessageIdsPage() {
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")

  const mailbox = useQuery({
    queryKey: ["ingestion", "mailbox-runs", "message-id-view"],
    queryFn: () => IngestionApi.listMailboxRuns({ limit: 300 }),
  })
  const rejected = useQuery({
    queryKey: ["ingestion", "rejected-central", "message-id-view"],
    queryFn: () => IngestionApi.listRejectedCentral({ limit: 200 }),
  })
  const unmapped = useQuery({
    queryKey: ["ingestion", "internal-unmapped", "message-id-view"],
    queryFn: () => IngestionApi.listInternalUnmapped({ limit: 200 }),
  })
  const byMessageId = useQuery({
    queryKey: ["ingestion", "by-message-id", selectedMessageId],
    queryFn: async () => {
      if (!selectedMessageId) throw new Error("No message-id selected")
      return IngestionApi.getByMessageId(selectedMessageId)
    },
    enabled: !!selectedMessageId,
  })

  const allMessageIds = useMemo(() => {
    const ids = new Set<string>()
    for (const item of mailbox.data?.data ?? []) {
      if (item.run.source_message_id_norm) ids.add(item.run.source_message_id_norm)
    }
    for (const row of rejected.data?.data ?? []) {
      if (row.message_id_norm) ids.add(row.message_id_norm)
    }
    for (const row of unmapped.data?.data ?? []) {
      if (row.message_id_norm) ids.add(row.message_id_norm)
    }
    return Array.from(ids).sort((a, b) => a.localeCompare(b))
  }, [mailbox.data?.data, rejected.data?.data, unmapped.data?.data])

  const filteredIds = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    if (!q) return allMessageIds
    return allMessageIds.filter((mid) => mid.toLowerCase().includes(q))
  }, [allMessageIds, searchQuery])

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Message ID Explorer</h1>
        <p className="text-sm text-muted-foreground">
          Browse persisted message IDs and inspect comprehensive ingestion payload by message ID.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[340px_1fr]">
        <div className="rounded-md border">
          <div className="border-b p-3">
            <div className="mb-2 text-sm font-medium">All persisted Message-IDs</div>
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search message-id..."
              className="h-9 w-full rounded-md border px-3 text-sm"
            />
            <p className="mt-2 text-xs text-muted-foreground">
              {filteredIds.length} shown / {allMessageIds.length} total
            </p>
          </div>
          <div className="max-h-[560px] overflow-auto p-2">
            {filteredIds.map((mid) => (
              <button
                key={mid}
                type="button"
                onClick={() => setSelectedMessageId(mid)}
                className={`mb-1 w-full rounded border px-2 py-1 text-left font-mono text-xs hover:bg-muted ${
                  selectedMessageId === mid ? "bg-muted" : ""
                }`}
              >
                {mid}
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-md border">
          <div className="border-b px-3 py-2 text-sm font-medium">Comprehensive data by Message-ID</div>
          <div className="max-h-[640px] overflow-auto p-3">
            {!selectedMessageId && (
              <p className="text-xs text-muted-foreground">Select a message-id from the left list.</p>
            )}
            {selectedMessageId && byMessageId.isLoading && (
              <p className="text-xs text-muted-foreground">Loading comprehensive payload...</p>
            )}
            {selectedMessageId && byMessageId.data && (
              <pre className="whitespace-pre-wrap break-all text-xs">
                {JSON.stringify(byMessageId.data, null, 2)}
              </pre>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
