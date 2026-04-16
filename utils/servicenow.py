import requests
import yaml
import urllib3
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def create_incident():
    try:
        with open("config/config.yaml", "r") as file:
            config = yaml.safe_load(file)

        snow = config["servicenow"]

        url = f"{snow['instance_url']}/api/now/table/incident"
        auth = (snow["username"], snow["password"])

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Check ACTIVE incidents
        query = "short_descriptionLIKEOnPrem Server Down^incident_stateIN1,2,3"

        check = requests.get(
            url,
            params={"sysparm_query": query, "sysparm_limit": 1},
            auth=auth,
            headers=headers,
            verify=False
        )

        if check.status_code == 200 and check.json().get("result"):
            existing = check.json()["result"][0]

            number = existing["number"]
            sys_id = existing["sys_id"]

            print(f"[INFO] Existing ACTIVE incident found: {number}")

            with open("logs/last_incident.txt", "w") as f:
                f.write(f"{number},{sys_id}")

            return "existing"

        # Create new incident
        payload = {
            "short_description": "OnPrem Server Down - DR Triggered",
            "description": "Health check failed. Initiating DR workflow.",
            "urgency": "1",
            "impact": "1",
            "assignment_group": "a48adc8c53337210610572d0a0490ec7",
        }

        response = requests.post(
            url,
            json=payload,
            auth=auth,
            headers=headers,
            verify=False
        )

        if response.status_code == 201:
            data = response.json()["result"]

            number = data["number"]
            sys_id = data["sys_id"]

            print(f"[OK] ServiceNow incident created: {number}")

            with open("logs/last_incident.txt", "w") as f:
                f.write(f"{number},{sys_id}")

            return "created"

        else:
            print(f"[ERROR] Failed to create incident: {response.status_code}")
            print(response.text)
            return "error"

    except Exception as e:
        print(f"[ERROR] create_incident: {e}")
        return "error"


def close_incident():
    try:
        with open("config/config.yaml", "r") as file:
            config = yaml.safe_load(file)

        snow = config["servicenow"]

        if not os.path.exists("logs/last_incident.txt"):
            print("[INFO] No incident to close")
            return

        with open("logs/last_incident.txt", "r") as f:
            number, sys_id = f.read().strip().split(",")

        url = f"{snow['instance_url']}/api/now/table/incident/{sys_id}"
        auth = (snow["username"], snow["password"])
        headers = {"Content-Type": "application/json"}

        get_resp = requests.get(url, auth=auth, headers=headers, verify=False)

        if get_resp.status_code != 200:
            print("[ERROR] Unable to fetch incident state")
            return

        result = get_resp.json()["result"]

        active = str(result.get("active")).lower()
        state = str(result.get("incident_state"))

        print(f"[DEBUG] {number} | active={active} | state={state}")

        if active == "false" or state in ["6", "7"]:
            print(f"[INFO] Incident {number} already closed/resolved")
            os.remove("logs/last_incident.txt")
            return

        # Move to In Progress
        requests.patch(
            url,
            json={"incident_state": "2"},
            auth=auth,
            headers=headers,
            verify=False
        )

        # Resolve
        response = requests.patch(
            url,
            json={
                "incident_state": "6",
                "state": "6",
                "close_code": "Solution provided",
                "close_notes": "DR completed successfully"
            },
            auth=auth,
            headers=headers,
            verify=False
        )

        if response.status_code == 200:
            print(f"[OK] Incident {number} resolved successfully")
            os.remove("logs/last_incident.txt")
        else:
            print(f"[ERROR] Close failed: {response.text}")

    except Exception as e:
        print(f"[ERROR] close_incident: {e}")
