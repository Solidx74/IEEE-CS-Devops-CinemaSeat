#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-http://localhost:8000}
SHOWTIME_ID=${SHOWTIME_ID:-1}
SEAT_ID=${SEAT_ID:-8}
OUTPUT_FILE=${OUTPUT_FILE:-loadtest/results/scenario_b_raw.txt}

mkdir -p "$(dirname "$OUTPUT_FILE")"
exec > >(tee "$OUTPUT_FILE") 2>&1

timestamp() {
  date --utc +'%Y-%m-%dT%H:%M:%S.%3NZ'
}

seat_status() {
  curl --silent --show-error "$BASE_URL/api/v1/showtimes/$SHOWTIME_ID/seats" \
    | jq -r --argjson seat_id "$SEAT_ID" '.seats[] | select(.id == $seat_id) | .status'
}

echo "CinemaSeat Scenario B raw run"
echo "generator=host bash/curl"
echo "target=showtime:$SHOWTIME_ID seat:$SEAT_ID"
echo "timeline_initial_at=$(timestamp) status=$(seat_status)"

first_body_file=$(mktemp)
trap 'rm -f "$first_body_file"' EXIT
first_code=$(curl --silent --show-error --output "$first_body_file" --write-out '%{http_code}' \
  --request POST "$BASE_URL/api/v1/showtimes/$SHOWTIME_ID/holds" \
  --header 'Content-Type: application/json' \
  --data "{\"seat_id\":$SEAT_ID,\"customer_email\":\"abandoning-user@example.com\"}")
first_body=$(tr -d '\n' < "$first_body_file")
ttl_seconds=$(jq -r '.ttl_seconds' <<<"$first_body")
first_hold_id=$(jq -r '.hold_id' <<<"$first_body")
echo "timeline_first_hold_at=$(timestamp) http_status=$first_code hold_id=$first_hold_id ttl_seconds=$ttl_seconds body=$first_body"
echo "timeline_held_at=$(timestamp) status=$(seat_status)"
test "$first_code" -eq 201
test "$ttl_seconds" -le 10

sleep $((ttl_seconds + 1))
available_status=$(seat_status)
echo "timeline_after_expiry_at=$(timestamp) waited_seconds=$((ttl_seconds + 1)) status=$available_status"
test "$available_status" = "AVAILABLE"

second_body_file=$(mktemp)
second_code=$(curl --silent --show-error --output "$second_body_file" --write-out '%{http_code}' \
  --request POST "$BASE_URL/api/v1/showtimes/$SHOWTIME_ID/holds" \
  --header 'Content-Type: application/json' \
  --data "{\"seat_id\":$SEAT_ID,\"customer_email\":\"booking-user@example.com\"}")
second_body=$(tr -d '\n' < "$second_body_file")
second_hold_id=$(jq -r '.hold_id' <<<"$second_body")
echo "timeline_second_hold_at=$(timestamp) http_status=$second_code hold_id=$second_hold_id body=$second_body"
test "$second_code" -eq 201

pay_body_file=$(mktemp)
pay_code=$(curl --silent --show-error --output "$pay_body_file" --write-out '%{http_code}' \
  --request POST "$BASE_URL/api/v1/pay" \
  --header 'Content-Type: application/json' \
  --header 'X-Mock-Mode: deterministic' \
  --data "{\"hold_id\":\"$second_hold_id\",\"currency\":\"BDT\"}")
pay_body=$(tr -d '\n' < "$pay_body_file")
payment_id=$(jq -r '.payment_id' <<<"$pay_body")
booking_ref=$(jq -r '.booking_ref' <<<"$pay_body")
echo "timeline_pay_accepted_at=$(timestamp) http_status=$pay_code payment_id=$payment_id booking_ref=$booking_ref body=$pay_body"
test "$pay_code" -eq 202

terminal_status=""
payment_body=""
for attempt in $(seq 1 15); do
  payment_body=$(curl --silent --show-error "$BASE_URL/api/v1/payments/$payment_id")
  terminal_status=$(jq -r '.status' <<<"$payment_body")
  if [[ "$terminal_status" != "PENDING" && "$terminal_status" != "INITIATING" ]]; then
    break
  fi
  sleep 1
done

final_seat_status=$(seat_status)
echo "timeline_terminal_at=$(timestamp) payment_status=$terminal_status seat_status=$final_seat_status payment_body=$payment_body"
echo "summary_first_user_abandoned=true"
echo "summary_expired_seat_became_available=$([[ "$available_status" = "AVAILABLE" ]] && echo true || echo false)"
echo "summary_second_user_hold_http_status=$second_code"
echo "summary_second_user_booking_confirmed=$(jq -r '.booking_confirmed' <<<"$payment_body")"
echo "summary_final_seat_status=$final_seat_status"

rm -f "$second_body_file" "$pay_body_file"
test "$terminal_status" = "SUCCEEDED"
test "$(jq -r '.booking_confirmed' <<<"$payment_body")" = "true"
test "$final_seat_status" = "BOOKED"
