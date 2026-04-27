import { OpenAPI } from "@/client"

type Method = "GET" | "POST" | "PATCH" | "PUT" | "DELETE"

export async function callApi<T>(
  path: string,
  method: Method,
  body?: unknown,
): Promise<T> {
  const token = localStorage.getItem("access_token")
  const response = await fetch(`${OpenAPI.BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!response.ok) {
    const errText = await response.text()
    throw new Error(errText || `Request failed with ${response.status}`)
  }
  if (response.status === 204) {
    return {} as T
  }
  return (await response.json()) as T
}
