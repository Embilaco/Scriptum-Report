#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: convert_video.sh [OPTIONS] [PATH ...]

Convert one or more video files to PowerPoint-friendly MP4 files, extract a
poster frame image, and collect basic metadata (width/height).

When PATH points to a directory, all supported video files inside it will be
processed recursively.

Options:
  -o, --output DIR   Write converted files to DIR. Defaults to the directory of
                     each input file.
  -f, --force        Overwrite existing outputs.
  -h, --help         Show this help message and exit.

Requirements:
  * ffmpeg (https://ffmpeg.org/)
  * ffprobe (usually distributed alongside ffmpeg)

The script is compatible with Linux and Windows (Git Bash, WSL, Cygwin, or
similar environments) as long as the required tools are installed and available
on the PATH.
USAGE
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

ensure_dependency() {
  local cmd="$1"
  local url="$2"
  if ! command_exists "$cmd"; then
    printf 'ERROR: required command "%s" not found on PATH.\n' "$cmd" >&2
    printf '       Please install %s: %s\n' "$cmd" "$url" >&2
    exit 1
  fi
}

json_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  printf '%s' "$s"
}

absolute_path() {
  local path="$1"
  if command_exists realpath; then
    realpath "$path"
  else
    local dir
    dir=$(cd "$(dirname "$path")" && pwd)
    printf '%s/%s\n' "$dir" "$(basename "$path")"
  fi
}

declare -a INPUTS=()
OUTPUT_DIR=""
FORCE=0

while (($#)); do
  case "$1" in
    -o|--output)
      [[ $# -ge 2 ]] || { printf 'ERROR: missing argument for %s\n' "$1" >&2; exit 1; }
      OUTPUT_DIR="$2"
      shift 2
      ;;
    -f|--force)
      FORCE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      while (($#)); do
        INPUTS+=("$1")
        shift
      done
      ;;
    -*)
      printf 'ERROR: unknown option %s\n\n' "$1" >&2
      usage
      exit 1
      ;;
    *)
      INPUTS+=("$1")
      shift
      ;;
  esac
done

if ((${#INPUTS[@]} == 0)); then
  usage
  exit 0
fi

ensure_dependency ffmpeg "https://ffmpeg.org/download.html"
ensure_dependency ffprobe "https://ffmpeg.org/download.html"

SUPPORTED_EXTENSIONS=(avi mkv mov mpg mpeg wmv flv webm m4v gif qt 3gp mp4)

declare -a FILES

add_file() {
  local file="$1"
  if [[ -f "$file" ]]; then
    FILES+=("$file")
  fi
}

collect_files_from_dir() {
  local dir="$1"
  local extension_args=()
  local first=1
  for ext in "${SUPPORTED_EXTENSIONS[@]}"; do
    if (( first )); then
      extension_args+=( -iname "*.${ext}" )
      first=0
    else
      extension_args+=( -o -iname "*.${ext}" )
    fi
  done

  while IFS= read -r -d '' file; do
    FILES+=("$file")
  done < <(find "$dir" -type f \( "${extension_args[@]}" \) -print0)
}

for input_path in "${INPUTS[@]}"; do
  if [[ -d "$input_path" ]]; then
    collect_files_from_dir "$input_path"
  elif [[ -f "$input_path" ]]; then
    add_file "$input_path"
  else
    printf 'WARNING: %s is not a valid file or directory. Skipping.\n' "$input_path" >&2
  fi
done

if ((${#FILES[@]} == 0)); then
  printf 'No supported video files found.\n' >&2
  exit 1
fi

mkdir -p "${OUTPUT_DIR:-.}"

FFMPEG_VIDEO_OPTS=(
  -c:v libx264
  -preset slow
  -profile:v high
  -level 4.0
  -pix_fmt yuv420p
  -crf 22
  -movflags +faststart
)

FFMPEG_AUDIO_OPTS=(
  -c:a aac
  -b:a 192k
)

process_file() {
  local src="$1"
  local src_dir
  src_dir=$(dirname "$src")
  local base_name
  base_name=$(basename "$src")
  base_name="${base_name%.*}"

  local target_dir="${OUTPUT_DIR:-$src_dir}"
  mkdir -p "$target_dir"

  local mp4_path="$target_dir/${base_name}.mp4"
  local poster_path="$target_dir/${base_name}_poster.jpg"
  local metadata_path="$target_dir/${base_name}.metadata.json"

  if [[ -e "$mp4_path" && $FORCE -eq 0 ]]; then
    printf 'Skipping conversion (exists): %s\n' "$mp4_path"
  else
    local overwrite_flag="-n"
    (( FORCE )) && overwrite_flag="-y"

    printf 'Converting %s -> %s\n' "$src" "$mp4_path"
    ffmpeg "$overwrite_flag" -i "$src" "${FFMPEG_VIDEO_OPTS[@]}" "${FFMPEG_AUDIO_OPTS[@]}" "$mp4_path"
  fi

  if [[ ! -e "$poster_path" || $FORCE -ne 0 ]]; then
    local overwrite_flag="-n"
    (( FORCE )) && overwrite_flag="-y"
    printf 'Extracting poster frame %s\n' "$poster_path"
    ffmpeg "$overwrite_flag" -i "$mp4_path" -frames:v 1 "$poster_path"
  else
    printf 'Skipping poster frame (exists): %s\n' "$poster_path"
  fi

  local dimensions
  if ! dimensions=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0:s=x "$mp4_path"); then
    printf 'WARNING: unable to determine dimensions for %s\n' "$mp4_path" >&2
    return
  fi

  local width="${dimensions%x*}"
  local height="${dimensions#*x}"

  local src_abs mp4_abs poster_abs
  src_abs=$(absolute_path "$src")
  mp4_abs=$(absolute_path "$mp4_path")
  poster_abs=$(absolute_path "$poster_path")

  local src_json mp4_json poster_json
  src_json=$(json_escape "$src_abs")
  mp4_json=$(json_escape "$mp4_abs")
  poster_json=$(json_escape "$poster_abs")

  cat >"$metadata_path" <<EOF
{
  "source": "$src_json",
  "video": "$mp4_json",
  "poster_frame": "$poster_json",
  "width": $width,
  "height": $height
}
EOF

  printf 'Metadata written to %s\n' "$metadata_path"
}

for file in "${FILES[@]}"; do
  process_file "$file"
done

printf '\nProcessed %d file(s).\n' "${#FILES[@]}"
