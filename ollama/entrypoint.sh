#!/bin/sh
# Do not use set -e: a failed ollama pull must not stop the server.
PULL_MODEL="${OLLAMA_PULL_MODEL:-llama3.1}"

ollama serve &
OLLAMA_PID=$!

i=0
until ollama list >/dev/null 2>&1; do
  i=$((i + 1))
  if [ "$i" -gt 120 ]; then
    echo "ollama_entrypoint: API did not become ready in time"
    exit 1
  fi
  sleep 1
done

echo "ollama_entrypoint: pulling model '${PULL_MODEL}' (set OLLAMA_MODEL in .env to change)"
if ! ollama pull "$PULL_MODEL"; then
  echo "ollama_entrypoint: WARNING - pull failed. Start anyway; run manually: ollama pull ${PULL_MODEL}"
fi

wait "$OLLAMA_PID"
