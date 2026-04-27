import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useEffect, useMemo, useState } from "react"

import { UsersService } from "@/client"
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
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useCustomToast from "@/hooks/useCustomToast"
import { MailAccessApi } from "@/lib/api/mailAccessApi"
import { handleError } from "@/utils"

export const Route = createFileRoute("/_layout/mail-access")({
  component: MailAccessPage,
})

function MailAccessPage() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [email, setEmail] = useState("")
  const [appPassword, setAppPassword] = useState("")
  const [ingestionRetrievalPeriodMinutes, setIngestionRetrievalPeriodMinutes] = useState("")
  const [selectedUser, setSelectedUser] = useState("")
  const [userAccessType, setUserAccessType] = useState<
    "OrderUser" | "OrderInternalUser"
  >("OrderUser")
  const [userPassword, setUserPassword] = useState("")
  const [editingUserId, setEditingUserId] = useState("")
  const [isUserDialogOpen, setIsUserDialogOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<"central" | "order-user" | "internal-user">(
    "central",
  )
  const [page, setPage] = useState(1)
  const [revokeCandidate, setRevokeCandidate] = useState<{ userId: string; email: string } | null>(
    null,
  )

  const { data: centralMailbox } = useQuery({
    queryKey: ["centralMailbox"],
    queryFn: MailAccessApi.getCentralMailbox,
  })
  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: () => UsersService.readUsers({ limit: 100, skip: 0 }),
  })
  const { data: userMailAccesses } = useQuery({
    queryKey: ["userMailAccesses"],
    queryFn: MailAccessApi.listUserMailAccesses,
    placeholderData: (previousData) => previousData,
  })

  const saveCentralMailbox = useMutation({
    mutationFn: () => {
      const ingestionPeriod = ingestionRetrievalPeriodMinutes
        ? `${ingestionRetrievalPeriodMinutes} minutes`
        : undefined
      if (!centralMailbox || appPassword) {
        return MailAccessApi.upsertCentralMailbox({
          email,
          app_password: appPassword,
          ingestion_retrieval_period: ingestionPeriod,
        })
      }
      return MailAccessApi.updateCentralMailbox({
        email: email || undefined,
        ingestion_retrieval_period: ingestionPeriod,
      })
    },
    onSuccess: () => {
      showSuccessToast("Central mailbox saved")
      queryClient.invalidateQueries({ queryKey: ["centralMailbox"] })
      setAppPassword("")
    },
    onError: handleError.bind(showErrorToast),
  })

  const updateUserAccess = useMutation({
    mutationFn: (payload: {
      userId: string
      access_type?: "OrderUser" | "OrderInternalUser"
      app_password?: string
      is_active?: boolean
    }) =>
      MailAccessApi.updateUserMailAccess(payload.userId, {
        access_type: payload.access_type,
        app_password: payload.app_password,
        is_active: payload.is_active,
      }),
    onSuccess: () => {
      showSuccessToast("User mail access updated")
      queryClient.invalidateQueries({ queryKey: ["userMailAccesses"] })
      setUserPassword("")
      setEditingUserId("")
    },
    onError: handleError.bind(showErrorToast),
  })

  const grantUserAccess = useMutation({
    mutationFn: () =>
      MailAccessApi.grantUserMailAccess({
        user_id: selectedUser,
        access_type: userAccessType,
        app_password: userPassword,
      }),
    onSuccess: () => {
      showSuccessToast("User mail access updated")
      queryClient.invalidateQueries({ queryKey: ["userMailAccesses"] })
      setUserPassword("")
    },
    onError: handleError.bind(showErrorToast),
  })

  const revokeUserAccess = useMutation({
    mutationFn: (userId: string) => MailAccessApi.revokeUserMailAccess(userId),
    onSuccess: () => {
      showSuccessToast("User mail access revoked")
      queryClient.invalidateQueries({ queryKey: ["userMailAccesses"] })
    },
    onError: handleError.bind(showErrorToast),
  })

  const userMap = useMemo(() => {
    const map = new Map<string, string>()
    ;(users?.data ?? []).forEach((u) => {
      map.set(String(u.id), u.email)
    })
    return map
  }, [users?.data])

  const accessRowsRaw = (
    userMailAccesses as
      | {
          data?: Array<{
            id: string
            user_id: string
            access_type: "OrderUser" | "OrderInternalUser"
            is_active: boolean
          }>
        }
      | undefined
  )?.data
  const accessRows = Array.isArray(accessRowsRaw) ? accessRowsRaw : []
  const filteredAccessRows = accessRows
  const filteredOrderUsers = filteredAccessRows.filter(
    (row) => row.access_type === "OrderUser",
  )
  const filteredInternalUsers = filteredAccessRows.filter(
    (row) => row.access_type === "OrderInternalUser",
  )
  const pageSize = 8
  const activeRows =
    activeTab === "order-user" ? filteredOrderUsers : filteredInternalUsers
  const totalPages = Math.max(1, Math.ceil(activeRows.length / pageSize))
  const pagedRows = activeRows.slice((page - 1) * pageSize, page * pageSize)

  useEffect(() => {
    if (!centralMailbox) return
    setEmail(centralMailbox.email ?? "")
    const minutes = centralMailbox.ingestion_retrieval_period
      ?.toLowerCase()
      .replace("minutes", "")
      .trim()
    if (minutes) {
      setIngestionRetrievalPeriodMinutes(minutes)
    }
  }, [centralMailbox])

  const renderAccessRow = (entry: {
    id: string
    user_id: string
    access_type: "OrderUser" | "OrderInternalUser"
    is_active: boolean
  }) => (
    <div key={entry.id} className="flex flex-wrap items-center gap-2 rounded-md border px-3 py-2">
      <div className="min-w-72 flex-1">
        <p className="font-medium">{userMap.get(entry.user_id) ?? entry.user_id}</p>
        <p className="text-muted-foreground">
          {entry.access_type} • {entry.is_active ? "Active" : "Revoked"}
        </p>
      </div>
      <Button
        variant="outline"
        size="sm"
        onClick={() => {
          setEditingUserId(entry.user_id)
          setSelectedUser(entry.user_id)
          setUserAccessType(entry.access_type)
          setUserPassword("")
          setIsUserDialogOpen(true)
        }}
      >
        Edit
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={() =>
          updateUserAccess.mutate({
            userId: entry.user_id,
            is_active: !entry.is_active,
          })
        }
      >
        {entry.is_active ? "Deactivate" : "Activate"}
      </Button>
      <Button
        variant="destructive"
        size="sm"
        onClick={() =>
          setRevokeCandidate({
            userId: entry.user_id,
            email: userMap.get(entry.user_id) ?? entry.user_id,
          })
        }
      >
        Revoke
      </Button>
    </div>
  )

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Mail Access</h1>
        <p className="text-muted-foreground">
          Configure centralOrderMail and per-user IMAP/SMTP privileges.
        </p>
      </div>

      <Tabs
        value={activeTab}
        onValueChange={(value) => {
          const tab = value as "central" | "order-user" | "internal-user"
          setActiveTab(tab)
          setPage(1)
          setEditingUserId("")
          setSelectedUser("")
          setUserPassword("")
          setIsUserDialogOpen(false)
          if (tab === "order-user") {
            setUserAccessType("OrderUser")
          } else if (tab === "internal-user") {
            setUserAccessType("OrderInternalUser")
          }
        }}
        className="space-y-4"
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <TabsList>
            <TabsTrigger value="central">Central Email</TabsTrigger>
            <TabsTrigger value="order-user">OrderUser</TabsTrigger>
            <TabsTrigger value="internal-user">InternalOrderUser</TabsTrigger>
          </TabsList>
          <div />
        </div>

        <TabsContent value="central">
          <section className="space-y-3 rounded-lg border p-4">
            <h2 className="font-semibold">Central Order Mail</h2>
            <p className="text-muted-foreground text-sm">
              Single global mailbox configuration.
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <Label>Email</Label>
                <Input
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={centralMailbox?.email ?? "orders@example.com"}
                />
              </div>
              <div className="space-y-1">
                <Label>App Password</Label>
                <Input
                  type="password"
                  value={appPassword}
                  onChange={(e) => setAppPassword(e.target.value)}
                  placeholder="App password"
                />
              </div>
              <div className="space-y-1">
                <Label>Ingestion Retrieval Period</Label>
                <div className="flex items-center gap-2">
                  <Input
                    value={ingestionRetrievalPeriodMinutes}
                    onChange={(e) =>
                      setIngestionRetrievalPeriodMinutes(e.target.value.replace(/[^0-9]/g, ""))
                    }
                    placeholder={centralMailbox?.ingestion_retrieval_period?.replace(" minutes", "") ?? "15"}
                  />
                  <span className="text-muted-foreground text-sm">minutes</span>
                </div>
              </div>
            </div>
            <Button
              onClick={() => saveCentralMailbox.mutate()}
              disabled={
                !email ||
                !ingestionRetrievalPeriodMinutes ||
                saveCentralMailbox.isPending
              }
            >
              Save central mailbox
            </Button>
            <p className="text-muted-foreground text-xs">
              Keep app password empty to preserve existing password.
            </p>
            <p className="text-muted-foreground text-sm">
              Saved value: {centralMailbox?.ingestion_retrieval_period ?? "Not set"}
            </p>
          </section>
        </TabsContent>

        <TabsContent value="order-user">
          <section className="space-y-3 rounded-lg border p-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold">OrderUser Access (IMAP + SMTP)</h2>
              <Button
                onClick={() => {
                  setEditingUserId("")
                  setSelectedUser("")
                  setUserPassword("")
                  setUserAccessType("OrderUser")
                  setIsUserDialogOpen(true)
                }}
              >
                Add user access
              </Button>
            </div>
            <p className="text-muted-foreground text-sm">
              Total records: {filteredOrderUsers.length}
            </p>
            <div className="space-y-2">
              {pagedRows.length ? (
                pagedRows.map(renderAccessRow)
              ) : (
                <p className="text-muted-foreground text-sm">No OrderUser records found.</p>
              )}
            </div>
          </section>
        </TabsContent>

        <TabsContent value="internal-user">
          <section className="space-y-3 rounded-lg border p-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold">InternalOrderUser Access (IMAP only)</h2>
              <Button
                onClick={() => {
                  setEditingUserId("")
                  setSelectedUser("")
                  setUserPassword("")
                  setUserAccessType("OrderInternalUser")
                  setIsUserDialogOpen(true)
                }}
              >
                Add user access
              </Button>
            </div>
            <p className="text-muted-foreground text-sm">
              Total records: {filteredInternalUsers.length}
            </p>
            <div className="space-y-2">
              {pagedRows.length ? (
                pagedRows.map(renderAccessRow)
              ) : (
                <p className="text-muted-foreground text-sm">
                  No InternalOrderUser records found.
                </p>
              )}
            </div>
          </section>
        </TabsContent>
      </Tabs>
      {activeTab !== "central" ? (
        <div className="flex items-center justify-between">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            Prev
          </Button>
          <span className="text-muted-foreground text-sm">
            Page {page} of {totalPages}
          </span>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
          >
            Next
          </Button>
        </div>
      ) : null}
      <Dialog open={!!revokeCandidate} onOpenChange={(open) => !open && setRevokeCandidate(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Revoke mail access</DialogTitle>
            <DialogDescription>
              Revoke mailbox access for `{revokeCandidate?.email}`?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRevokeCandidate(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                if (!revokeCandidate) return
                revokeUserAccess.mutate(revokeCandidate.userId)
                setRevokeCandidate(null)
              }}
            >
              Revoke
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <Dialog open={isUserDialogOpen} onOpenChange={setIsUserDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingUserId ? "Edit user mail access" : "Add user mail access"}</DialogTitle>
            <DialogDescription>Set access type and optionally rotate app password.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-1">
              <Label>User</Label>
              <select
                className="h-11 w-full rounded-md border bg-transparent px-3 py-1 text-base sm:h-9 sm:text-sm"
                value={selectedUser}
                onChange={(e) => setSelectedUser(e.target.value)}
                disabled={!!editingUserId}
              >
                <option value="">Select user</option>
                {users?.data?.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.email}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <Label>Access Type</Label>
              <select
                className="h-11 w-full rounded-md border bg-transparent px-3 py-1 text-base sm:h-9 sm:text-sm"
                value={userAccessType}
                onChange={(e) => setUserAccessType(e.target.value as "OrderUser" | "OrderInternalUser")}
              >
                <option value="OrderUser">OrderUser (IMAP + SMTP)</option>
                <option value="OrderInternalUser">OrderInternalUser (IMAP only)</option>
              </select>
            </div>
            <div className="space-y-1">
              <Label>App Password {editingUserId ? "(optional)" : ""}</Label>
              <Input type="password" value={userPassword} onChange={(e) => setUserPassword(e.target.value)} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsUserDialogOpen(false)}>Cancel</Button>
            <Button
              onClick={() => {
                if (editingUserId) {
                  updateUserAccess.mutate({
                    userId: editingUserId,
                    access_type: userAccessType,
                    app_password: userPassword || undefined,
                  })
                  setIsUserDialogOpen(false)
                  return
                }
                grantUserAccess.mutate()
                setIsUserDialogOpen(false)
              }}
              disabled={
                !selectedUser ||
                !userAccessType ||
                (!editingUserId && !userPassword) ||
                grantUserAccess.isPending ||
                updateUserAccess.isPending
              }
            >
              {editingUserId ? "Update" : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
