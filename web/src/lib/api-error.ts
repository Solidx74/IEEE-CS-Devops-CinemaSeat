export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/** status 0 means the request never reached a server. */
export function isOffline(error: unknown) {
  return error instanceof ApiError && error.status === 0;
}
