#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-http://localhost:8000}
SHOWTIME_ID=${SHOWTIME_ID:-1}
SEAT_ID=${SEAT_ID:-5}
GATEWAY_SECRET=${GATEWAY_SECRET:-z2p-2026-secret}
OUTPUT_FILE=${OUTPUT_FILE:-loadtest/results/fresh_duplicate_callback_raw.txt}

work_dir=$(mktemp -d)
trap 'rm -rf "$work_dir"' EXIT
mkdir -p "$(dirname "$OUTPUT_FILE")"

hold_body=$(curl --silent --show-error --request POST "$BASE_URL/api/v1/showtimes/$SHOWTIME_ID/holds" \
  --header 'Content-Type: application/json' \
  --data "{\"seat_id\":$SEAT_ID,\"customer_email\":\"fresh-duplicate@example.com\"}")
hold_id=$(jq -r '.hold_id' <<<"$hold_body")
pay_body=$(curl --silent --show-error --request POST "$BASE_URL/api/v1/pay" \
  --header 'Content-Type: application/json' \
  --header 'X-Mock-Force: timeout' \
  --data "{\"hold_id\":\"$hold_id\",\"currency\":\"BDT\"}")
booking_ref=$(jq -r '.booking_ref' <<<"$pay_body")
event_id="evt_fresh_$(date +%s%N)"
gateway_payment_id="pay_fresh_$(date +%s%N)"
raw_body="{\"event_id\":\"$event_id\",\"payment_id\":\"$gateway_payment_id\",\"booking_ref\":\"$booking_ref\",\"status\":\"SUCCEEDED\",\"amount\":450,\"currency\":\"BDT\",\"timestamp\":\"2026-08-08T07:00:00Z\"}"
signature=$(printf '%s' "$raw_body" | openssl dgst -sha256 -hmac "$GATEWAY_SECRET" | awk '{print $2}')

run_callback() {
  request_id=$1
  curl --silent --show-error \
    --output "$work_dir/body_$request_id.json" \
    --write-out "%{http_code}" \
    --request POST "$BASE_URL/api/v1/payments/callback" \
    --header 'Content-Type: application/json' \
    --header "X-Signature: $signature" \
    --data-binary "$raw_body" >"$work_dir/status_$request_id.txt"
}

run_callback 1 &
first_pid=$!
run_callback 2 &
second_pid=$!
wait "$first_pid"
wait "$second_pid"

first_status=$(<"$work_dir/status_1.txt")
second_status=$(<"$work_dir/status_2.txt")
first_result=$(jq -r '.result' "$work_dir/body_1.json")
second_result=$(jq -r '.result' "$work_dir/body_2.json")
db_state=$(docker compose exec -T db psql -U cinemaseat -d cinemaseat -At -F '|' -c \
  "select p.status,p.revenue_counted,(select count(*) from payment_events e where e.payment_id=p.id),(select count(*) from bookings b where b.hold_id=p.hold_id) from payments p where p.booking_ref='$booking_ref'")

{
  echo "CinemaSeat concurrent fresh duplicate callback run"
  echo "booking_ref=$booking_ref"
  echo "event_id=$event_id"
  echo "request_1_http=$first_status result=$first_result"
  echo "request_2_http=$second_status result=$second_result"
  echo "db_payment_status|revenue_counted|event_count|booking_count=$db_state"
} | tee "$OUTPUT_FILE"

test "$first_status" = "200"
test "$second_status" = "200"
test "$(printf '%s\n%s\n' "$first_result" "$second_result" | grep -c '^confirmed$')" -eq 1
test "$(printf '%s\n%s\n' "$first_result" "$second_result" | grep -c '^duplicate$')" -eq 1
test "$db_state" = "SUCCEEDED|t|1|1"
