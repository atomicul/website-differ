#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Usage: $0 <website-directory>"
    echo ""
    echo "Computes pairwise diff scores between consecutive snapshots"
    echo "of a website directory containing timestamped subdirectories."
    echo ""
    echo "Example: $0 websites/bunnyshell.com"
    exit 1
}

if [[ $# -ne 1 ]]; then
    usage
fi

website_dir="$1"

if [[ ! -d "$website_dir" ]]; then
    echo "Error: '$website_dir' is not a directory" >&2
    exit 1
fi

script_dir="$(cd "$(dirname "$0")" && pwd)"
differ="$script_dir/differ.py"

snapshots=()
while IFS= read -r dir; do
    html="$dir/index.html"
    if [[ -f "$html" ]]; then
        snapshots+=("$dir")
    fi
done < <(find "$website_dir" -mindepth 1 -maxdepth 1 -type d | sort)

if [[ ${#snapshots[@]} -lt 2 ]]; then
    echo "Error: need at least 2 snapshots, found ${#snapshots[@]}" >&2
    exit 1
fi

format_timestamp() {
    local name
    name="$(basename "$1")"
    if [[ ${#name} -ge 8 ]]; then
        echo "${name:0:4}-${name:4:2}-${name:6:2} ${name:8:2}:${name:10:2}:${name:12:2}"
    else
        echo "$name"
    fi
}

score_bar() {
    local score="$1"
    local width=30
    local filled
    filled=$(awk "BEGIN { printf \"%d\", $score * $width }")
    local empty=$((width - filled))
    local bar=""
    for ((i = 0; i < filled; i++)); do bar+="█"; done
    for ((i = 0; i < empty; i++)); do bar+="░"; done
    echo "$bar"
}

score_label() {
    local cmp
    cmp=$(awk "BEGIN { print ($1 > 0.40) }")
    if [[ "$cmp" == "1" ]]; then
        echo "MAJOR"
        return
    fi
    cmp=$(awk "BEGIN { print ($1 > 0.15) }")
    if [[ "$cmp" == "1" ]]; then
        echo "SIGNIFICANT"
        return
    fi
    echo "minor"
}

website_name="$(basename "$website_dir")"
echo "Website: $website_name"
echo "Snapshots: ${#snapshots[@]}"
echo ""
printf "%-21s  %-21s  %6s  %-30s  %s\n" "From" "To" "Score" "" "Label"
printf '%0.s─' {1..100}
echo ""

for ((i = 0; i < ${#snapshots[@]} - 1; i++)); do
    old="${snapshots[$i]}/index.html"
    new="${snapshots[$i + 1]}/index.html"

    score=$(uv run python "$differ" "$old" "$new" | head -1 | awk '{print $NF}')

    from_ts=$(format_timestamp "${snapshots[$i]}")
    to_ts=$(format_timestamp "${snapshots[$i + 1]}")
    bar=$(score_bar "$score")
    label=$(score_label "$score")

    printf "%-21s  %-21s  %6s  %s  %s\n" "$from_ts" "$to_ts" "$score" "$bar" "$label"
done
