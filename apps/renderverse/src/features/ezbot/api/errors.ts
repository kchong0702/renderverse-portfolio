import { FALLBACK_ERROR_CODE, RETRY_AFTER_HEADER } from "./constants";

export class EzbotApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly retryAfterS: number | null = null,
  ) {
    super(message);
    this.name = "EzbotApiError";
  }
}

export async function toApiError(response: Response): Promise<EzbotApiError> {
  let code = FALLBACK_ERROR_CODE;
  let message = `Ezbot request failed with status ${response.status}`;
  const body = await response.json().catch(() => null);
  if (body?.detail?.code) {
    code = body.detail.code;
    message = body.detail.message ?? message;
  }
  const retryAfter = Number(response.headers.get(RETRY_AFTER_HEADER));
  return new EzbotApiError(
    response.status,
    code,
    message,
    Number.isFinite(retryAfter) && retryAfter > 0 ? retryAfter : null,
  );
}
