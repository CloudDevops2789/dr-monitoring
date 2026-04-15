import sys
import requests
import psutil
import pymysql
import yaml
import logging

from utils.servicenow import create_incident

# Logging setup
logging.basicConfig(
    filename='logs/health.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print("===== DR Health Check Started =====")
logging.info("Health check started")

# Load config
with open('config/config.yaml', 'r') as file:
    config = yaml.safe_load(file)

WEB_URL = config['web_url']
DB = config['database']
THRESHOLDS = config['thresholds']

status = 0

# -----------------------------
# 1. Web Check
# -----------------------------
try:
    response = requests.get(WEB_URL, timeout=5)
    if response.status_code == 200:
        print("[OK] Web is reachable")
        logging.info("Web check passed")
    else:
        print(f"[ERROR] Web failed: {response.status_code}")
        logging.error("Web check failed")
        status = 1
except Exception as e:
    print(f"[ERROR] Web exception: {e}")
    logging.error(f"Web exception: {e}")
    status = 1


# -----------------------------
# 2. DB Check
# -----------------------------
try:
    conn = pymysql.connect(
        host=DB['host'],
        user=DB['user'],
        password=DB['password'],
        database=DB['name'],
        connect_timeout=5
    )
    conn.close()
    print("[OK] DB reachable")
    logging.info("DB check passed")
except Exception as e:
    print(f"[ERROR] DB failed: {e}")
    logging.error(f"DB check failed: {e}")
    status = 1


# -----------------------------
# 3. CPU Check
# -----------------------------
cpu = psutil.cpu_percent(interval=1)
if cpu > THRESHOLDS['cpu']:
    print(f"[WARNING] High CPU: {cpu}%")
    logging.warning(f"High CPU: {cpu}")
    status = 1
else:
    print(f"[OK] CPU normal: {cpu}%")


# -----------------------------
# 4. Memory Check
# -----------------------------
mem = psutil.virtual_memory().percent
if mem > THRESHOLDS['memory']:
    print(f"[WARNING] High Memory: {mem}%")
    logging.warning(f"High Memory: {mem}")
    status = 1
else:
    print(f"[OK] Memory normal: {mem}%")

print("===== Health Check Completed =====")
logging.info("Health check completed")

# -----------------------------
# FINAL DECISION
# -----------------------------
if status != 0:
    print("DR_TRIGGER=true")
    logging.error("System unhealthy - triggering ServiceNow incident")

    create_incident()

    sys.exit(1)
else:
    print("System healthy")
    sys.exit(0)
