# cronwatch

A lightweight CLI tool to monitor, log, and alert on cron job failures with Slack and email integration.

---

## Installation

```bash
pip install cronwatch
```

Or install from source:

```bash
git clone https://github.com/yourname/cronwatch.git && cd cronwatch && pip install .
```

---

## Usage

Wrap any cron command with `cronwatch` to automatically log output and receive alerts on failure:

```bash
cronwatch --name "nightly-backup" --notify slack,email -- /usr/bin/backup.sh
```

Configure your notification settings in `~/.cronwatch/config.yaml`:

```yaml
slack:
  webhook_url: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

email:
  smtp_host: "smtp.gmail.com"
  smtp_port: 587
  from: "alerts@example.com"
  to: "you@example.com"
```

View recent job history:

```bash
cronwatch logs --name "nightly-backup" --last 10
```

---

## Features

- 🔍 Captures exit codes, stdout, and stderr for every job run
- 📣 Sends instant alerts to Slack and/or email on failure
- 📋 Maintains a local log history queryable from the CLI
- ⚙️ Simple YAML-based configuration

---

## License

This project is licensed under the [MIT License](LICENSE).