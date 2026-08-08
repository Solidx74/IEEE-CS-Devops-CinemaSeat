export type SeatStatus = "AVAILABLE" | "HELD" | "BOOKED";
export type SeatType = "STANDARD" | "PREMIUM";

export interface Showtime {
  id: string;
  starts_at: string;
  price: number;
  theatre_id: string;
  theatre_name: string;
}

export interface Movie {
  id: string;
  title: string;
  description: string;
  duration_minutes: number;
  poster_url: string;
  showtimes: Showtime[];
}

export interface Seat {
  id: string;
  row_label: string;
  seat_number: number;
  seat_type: SeatType | string;
  status: SeatStatus;
}

export interface SeatMapResponse {
  showtime_id: string;
  movie_title: string;
  theatre_name: string;
  starts_at: string;
  price: number;
  seats: Seat[];
}

export interface Hold {
  hold_id: string;
  showtime_id: string;
  seat_id: string;
  status: string;
  expires_at: string;
  ttl_seconds: number;
}

export interface PaymentInit {
  payment_id: string;
  booking_ref: string;
  status: string;
  poll_url: string;
}

export type PaymentStatusValue =
  | "PENDING"
  | "INITIATING"
  | "SUCCEEDED"
  | "FAILED"
  | "INITIATION_FAILED"
  | "SUCCEEDED_NO_HOLD"
  | "CONFLICT_REFUND_REQUIRED"
  | "REFUNDED";

export interface Payment {
  payment_id: string;
  booking_ref: string;
  gateway_payment_id: string | null;
  status: PaymentStatusValue | string;
  amount: number;
  currency: string;
  booking_confirmed: boolean;
  created_at: string;
}

export type BookingStep = "browse" | "seats" | "hold" | "pay" | "ticket";
