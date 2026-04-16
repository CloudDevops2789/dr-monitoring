import sys
import requests
import pymysql
import yaml
import logging
import os

from utils.servicenow import create_incident

# ANSI color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
RESET = "\033[0m"

# Logging setup
logging.basicConfig(
    filename='logs/health.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Helper print functions
def ok(msg): print(f"{GREEN}[OK]{RESET} {msg}")
def warn(msg): print(f"{YELLOW}[WARNING]{RESET} {msg}")
def err(msg): print(f"{RED}[ERROR]{RESET} {msg}")
def crit(msg): print(f"{BOLD}{RED}[CRITICAL]{RESET} {msg}")
def info(msg): print(f"{CYAN}{msg}{RESET}")

info("===== DR Health Check Started =====")
logging.info("Health check started")

# Load config
with open('config/config.yaml', 'r') as file:
    config = yaml.safe_load(file)

WEB_URL = config['web_url']
DB = config['database']

status = 0

# -----------------------------
# 0. Host Reachability Check
# -----------------------------
host = DB['host']
ping = os.system(f"ping -c 1 {host} > /dev/null 2>&1")

if ping != 0:
    crit("Host unreachable")
    logging.error("Host unreachable")
    status = 1
else:
    ok("Host reachable")
    logging.info("Host reachable")

# -----------------------------
# 1. Web Check
# -----------------------------
try:
    response = requests.get(WEB_URL, timeout=5)
    if response.status_code == 200:
        ok("Web is reachable")
        logging.info("Web check passed")
    else:
        err(f"Web failed: {response.status_code}")
        logging.error("Web check failed")
        status = 1
except Exception as e:
    err(f"Web exception: {e}")
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
    ok("DB reachable")
    logging.info("DB check passed")
except Exception as e:
    err(f"DB failed: {e}")
    logging.error(f"DB check failed: {e}")
    status = 1

info("===== Health Check Completed =====")
logging.info("Health check completed")

# -----------------------------
# FINAL DECISION
# -----------------------------
if status != 0:
    print(f"{BOLD}{MAGENTA}DR_TRIGGER=true{RESET}")
    logging.error("System unhealthy - triggering ServiceNow incident")

    result = create_incident()

    if result == "created":
        ok("ServiceNow incident created")
    elif result == "existing":
        warn("Reusing existing active incident")
    else:
        err("ServiceNow operation failed")

    sys.exit(1)
else:
    ok("System healthy")
    sys.exit(0)
