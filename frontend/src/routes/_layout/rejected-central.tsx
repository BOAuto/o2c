import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { IngestionApi } from "@/lib/api/ingestionApi"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export const Route = createFileRoute("/_layout/rejected-central")({
  component: RejectedCentralPage,
})

function RejectedCentralPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["ingestion", "rejected-central"],
    queryFn: () => IngestionApi.listRejectedCentral({ limit: 200 }),
  })

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Rejected central senders</h1>
        <p className="text-muted-foreground text-sm">
          Messages received on the central order mailbox from senders that are not configured OrderUser
          addresses (<code className="text-xs">not_order_user</code> includes OrderInternalUser on
          central; <code className="text-xs">external</code> for other addresses).
        </p>
      </div>

      {isLoading && <p className="text-muted-foreground text-sm">Loading…</p>}
      {isError && (
        <p className="text-destructive text-sm">Could not load rejected senders. Are you a superuser?</p>
      )}

      {data && data.data.length === 0 && (
        <p className="text-muted-foreground text-sm">No rejected messages recorded yet.</p>
      )}

      {data && data.data.length > 0 && (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>From</TableHead>
                <TableHead>Subject</TableHead>
                <TableHead>Reason</TableHead>
                <TableHead>Message-ID</TableHead>
                <TableHead>IMAP UID</TableHead>
                <TableHead>Received</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.data.map((row) => (
                <TableRow key={row.id}>
                  <TableCell className="max-w-[200px] truncate font-mono text-xs">
                    {row.from_address}
                  </TableCell>
                  <TableCell className="max-w-[240px] truncate text-sm">{row.subject ?? "—"}</TableCell>
                  <TableCell className="text-sm">{row.rejection_reason}</TableCell>
                  <TableCell className="max-w-[160px] truncate font-mono text-xs">
                    {row.message_id_norm ?? "—"}
                  </TableCell>
                  <TableCell className="font-mono text-xs">{row.imap_uid}</TableCell>
                  <TableCell className="text-muted-foreground text-xs whitespace-nowrap">
                    {row.created_at ? new Date(row.created_at).toLocaleString() : "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
