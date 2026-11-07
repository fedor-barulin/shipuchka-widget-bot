#!/bin/sh
# Watchdog for the bot container: messages the admin through the Bot API when the bot
# is down, crash-loops or logs a Python traceback, and once more when it recovers.
# The Bot API works with the same token even when the MTProto client cannot start.
# cron: */2 * * * * /opt/widget-bot/watchdog.sh
set -u
DIR=$(cd "$(dirname "$0")" && pwd)
NAME=${WATCHDOG_CONTAINER:-widget-bot}
STATE="$DIR/data/.watchdog"
TOKEN=$(grep -E '^BOT_TOKEN=' "$DIR/.env" | head -1 | cut -d= -f2-)
ADMIN=$(grep -E '^ADMIN_IDS=' "$DIR/.env" | head -1 | cut -d= -f2- | cut -d, -f1)
[ -n "$TOKEN" ] && [ -n "$ADMIN" ] || exit 0

send() {
    code=$(curl -s -m 15 -o /dev/null -w '%{http_code}' "https://api.telegram.org/bot$TOKEN/sendMessage" \
        --data-urlencode "chat_id=$ADMIN" --data-urlencode "text=$1")
    echo "$(date -u '+%F %T') sent ($code): $(echo "$1" | head -1)" >> "$DIR/data/watchdog.log"
}

prev_state=ok; prev_restarts=0; last_err=0
[ -f "$STATE" ] && . "$STATE"

info=$(docker inspect -f '{{.State.Status}} {{.RestartCount}}' "$NAME" 2>/dev/null || echo "missing 0")
status=${info% *}; restarts=${info#* }
now=$(date +%s)

state=ok; why=""
if [ "$status" != "running" ]; then
    state=down; why="контейнер в состоянии $status"
elif [ "$restarts" -gt "$prev_restarts" ]; then
    state=down; why="перезапускался $((restarts - prev_restarts)) раз за 2 минуты"
fi

err=$(docker logs --since 2m "$NAME" 2>&1 | grep -E 'Error|Exception' | grep -v -E 'INFO|WARNING' | tail -1 \
    | sed -E 's/[0-9]{8,}:[A-Za-z0-9_-]{30,}/<token>/g' | cut -c1-300)

if [ "$state" = down ] && [ "$prev_state" = ok ]; then
    send "🚨 Бот упал: $why.${err:+
Последняя ошибка: $err}
Логи: docker logs --tail 50 $NAME"
elif [ "$state" = ok ] && [ "$prev_state" = down ]; then
    send "✅ Бот снова работает."
elif [ "$state" = ok ] && [ -n "$err" ] && [ $((now - last_err)) -gt 1800 ]; then
    send "⚠️ Бот работает, но пишет ошибки:
$err"
    last_err=$now
fi

printf 'prev_state=%s\nprev_restarts=%s\nlast_err=%s\n' "$state" "$restarts" "$last_err" > "$STATE"
