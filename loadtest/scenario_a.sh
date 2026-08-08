#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-http://localhost:8000}
SHOWTIME_ID=${SHOWTIME_ID:-1}
SEAT_ID=${SEAT_ID:-7}
REQUESTS=${REQUESTS:-100}
OUTPUT_FILE=${OUTPUT_FILE:-loadtest/results/scenario_a_raw.txt}

mkdir -p "$(dirname "$OUTPUT_FILE")"
work_dir=$(mktemp -d)
trap 'rm -rf "$work_dir"' EXIT

export BASE_URL SHOWTIME_ID SEAT_ID work_dir

run_hold_request() {
  request_id=$1
  body_file="$work_dir/body_$request_id.json"
  metrics=$(curl --silent --show-error \
    --output "$body_file" \
    --write-out '%{http_code} %{time_total}' \
    --request POST "$BASE_URL/api/v1/showtimes/$SHOWTIME_ID/holds" \
    --header 'Content-Type: application/json' \
    --data "{\"seat_id\":$SEAT_ID,\"customer_email\":\"scenario-a-$request_id@example.com\"}")
  read -r http_status total_seconds <<<"$metrics"
  printf '%03d\t%s\t%s\t%s\n' \
    "$request_id" "$http_status" "$total_seconds" "$(tr -d '\n' < "$body_file")" \
    > "$work_dir/result_$request_id.txt"
}
export -f run_hold_request

started_at=$(date --utc +'%Y-%m-%dT%H:%M:%S.%3NZ')
start_ns=$(date +%s%N)
seq 1 "$REQUESTS" | xargs -P "$REQUESTS" -I '{}' bash -c 'run_hold_request "$1"' _ '{}'
end_ns=$(date +%s%N)
finished_at=$(date --utc +'%Y-%m-%dT%H:%M:%S.%3NZ')

sort -n -k1,1 "$work_dir"/result_*.txt > "$work_dir/all_results.txt"
successes=$(awk -F '\t' '$2 == 201 {count++} END {print count+0}' "$work_dir/all_results.txt")
conflicts=$(awk -F '\t' '$2 == 409 {count++} END {print count+0}' "$work_dir/all_results.txt")
other=$(awk -F '\t' '$2 != 201 && $2 != 409 {count++} END {print count+0}' "$work_dir/all_results.txt")
oversell_count=$((successes > 1 ? successes - 1 : 0))
duration_ms=$(((end_ns - start_ns) / 1000000))

seat_map=$(curl --silent --show-error "$BASE_URL/api/v1/showtimes/$SHOWTIME_ID/seats")
seat_status=$(jq -r --argjson seat_id "$SEAT_ID" '.seats[] | select(.id == $seat_id) | .status' <<<"$seat_map")
held_entries=$(jq --argjson seat_id "$SEAT_ID" '[.seats[] | select(.id == $seat_id and .status == "HELD")] | length' <<<"$seat_map")

{
  echo "CinemaSeat Scenario A raw run"
  echo "started_at=$started_at"
  echo "finished_at=$finished_at"
  echo "generator=host xargs/curl parallelism=$REQUESTS"
  echo "target=showtime:$SHOWTIME_ID seat:$SEAT_ID"
  echo "requests_sent=$REQUESTS"
  echo "burst_duration_ms=$duration_ms"
  echo
  echo -e "request_id\thttp_status\ttotal_seconds\tresponse_body"
  cat "$work_dir/all_results.txt"
  echo
  echo "summary_success_201=$successes"
  echo "summary_conflict_409=$conflicts"
  echo "summary_other=$other"
  echo "summary_oversell_count=$oversell_count"
  echo "seat_map_status_after_burst=$seat_status"
  echo "seat_map_held_entries_for_target=$held_entries"
  echo "seat_map_raw=$seat_map"
} | tee "$OUTPUT_FILE"

test "$successes" -eq 1
test "$conflicts" -eq $((REQUESTS - 1))
test "$other" -eq 0
test "$oversell_count" -eq 0
test "$seat_status" = "HELD"
test "$held_entries" -eq 1

