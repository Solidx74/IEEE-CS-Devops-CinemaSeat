#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-http://localhost:8000}
CALLBACK_COUNT=${CALLBACK_COUNT:-100}
GATEWAY_SECRET=${GATEWAY_SECRET:-z2p-2026-secret}
BOOKING_REF=${BOOKING_REF:?Set BOOKING_REF to an existing payment booking_ref}
GATEWAY_PAYMENT_ID=${GATEWAY_PAYMENT_ID:?Set GATEWAY_PAYMENT_ID to the existing payment gateway id}
EVENT_ID=${EVENT_ID:?Set EVENT_ID to an already-recorded event id}
OUTPUT_FILE=${OUTPUT_FILE:-loadtest/results/callback_latency_raw.txt}

mkdir -p "$(dirname "$OUTPUT_FILE")"
work_dir=$(mktemp -d)
trap 'rm -rf "$work_dir"' EXIT

raw_body="{\"event_id\":\"$EVENT_ID\",\"payment_id\":\"$GATEWAY_PAYMENT_ID\",\"booking_ref\":\"$BOOKING_REF\",\"status\":\"SUCCEEDED\",\"amount\":450,\"currency\":\"BDT\",\"timestamp\":\"2026-08-08T05:21:09.058Z\"}"
signature=$(printf '%s' "$raw_body" | openssl dgst -sha256 -hmac "$GATEWAY_SECRET" -hex | awk '{print $2}')

export BASE_URL raw_body signature work_dir
run_callback() {
  request_id=$1
  metrics=$(curl --silent --show-error \
    --output "$work_dir/body_$request_id.json" \
    --write-out '%{http_code} %{time_total}' \
    --request POST "$BASE_URL/api/v1/payments/callback" \
    --header 'Content-Type: application/json' \
    --header "X-Signature: $signature" \
    --data-binary "$raw_body")
  read -r http_status total_seconds <<<"$metrics"
  printf '%03d\t%s\t%s\t%s\n' \
    "$request_id" "$http_status" "$total_seconds" "$(tr -d '\n' < "$work_dir/body_$request_id.json")" \
    > "$work_dir/result_$request_id.txt"
}
export -f run_callback

started_at=$(date --utc +'%Y-%m-%dT%H:%M:%S.%3NZ')
start_ns=$(date +%s%N)
seq 1 "$CALLBACK_COUNT" | xargs -P "$CALLBACK_COUNT" -I '{}' bash -c 'run_callback "$1"' _ '{}'
end_ns=$(date +%s%N)
finished_at=$(date --utc +'%Y-%m-%dT%H:%M:%S.%3NZ')

sort -n -k1,1 "$work_dir"/result_*.txt > "$work_dir/all_results.txt"
awk -F '\t' '{print $3}' "$work_dir/all_results.txt" | sort -n > "$work_dir/latencies.txt"
successes=$(awk -F '\t' '$2 == 200 {count++} END {print count+0}' "$work_dir/all_results.txt")
others=$((CALLBACK_COUNT - successes))
p50_index=$(((CALLBACK_COUNT * 50 + 99) / 100))
p95_index=$(((CALLBACK_COUNT * 95 + 99) / 100))
p50=$(sed -n "${p50_index}p" "$work_dir/latencies.txt")
p95=$(sed -n "${p95_index}p" "$work_dir/latencies.txt")
max=$(tail -n 1 "$work_dir/latencies.txt")
duration_ms=$(((end_ns - start_ns) / 1000000))

{
  echo "CinemaSeat callback row-lock latency run"
  echo "started_at=$started_at"
  echo "finished_at=$finished_at"
  echo "generator=host xargs/curl parallelism=$CALLBACK_COUNT"
  echo "booking_ref=$BOOKING_REF"
  echo "event_id=$EVENT_ID"
  echo "burst_duration_ms=$duration_ms"
  echo
  echo -e "request_id\thttp_status\ttotal_seconds\tresponse_body"
  cat "$work_dir/all_results.txt"
  echo
  echo "summary_http_200=$successes"
  echo "summary_other=$others"
  echo "summary_p50_seconds=$p50"
  echo "summary_p95_seconds=$p95"
  echo "summary_max_seconds=$max"
  echo "gateway_callback_timeout_seconds=5"
} | tee "$OUTPUT_FILE"

test "$successes" -eq "$CALLBACK_COUNT"
max_whole_seconds=${max%%.*}
test "$max_whole_seconds" -lt 5
