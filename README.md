# System Monitor

A lightweight, reliable system monitoring application that checks website availability, API endpoints, and server statuses with real-time Telegram notifications when systems go down.

## 🔍 Features

- **Real-time Monitoring**: Checks multiple systems at configurable intervals
- **Instant Notifications**: Sends alerts via Telegram when a system becomes unavailable
- **Recovery Tracking**: Notifies when systems come back online with downtime statistics
- **Low Resource Usage**: Designed to run efficiently with minimal system footprint
- **Cross-Platform**: Works seamlessly on both Windows and Linux
- **Configurable**: Easy YAML configuration for all settings
- **Failure Tolerance**: Configurable failure thresholds to prevent false alarms
- **Detailed Logging**: Comprehensive logging of all events and status changes

## 📋 Requirements

- Python 3.6+
- Required packages:
  - requests
  - pyyaml
  - schedule

## 🚀 Quick Start

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/system-monitor.git
cd system-monitor
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Configure your systems**

Edit the `config.yaml` file to add your systems and Telegram credentials:

```yaml
# Systems to monitor
targets:
  - id: "Main Website"
    url: "https://example.com"
    method: "GET"
    expected_status_code: 200
    failure_threshold: 3

# Telegram settings
telegram_bot_token: "YOUR_TELEGRAM_BOT_TOKEN"
telegram_chat_id: "YOUR_CHAT_ID"

# General settings
check_interval: 60 # seconds
timeout: 10 # seconds
```

4. **Run the monitor**

```bash
python system_monitor.py
```

## 🔧 Configuration Options

| Option               | Description                          |
| -------------------- | ------------------------------------ |
| `targets`            | List of systems to monitor           |
| `telegram_bot_token` | Your Telegram bot token              |
| `telegram_chat_id`   | Chat ID to send notifications to     |
| `check_interval`     | How often to check systems (seconds) |
| `timeout`            | Request timeout (seconds)            |

### Target Options

| Option                 | Description                                 |
| ---------------------- | ------------------------------------------- |
| `id`                   | Friendly name for the system                |
| `url`                  | URL to check                                |
| `method`               | HTTP method (GET, POST, etc.)               |
| `expected_status_code` | Expected HTTP status code                   |
| `headers`              | Optional HTTP headers                       |
| `failure_threshold`    | Number of consecutive failures before alert |

## 📱 Telegram Setup

1. Create a new bot by messaging [@BotFather](https://t.me/BotFather) on Telegram
2. Get your Chat ID by messaging [@userinfobot](https://t.me/userinfobot)
3. Add these values to your `config.yaml` file

## 🌩️ Deployment

### Railway

Deploy to Railway with these simple steps:

1. Push your code to GitHub
2. Connect your GitHub repo to Railway
3. Railway will automatically detect the Procfile and deploy the application

For secure credential management, use Railway environment variables instead of storing them in config.yaml.

## 📊 Monitoring Examples

- Web applications and static websites
- REST APIs and microservices
- Internal services and database health endpoints
- Custom application health checks
- Network services

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
