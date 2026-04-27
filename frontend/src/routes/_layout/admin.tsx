import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Suspense, useMemo, useState } from "react"

import { type UserPublic, UsersService } from "@/client"
import AddUser from "@/components/Admin/AddUser"
import { columns, type UserTableData } from "@/components/Admin/columns"
import { DataTable } from "@/components/Common/DataTable"
import { Input } from "@/components/ui/input"
import PendingUsers from "@/components/Pending/PendingUsers"
import useAuth from "@/hooks/useAuth"

function getUsersQueryOptions() {
  return {
    queryFn: () => UsersService.readUsers({ skip: 0, limit: 100 }),
    queryKey: ["users"],
  }
}

export const Route = createFileRoute("/_layout/admin")({
  component: Admin,
  beforeLoad: async () => {
    const user = await UsersService.readUserMe()
    if (!user.is_superuser) {
      throw redirect({
        to: "/",
      })
    }
  },
  head: () => ({
    meta: [
      {
        title: "Admin - FastAPI Template",
      },
    ],
  }),
})

function UsersTableContent({ search }: { search: string }) {
  const { user: currentUser } = useAuth()
  const { data: users } = useSuspenseQuery(getUsersQueryOptions())

  const tableData: UserTableData[] = users.data.map((user: UserPublic) => ({
    ...user,
    isCurrentUser: currentUser?.id === user.id,
  }))
  const filteredData = useMemo(() => {
    if (!search.trim()) {
      return tableData
    }
    const q = search.toLowerCase()
    return tableData.filter(
      (user) =>
        user.email.toLowerCase().includes(q) ||
        (user.full_name ?? "").toLowerCase().includes(q),
    )
  }, [tableData, search])

  return <DataTable columns={columns} data={filteredData} />
}

function UsersTable({ search }: { search: string }) {
  return (
    <Suspense fallback={<PendingUsers />}>
      <UsersTableContent search={search} />
    </Suspense>
  )
}

function Admin() {
  const [search, setSearch] = useState("")

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Users</h1>
          <p className="text-muted-foreground">
            Manage user accounts and permissions
          </p>
        </div>
        <div className="self-start sm:self-auto">
          <AddUser />
        </div>
      </div>
      <Input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search users by email or name"
        className="max-w-sm"
      />
      <UsersTable search={search} />
    </div>
  )
}
