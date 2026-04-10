# Runbook: put-email-offers-on-my-calendar

## First-time setup

The canonical systemd unit files live in this skill directory. Symlink them into
`~/.config/systemd/user/` so systemd can find them, then enable the timer:

```sh
SKILL_DIR=~/skills/skills/daily/put-email-offers-on-my-calendar

ln -sf "$SKILL_DIR/put-email-offers-on-calendar.service" ~/.config/systemd/user/
ln -sf "$SKILL_DIR/put-email-offers-on-calendar.timer"   ~/.config/systemd/user/

chmod +x "$SKILL_DIR/run.sh"
systemctl --user daemon-reload
systemctl --user enable --now put-email-offers-on-calendar.timer
```

## Verify the timer is scheduled

```sh
systemctl --user list-timers put-email-offers-on-calendar.timer
```

## Run manually (without waiting for 3am)

```sh
systemctl --user start put-email-offers-on-calendar.service
```

## Check logs

```sh
# Follow logs in real time
journalctl --user -u put-email-offers-on-calendar.service -f

# View all past logs for this service
journalctl --user -u put-email-offers-on-calendar.service
```

## Stop the timer (disable scheduled runs)

```sh
systemctl --user disable --now put-email-offers-on-calendar.timer
```

## Re-enable the timer after stopping

```sh
systemctl --user enable --now put-email-offers-on-calendar.timer
```

## Check timer/service status

```sh
systemctl --user status put-email-offers-on-calendar.timer
systemctl --user status put-email-offers-on-calendar.service
```
