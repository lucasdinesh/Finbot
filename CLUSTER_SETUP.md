# Financial Couple Bot - Docker Compose Cluster Setup

Complete guide to running the Financial Couple Telegram Bot in a Docker Compose cluster with Prometheus metrics and Grafana monitoring.

## 📋 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 Docker Compose Network                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐  ┌────────────────┐  ┌────────────┐ │
│  │ Financial    │  │  Prometheus    │  │  Grafana   │ │
│  │ Bot          │→→│  (Metrics)     │→→│ (Dashboard)│ │
│  │ :8000        │  │  :9090         │  │  :3000     │ │
│  └──────────────┘  └────────────────┘  └────────────┘ │
│                                                         │
│  All services communicate via Docker network           │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker (v20.10+)
- Docker Compose (v1.29+)

### Step 1: Build and Start Services

```bash
cd /home/lucas/PycharmProjects/FinancialCouple

# Build the bot image
docker-compose build

# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

### Step 2: Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| **Bot** | (Telegram) | Token in config.py |
| **Prometheus** | http://localhost:9090 | (Public) |
| **Grafana** | http://localhost:3000 | admin/admin |

### Step 3: Verify Metrics Flow

1. **Check Prometheus is scraping metrics:**
   ```
   http://localhost:9090/targets
   ```
   You should see the bot target as "UP"

2. **Check bot is exposing metrics:**
   ```bash
   curl http://localhost:8000/metrics
   ```
   You should see Prometheus metric output

3. **View Grafana Dashboard:**
   - Login: http://localhost:3000 (admin/admin)
   - Go to Dashboards → Financial Bot Dashboard
   - You'll see real-time metrics!

## 📊 Available Metrics

### Counter Metrics (Cumulative)
- `bot_command_executions_total` - Command execution counts by command/user/status
- `bot_messages_received_total` - Total messages received
- `bot_expenses_added_total` - Total expenses added
- `bot_expenses_deleted_total` - Total expenses deleted
- `bot_errors_total` - Total errors

### Gauge Metrics (Current Values)
- `bot_active_users` - Number of active users
- `bot_concurrent_conversations` - Number of concurrent conversations
- `bot_running` - Bot running status (1 or 0)
- `bot_user_state_cache_size` - Size of user state cache

### Histogram Metrics (Latency)
- `bot_request_duration_seconds` - Request processing time

## 📈 Grafana Dashboard Panels

Your dashboard includes:

1. **Commands Execution Rate** (Pie Chart)
   - Shows which commands are most used

2. **Messages Received Rate** (Time Series)
   - Trends over time

3. **Active Users** (Gauge)
   - Current active users

4. **Concurrent Conversations** (Gauge)
   - How many users are in conversation flow

5. **Expenses Added (Last Hour)** (Stat)
   - Quick metric for business activity

6. **Errors (Last Hour)** (Stat)
   - Quick health check

7. **Requests by User** (Time Series)
   - Per-user activity over time

## 📝 Usage Examples

### Test the Bot
```bash
# Read logs
docker-compose logs -f bot

# Run a command
docker-compose exec bot python -c "from main import bot; print('Bot initialized')"

# Shell access
docker-compose exec bot /bin/bash
```

### Monitor Metrics
```bash
# Get metrics in raw format
curl http://localhost:8000/metrics | head -50

# Feed specific metric to Prometheus scraper
curl http://localhost:9090/api/v1/query?query=bot_active_users
```

## 🔧 Configuration

### Environment Variables
Edit `docker-compose.yml` to configure:
```yaml
environment:
  - LOCAL_MODE=true          # Set to false for cloud DB
  - PROMETHEUS_PORT=8000     # Metrics server port
```

### Prometheus Scrape Configuration
Edit `prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'financial-bot'
    scrape_interval: 5s  # Change frequency here
```

### Grafana Customization
Dashboards are auto-provisioned from `grafana/provisioning/dashboards/`

To customize:
1. Edit `grafana/provisioning/dashboards/financial-bot-dashboard.json`
2. Restart: `docker-compose restart grafana`

## 🛑 Stopping Services

```bash
# Stop all services
docker-compose stop

# Stop and remove containers (keep volumes)
docker-compose down

# Complete cleanup (removes volumes too!)
docker-compose down -v
```

## 🐛 Troubleshooting

### Metrics not appearing in Grafana
1. Check Prometheus job status: http://localhost:9090/targets
2. Verify bot is running: `docker-compose logs bot | grep "started"`
3. Check metrics endpoint: `curl http://localhost:8000/metrics`

### Bot not starting
```bash
# Check logs
docker-compose logs bot

# Rebuild image
docker-compose build --no-cache

# Restart
docker-compose up -d bot
```

### Prometheus not scraping
1. Verify network: `docker network ls`
2. Check bot internal IP: `docker inspect financial-bot | grep IPAddress`
3. Update `prometheus.yml` if needed

### Grafana not loading dashboard
1. Clear browser cache
2. Check datasource: http://localhost:3000/admin/datasources
3. Restart Grafana: `docker-compose restart grafana`

## 📦 Scaling the Bot

### Multiple Bot Instances
To run multiple bot instances with load balancing:

```yaml
services:
  bot-1:
    build: .
    environment:
      - INSTANCE=bot1
    ports:
      - "8001:8000"
  
  bot-2:
    build: .
    environment:
      - INSTANCE=bot2
    ports:
      - "8002:8000"
```

Update `prometheus.yml`:
```yaml
static_configs:
  - targets: ['localhost:8001', 'localhost:8002']
```

## 🔐 Production Considerations

1. **Change Grafana Password:**
   ```
   docker-compose exec grafana grafana-cli admin reset-admin-password newpassword
   ```

2. **Enable Persistence:**
   - Already configured with named volumes
   - Backup: `docker-compose exec prometheus tar czf prometheus-backup.tar.gz /prometheus`

3. **Add Authentication:**
   - Configure OAuth in Grafana settings
   - Secure Prometheus with reverse proxy

4. **Resource Limits:**
   - Add to `docker-compose.yml`:
   ```yaml
   services:
     bot:
       deploy:
         resources:
           limits:
             cpus: '1'
             memory: 512M
   ```

## 📚 Additional Resources

- [Prometheus Docs](https://prometheus.io/docs/)
- [Grafana Docs](https://grafana.com/docs/)
- [Docker Compose Docs](https://docs.docker.com/compose/)

## 💡 Next Steps

1. ✅ Deploy on local machine
2. 🔄 Test with actual users
3. 📊 Customize dashboards
4. 🚀 Deploy to cloud (AWS ECS, Kubernetes, etc.)
5. 🔐 Add authentication & SSL
