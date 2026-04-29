import { type ReactNode, useCallback, useEffect, useMemo, useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import {
  ArrowLeft,
  CircleAlert,
  Download,
  ExternalLink,
  Mail,
  MailOpen,
  Paperclip,
  RefreshCw,
  Search,
} from "lucide-react"

import { OpenAPI } from "@/client"
import { Button } from "@/components/ui/button"
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable"
import { useViewport } from "@/hooks/useViewport"
import { IngestionApi, type MailboxRunRow, type RunArtifact } from "@/lib/api/ingestionApi"
import { prepareInlineMailHtml } from "@/lib/mailHtml"
import { cn } from "@/lib/utils"

export const Route = createFileRoute("/_layout/mailbox")({
  component: MailboxPage,
})

type MailTab = "inbox" | "failed"

function TabButton({
  id,
  label,
  isActive,
  count,
  onClick,
}: {
  id: MailTab
  label: string
  isActive: boolean
  count: number
  onClick: (tab: MailTab) => void
}) {
  return (
    <button
      type="button"
      onClick={() => onClick(id)}
      className={cn(
        "inline-flex h-8 w-full items-center justify-center gap-1 rounded-md px-2 text-xs font-medium transition-colors focus-visible:ring-2 focus-visible:ring-ring/30 focus-visible:outline-none",
        isActive ? "bg-foreground text-background" : "text-foreground hover:bg-muted",
      )}
      aria-pressed={isActive}
    >
      <span className="truncate">{label}</span>
      <span
        className={cn(
          "hidden rounded-full px-1.5 py-0 text-[10px] sm:inline-flex",
          isActive ? "bg-background/20 text-background" : "bg-muted text-muted-foreground",
        )}
      >
        {count}
      </span>
    </button>
  )
}

async function fetchArtifactBlobUrl(
  runId: string,
  artifactId: string,
  disposition: "inline" | "attachment",
): Promise<{ url: string; revoke: () => void } | null> {
  const token = localStorage.getItem("access_token")
  const path = IngestionApi.getRunArtifactUrl(runId, artifactId, disposition)
  const res = await fetch(`${OpenAPI.BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) return null
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  return { url, revoke: () => URL.revokeObjectURL(url) }
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

function MailboxArtifactsBar({
  runId,
  artifacts,
  isLoading,
}: {
  runId: string
  artifacts: RunArtifact[]
  isLoading: boolean
}) {
  const poArts = useMemo(
    () => artifacts.filter((a) => a.artifact_kind === "po_attachment"),
    [artifacts],
  )
  const emlArt = useMemo(() => artifacts.find((a) => a.artifact_kind === "eml"), [artifacts])

  const openTab = async (artifactId: string) => {
    const r = await fetchArtifactBlobUrl(runId, artifactId, "inline")
    if (!r) return
    window.open(r.url, "_blank", "noopener,noreferrer")
    window.setTimeout(r.revoke, 120_000)
  }

  const download = async (artifactId: string, fileName: string) => {
    const r = await fetchArtifactBlobUrl(runId, artifactId, "attachment")
    if (!r) return
    const a = document.createElement("a")
    a.href = r.url
    a.download = fileName
    a.rel = "noopener"
    a.click()
    window.setTimeout(r.revoke, 5_000)
  }

  return (
    <div className="border-border bg-card shrink-0 border-t shadow-[0_-4px_12px_-4px_rgba(0,0,0,0.06)]">
      <div className="flex h-11 min-h-11 flex-nowrap items-center divide-x divide-border">
        <div className="flex min-h-11 min-w-0 flex-1 flex-nowrap items-center gap-2 px-2 py-1 sm:px-3">
          <span className="text-muted-foreground shrink-0 text-[10px] font-semibold tracking-wide uppercase">
            PO
          </span>
          {isLoading ? (
            <span className="text-muted-foreground text-xs">…</span>
          ) : poArts.length === 0 ? (
            <span className="text-muted-foreground text-xs">—</span>
          ) : (
            <div className="flex min-w-0 flex-1 flex-nowrap items-center gap-1.5 overflow-hidden">
              {poArts.map((art) => (
                <div
                  key={art.id}
                  className="border-border/80 bg-background flex h-8 max-w-[min(100%,12rem)] shrink-0 items-center gap-1 rounded-full border px-1.5"
                  title={`${art.file_name} (${formatBytes(art.size_bytes)})`}
                >
                  <Paperclip className="text-muted-foreground size-3.5 shrink-0" aria-hidden />
                  <span className="text-muted-foreground min-w-0 flex-1 truncate text-[11px]">
                    {art.file_name}
                  </span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="size-6 shrink-0"
                    title="Open"
                    onClick={() => void openTab(art.id)}
                  >
                    <ExternalLink className="size-3" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="size-6 shrink-0"
                    title="Download"
                    onClick={() => void download(art.id, art.file_name)}
                  >
                    <Download className="size-3" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="flex min-h-11 min-w-0 flex-1 flex-nowrap items-center gap-2 px-2 py-1 sm:px-3">
          <span className="text-muted-foreground shrink-0 text-[10px] font-semibold tracking-wide uppercase">
            EML
          </span>
          {isLoading ? (
            <span className="text-muted-foreground text-xs">…</span>
          ) : !emlArt ? (
            <span className="text-muted-foreground text-xs">—</span>
          ) : (
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="size-9 shrink-0 rounded-full"
              title={`Download EML (${emlArt.file_name}, ${formatBytes(emlArt.size_bytes)})`}
              onClick={() => void download(emlArt.id, emlArt.file_name)}
            >
              <Mail className="text-amber-600 size-5" aria-hidden />
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}

function EmptyListState({
  icon,
  title,
  description,
}: {
  icon: ReactNode
  title: string
  description: string
}) {
  return (
    <div className="text-muted-foreground flex min-h-[140px] flex-col items-center justify-center gap-1.5 px-3 py-6 text-center">
      <div className="rounded-full border border-border bg-card p-1.5">{icon}</div>
      <h3 className="text-foreground text-sm font-semibold">{title}</h3>
      <p className="max-w-md text-xs leading-snug">{description}</p>
    </div>
  )
}

function MailboxPage() {
  const queryClient = useQueryClient()
  const { isMobile, isTablet } = useViewport()
  const [pollBusy, setPollBusy] = useState(false)
  const [activeTab, setActiveTab] = useState<MailTab>("inbox")
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const [mobileReaderOpen, setMobileReaderOpen] = useState(false)
  const [htmlContent, setHtmlContent] = useState<string>("")
  const [searchQuery, setSearchQuery] = useState("")
  const [senderFilter, setSenderFilter] = useState<string>("all")
  const [statusFilter, setStatusFilter] = useState<"all" | "completed" | "in_progress">("all")

  const mailbox = useQuery({
    queryKey: ["ingestion", "mailbox-runs"],
    queryFn: () => IngestionApi.listMailboxRuns({ limit: 200 }),
  })
  const runs = mailbox.data?.data ?? []

  const tabCounts = useMemo(() => {
    const inbox = runs.filter((item) => item.run.status !== "failed").length
    const failed = runs.filter((item) => item.run.status === "failed").length
    return { inbox, failed }
  }, [runs])

  const tabRuns = useMemo(() => {
    if (activeTab === "inbox") {
      return runs.filter((item) => item.run.status !== "failed")
    }
    return runs.filter((item) => item.run.status === "failed")
  }, [runs, activeTab])

  const senderOptions = useMemo(() => {
    const unique = new Set<string>()
    for (const item of tabRuns) {
      if (item.run.source_from) unique.add(item.run.source_from)
    }
    return Array.from(unique).sort((a, b) => a.localeCompare(b))
  }, [tabRuns])

  const filteredRuns = useMemo(() => {
    const query = searchQuery.trim().toLowerCase()
    return tabRuns.filter((item) => {
      if (activeTab === "inbox" && statusFilter !== "all" && item.run.status !== statusFilter) {
        return false
      }
      const senderMatches =
        senderFilter === "all" ||
        (item.run.source_from ?? "").toLowerCase() === senderFilter.toLowerCase()
      if (!senderMatches) return false
      if (!query) return true
      const haystack = [
        item.run.source_subject ?? "",
        item.run.source_from ?? "",
        item.run.source_message_id_norm ?? "",
        item.run.external_correspondent_from ?? "",
        item.run.external_correspondent_domain ?? "",
      ]
        .join(" ")
        .toLowerCase()
      return haystack.includes(query)
    })
  }, [tabRuns, activeTab, searchQuery, senderFilter, statusFilter])

  const selected = useMemo(
    () => filteredRuns.find((r) => r.run.id === selectedRunId) ?? filteredRuns[0] ?? null,
    [filteredRuns, selectedRunId],
  )

  const runDetail = useQuery({
    queryKey: ["ingestion", "run-detail", selected?.run.id],
    queryFn: async () => {
      if (!selected?.run.id) throw new Error("No mailbox run selected")
      return IngestionApi.getRunDetail(selected.run.id)
    },
    enabled: !!selected?.run.id,
  })

  const loadHtml = useCallback(async (runId: string) => {
    const token = localStorage.getItem("access_token")
    const res = await fetch(`${OpenAPI.BASE}${IngestionApi.getMailboxRunHtmlUrl(runId)}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) {
      setHtmlContent(`<html><body><p>Could not load HTML preview (${res.status}).</p></body></html>`)
      return
    }
    const text = await res.text()
    setHtmlContent(text)
  }, [])

  useEffect(() => {
    if (!selected?.run.id) {
      setHtmlContent("")
      return
    }
    void loadHtml(selected.run.id)
  }, [loadHtml, selected?.run.id])

  const sanitizedHtml = useMemo(() => {
    try {
      return prepareInlineMailHtml(htmlContent)
    } catch {
      return '<p class="text-muted-foreground p-3 text-sm">Could not render message body.</p>'
    }
  }, [htmlContent])

  const onTabChange = (tab: MailTab) => {
    setActiveTab(tab)
    setSearchQuery("")
    setSenderFilter("all")
    setStatusFilter("all")
    setSelectedRunId(null)
    setMobileReaderOpen(false)
  }

  const onSelectRow = (item: MailboxRunRow) => {
    setSelectedRunId(item.run.id)
    if (isMobile) setMobileReaderOpen(true)
  }

  const listLoading = mailbox.isLoading

  const onPollCentralAndRefresh = async () => {
    setPollBusy(true)
    try {
      await IngestionApi.requestO2cPollNow()
    } catch {
      // Still refresh mailbox list; user may see partial results.
    } finally {
      await queryClient.invalidateQueries({ queryKey: ["ingestion"] })
      await mailbox.refetch()
      setPollBusy(false)
    }
  }

  const listPanel = (
    <section className="bg-card flex h-full min-h-0 flex-col overflow-hidden rounded-md border border-border/80 shadow-sm">
      <div className="border-border border-b px-1 py-1">
        <div className="mb-1 flex flex-wrap items-center gap-1">
          <Button
            type="button"
            variant="outline"
            size="icon"
            className="size-8 shrink-0"
            title="Poll central unread and refresh list"
            onClick={() => void onPollCentralAndRefresh()}
            disabled={pollBusy || mailbox.isFetching}
          >
            <RefreshCw className={`size-4 ${pollBusy || mailbox.isFetching ? "animate-spin" : ""}`} />
          </Button>
          <div className="min-w-[140px] flex-1 sm:min-w-[180px]">
            <label htmlFor="mailbox-sender" className="sr-only">
              Filter by sender
            </label>
            <select
              id="mailbox-sender"
              className="border-input bg-background h-9 w-full rounded-md border px-2 text-sm"
              value={senderFilter}
              onChange={(e) => {
                setSenderFilter(e.target.value)
                setSelectedRunId(null)
                if (isMobile) setMobileReaderOpen(false)
              }}
            >
              <option value="all">All senders</option>
              {senderOptions.map((sender) => (
                <option key={sender} value={sender}>
                  {sender}
                </option>
              ))}
            </select>
          </div>
          {activeTab === "inbox" ? (
            <div className="min-w-[120px] flex-1 sm:min-w-[140px]">
              <label htmlFor="mailbox-status" className="sr-only">
                Filter by status
              </label>
              <select
                id="mailbox-status"
                className="border-input bg-background h-9 w-full rounded-md border px-2 text-sm"
                value={statusFilter}
                onChange={(e) =>
                  setStatusFilter(e.target.value as "all" | "completed" | "in_progress")
                }
              >
                <option value="all">All (inbox)</option>
                <option value="completed">Completed</option>
                <option value="in_progress">In progress</option>
              </select>
            </div>
          ) : null}
        </div>
        <div className="relative">
          <Search className="pointer-events-none absolute top-2.5 left-2.5 size-3.5 text-muted-foreground" />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search subject, sender, message-id, external…"
            className="border-input bg-background h-9 w-full rounded-md border py-2 pr-3 pl-8 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/30"
          />
        </div>
        <div className="mt-1 text-[11px] text-muted-foreground">
          Showing {filteredRuns.length} of {tabRuns.length} in this tab
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-0.5 py-0.5">
        {listLoading ? (
          <p className="text-muted-foreground p-4 text-sm">Loading…</p>
        ) : filteredRuns.length === 0 ? (
          <EmptyListState
            icon={
              activeTab === "failed" ? (
                <CircleAlert className="size-5" />
              ) : (
                <Search className="size-5" />
              )
            }
            title={activeTab === "failed" ? "No failed runs" : "No messages match"}
            description={
              activeTab === "failed"
                ? "Failed ingestion runs appear here. Adjust filters or refresh after workflows complete."
                : "Try another sender filter or search terms."
            }
          />
        ) : (
          <ul className="space-y-1">
            {filteredRuns.map((item) => {
              const isSelected = selected?.run.id === item.run.id
              return (
                <li
                  key={item.run.id}
                  className={cn(
                    "rounded-md border p-1 transition-colors",
                    isSelected ? "border-primary/40 bg-muted" : "border-border bg-background hover:bg-muted/60",
                  )}
                >
                  <button
                    type="button"
                    onClick={() => onSelectRow(item)}
                    className="w-full text-left"
                  >
                    <div className="mb-0.5 flex items-center gap-1.5">
                      <p className="truncate text-xs font-semibold sm:text-sm">
                        {item.run.source_from || "—"}
                      </p>
                      <span className="ml-auto shrink-0 text-xs text-muted-foreground">
                        {item.run.source_received_at
                          ? new Date(item.run.source_received_at).toLocaleString()
                          : item.run.created_at
                            ? new Date(item.run.created_at).toLocaleString()
                            : "—"}
                      </span>
                    </div>
                    <p className="line-clamp-1 text-xs font-medium sm:text-sm">
                      {item.run.source_subject || "(No subject)"}
                    </p>
                    <div className="mt-0.5 flex flex-wrap gap-0.5">
                      <span className="rounded-full border border-border/80 px-1.5 py-px text-[10px] text-muted-foreground">
                        {item.run.status}
                      </span>
                      {item.run.external_correspondent_from ? (
                        <span className="rounded-full border border-border/80 px-1.5 py-px text-[10px] text-muted-foreground">
                          external
                        </span>
                      ) : null}
                    </div>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </section>
  )

  const readingPane = (
    <section className="bg-card flex h-full min-h-0 flex-col overflow-hidden rounded-md border border-border/80 shadow-sm">
      <div className="border-border bg-card z-10 flex min-h-9 shrink-0 flex-wrap items-center gap-1 border-b px-2 py-1">
        {isMobile ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-8"
            onClick={() => setMobileReaderOpen(false)}
          >
            <ArrowLeft className="mr-1 size-4" />
            Back
          </Button>
        ) : null}
        <span className="text-muted-foreground ml-auto truncate text-xs sm:ml-0">
          {selected ? selected.run.source_subject || "Reading pane" : "Reading pane"}
        </span>
      </div>

      {!selected ? (
        <div className="min-h-0 min-w-0 flex-1 overflow-x-auto overflow-y-auto overscroll-contain [-webkit-overflow-scrolling:touch] touch-pan-x touch-pan-y">
          <EmptyListState
            icon={<MailOpen className="size-5" />}
            title="Select a message"
            description="Choose a run from the list to preview stored HTML and artifacts."
          />
        </div>
      ) : (
        <>
          {/* One scroll container only: padding lives here so inner markup cannot create a nested scroller. */}
          <div
            className={cn(
              "min-h-0 min-w-0 flex-1 overflow-x-auto overflow-y-auto overscroll-contain px-2 py-2 sm:px-3 sm:py-3",
              "[-webkit-overflow-scrolling:touch] touch-pan-x touch-pan-y",
            )}
          >
            {sanitizedHtml ? (
              <div
                className="mail-html-content text-foreground **:max-w-full max-w-none overflow-visible text-[13px] leading-normal wrap-break-word [&_img]:h-auto [&_img]:max-w-full [&_table]:max-w-full"
                // biome-ignore lint/security/noDangerouslySetInnerHtml: sanitized with DOMPurify; HTML is from our ingestion API
                dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
              />
            ) : (
              <p className="text-muted-foreground text-sm">No HTML body for this message.</p>
            )}
          </div>
          <MailboxArtifactsBar
            runId={selected.run.id}
            artifacts={runDetail.data?.artifacts ?? []}
            isLoading={runDetail.isLoading}
          />
        </>
      )}
    </section>
  )

  return (
    <div className="flex min-h-[calc(100vh-220px)] flex-col gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Mailbox</h1>
        <p className="text-muted-foreground text-sm">
          Order-user inbox with inbox / failed tabs, filters, and reading pane.
        </p>
      </div>

      <div className="shrink-0 rounded-md border border-border/80 bg-card p-0.5 shadow-sm">
        <div className="grid grid-cols-2 gap-1">
          <TabButton
            id="inbox"
            label="Inbox"
            isActive={activeTab === "inbox"}
            count={tabCounts.inbox}
            onClick={onTabChange}
          />
          <TabButton
            id="failed"
            label="Failed"
            isActive={activeTab === "failed"}
            count={tabCounts.failed}
            onClick={onTabChange}
          />
        </div>
      </div>

      <main className="min-h-0 flex-1 overflow-hidden">
        {isMobile ? (
          <div className="h-[min(70vh,640px)] min-h-0 overflow-hidden">{listPanel}</div>
        ) : isTablet ? (
          <div className="grid h-[min(72vh,720px)] min-h-0 grid-cols-[minmax(240px,38%)_minmax(0,1fr)] gap-2 overflow-hidden md:gap-3">
            {listPanel}
            {readingPane}
          </div>
        ) : (
          <div className="flex h-[min(72vh,760px)] min-h-0 overflow-hidden rounded-md border border-border/80 bg-muted/15 p-0 shadow-sm">
            <ResizablePanelGroup direction="horizontal" className="h-full min-h-0 w-full">
              <ResizablePanel defaultSize={34} minSize={22} className="min-h-0 min-w-0">
                <div className="box-border h-full min-h-0 min-w-0 overflow-hidden pr-0.5 md:pr-1">
                  {listPanel}
                </div>
              </ResizablePanel>
              <ResizableHandle className="bg-border/80 w-px" />
              <ResizablePanel defaultSize={66} minSize={28} className="min-h-0 min-w-0">
                <div className="box-border h-full min-h-0 min-w-0 overflow-hidden pl-0.5 md:pl-1">
                  {readingPane}
                </div>
              </ResizablePanel>
            </ResizablePanelGroup>
          </div>
        )}

        {isMobile && mobileReaderOpen ? (
          <div className="fixed inset-0 z-50 overflow-hidden bg-background/95 p-1 backdrop-blur-sm">
            {readingPane}
          </div>
        ) : null}
      </main>
    </div>
  )
}
