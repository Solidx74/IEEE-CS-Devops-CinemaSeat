import { ApiError } from "@/lib/api-error";
import type {
  Hold,
  Movie,
  Payment,
  PaymentInit,
  SeatMapResponse,
} from "@/types/booking";

export { ApiError };

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
    });
  } catch {
    throw new ApiError(
      0,
      "Can't reach the booking service. Check your connection and try again.",
    );
  }

  const text = await res.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = null;
    }
  }

  if (!res.ok) {
    const detail = getErrorDetail(body, res.status);
    throw new ApiError(res.status, detail);
  }

  return body as T;
}

function getErrorDetail(body: unknown, status: number): string {
  if (!body || typeof body !== "object" || !("detail" in body)) {
    return `Request failed (${status})`;
  }

  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    const messages = detail.flatMap((item) => {
      if (!item || typeof item !== "object" || !("msg" in item)) return [];
      const message = (item as { msg?: unknown }).msg;
      if (typeof message !== "string") return [];

      const location = (item as { loc?: unknown }).loc;
      const path = Array.isArray(location)
        ? location.filter((part) => typeof part === "string" || typeof part === "number")
        : [];
      const label = path.length > 1 ? `${path.slice(1).join(".")}: ` : "";
      return [`${label}${message}`];
    });
    if (messages.length > 0) return messages.join("; ");
  }

  return `Request failed (${status})`;
}

export const api = {
  getMovies: () => request<Movie[]>("/movies"),

  getSeats: (showtimeId: string) =>
    request<SeatMapResponse>(`/showtimes/${showtimeId}/seats`),

  createHold: (showtimeId: string, seatId: string, customerEmail: string) =>
    request<Hold>(`/showtimes/${showtimeId}/holds`, {
      method: "POST",
      body: JSON.stringify({
        seat_id: seatId,
        customer_email: customerEmail,
      }),
    }),

  pay: (holdId: string) =>
    request<PaymentInit>("/pay", {
      method: "POST",
      headers: { "X-Mock-Mode": "deterministic" },
      body: JSON.stringify({ hold_id: holdId, currency: "BDT" }),
    }),

  getPayment: (paymentId: string) =>
    request<Payment>(`/payments/${paymentId}`),

  sendOtp: (phone: string) =>
    request<{ ref: string; status: string }>("/otp/send", {
      method: "POST",
      body: JSON.stringify({ phone }),
    }),

  verifyOtp: (ref: string, code: string) =>
    request<{ ref: string; verified: boolean; error?: string }>(
      "/otp/verify",
      { method: "POST", body: JSON.stringify({ ref, code }) },
    ),
};
