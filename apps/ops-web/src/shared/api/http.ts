import i18n from "@/i18n";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json();
    // FastAPI sends { detail: string } for handled errors and a list for validation
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && body.detail[0]?.msg)
      return body.detail[0].msg;
  } catch {
    // Not JSON; fall back to the status text
  }
  return (
    response.statusText ||
    i18n.t("errors.requestFailed", { status: response.status })
  );
}

export async function request<T>(
  url: string,
  init: RequestInit = {},
): Promise<T> {
  const isForm = init.body instanceof FormData;
  const response = await fetch(url, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init.body && !isForm ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  });

  if (!response.ok)
    throw new ApiError(response.status, await errorMessage(response));
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const http = {
  get: <T>(url: string, signal?: AbortSignal) => request<T>(url, { signal }),
  post: <T>(url: string, body?: unknown) =>
    request<T>(url, {
      method: "POST",
      body:
        body instanceof FormData
          ? body
          : body === undefined
            ? undefined
            : JSON.stringify(body),
    }),
  put: <T>(url: string, body: unknown) =>
    request<T>(url, { method: "PUT", body: JSON.stringify(body) }),
  patch: <T>(url: string, body: unknown) =>
    request<T>(url, { method: "PATCH", body: JSON.stringify(body) }),
  delete: (url: string) => request<void>(url, { method: "DELETE" }),
};
