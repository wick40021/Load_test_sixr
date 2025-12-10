import logging
import uuid
import random
from locust import HttpUser, between, SequentialTaskSet, task

# ---------------------------------------
# Logging Configuration
# ---------------------------------------
logging.basicConfig(
    filename='locust_test.log',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ---------------------------------------
# Generate Random Gameplay Score Payload (UPDATED)
# ---------------------------------------
def generate_random_scores(player_id):
    possible_results = ["0", "1", "2", "3", "4", "6", "W"]
    overs = 2

    runs = [[random.choice(possible_results) for _ in range(6)] for _ in range(overs)]

    wickets = []
    ball_index = 0

    for over in runs:
        for result in over:
            # Only allow wicket AFTER ball 1 (ball index >= 2)
            if result == "W" and ball_index >= 2:
                wickets.append([str(ball_index), "BOWLED"])

            ball_index += 1

    return {
        "playerId": player_id,
        "RUNS": runs,
        "SIX": [],
        "WICKET": wickets
    }



# ---------------------------------------
# User Flow Sequence
# ---------------------------------------
class UserFlow(SequentialTaskSet):

    @task
    def login(self):
        url = "/api/v1/auth/guest"
        payload = {"deviceId": str(uuid.uuid4())}

        with self.client.post(url, json=payload, catch_response=True) as response:
            logging.info(f"🔍 [POST] {url} -> Status: {response.status_code}")
            logging.info(f"📦 Response: {response.text}")

            if response.status_code == 200:
                data = response.json().get("data", {})
                self.token = data.get("tokens", {}).get("accessToken")
                self.user_id = data.get("user", {}).get("id")
                logging.info(f"🎉 Logged in -> user_id: {self.user_id}")
            else:
                response.failure(f"❌ Login failed: {response.status_code}")

    @task
    def validate_token(self):
        url = "/api/v1/auth/validate"
        headers = {"Authorization": f"Bearer {self.token}"}

        with self.client.post(url, headers=headers, catch_response=True) as response:
            logging.info(f"🔍 [POST] {url} -> Status: {response.status_code}")
            logging.info(f"📦 Response: {response.text}")

            if response.status_code == 200:
                logging.info(f"✅ Token validated for user_id: {self.user_id}")
            else:
                response.failure("❌ Token validation failed")

    @task
    def load_home(self):
        url = "/api/v1/home"
        headers = {"Authorization": f"Bearer {self.token}"}

        with self.client.get(url, headers=headers, catch_response=True) as response:
            logging.info(f"🔍 [GET] {url} -> Status: {response.status_code}")
            logging.info(f"📦 Response: {response.text}")

            if response.status_code == 200:
                logging.info(f"✅ Home loaded successfully for user_id: {self.user_id}")
            else:
                response.failure("❌ Failed to load home")

    @task
    def claim_reward(self):
        url = "/api/v1/rewards/daily/claim"
        headers = {"Authorization": f"Bearer {self.token}"}
        json_body = {"userId": self.user_id}

        with self.client.post(url, headers=headers, json=json_body, catch_response=True) as response:
            logging.info(f"🔍 [POST] {url} -> Status: {response.status_code}")
            logging.info(f"📦 Payload: {json_body}")
            logging.info(f"📦 Response: {response.text}")

            if response.status_code == 200:
                logging.info(f"✅ Reward claimed for user_id: {self.user_id}")
            else:
                response.failure("❌ Reward claim failed")

    @task
    def gameplay_join(self):
        url = "/api/v1/gameplay/join"
        headers = {"Authorization": f"Bearer {self.token}"}
        self.matchKey = uuid.uuid4().hex[:32]

        json_body = {
            "matchKey": self.matchKey,
            "mode": "TargetMode",
            "overs": 2,
            "stake": 0,
            "targetScore": 14
        }

        with self.client.post(url, headers=headers, json=json_body, catch_response=True) as response:
            logging.info(f"🔍 [POST] {url} -> Status: {response.status_code}")
            logging.info(f"📦 Payload: {json_body}")
            logging.info(f"📦 Response: {response.text}")

            if response.status_code == 200:
                data = response.json().get("data", {})
                self.matchId = data.get("matchId")
                players = data.get("players", [])
                if players:
                    self.playerId = players[0].get("playerId")

                logging.info(f"✅ Gameplay joined -> matchId: {self.matchId}, playerId: {self.playerId}")
            else:
                response.failure(f"❌ Gameplay join failed: {response.text}")

    @task
    def update_score(self):
        if not getattr(self, "matchId", None) or not getattr(self, "playerId", None):
            logging.error("⛔ Missing matchId or playerId, skipping score update.")
            return

        url = f"/api/v1/gameplay/{self.matchId}/score"
        headers = {"Authorization": f"Bearer {self.token}"}

        random_scores = generate_random_scores(self.playerId)

        payload = {
            "matchKey": self.matchKey,
            "scores": [random_scores],
            "winner": self.playerId,
            "targetScore": 14
        }

        with self.client.post(url, headers=headers, json=payload, catch_response=True) as response:
            logging.info(f"🔍 [POST] {url} -> Status: {response.status_code}")
            logging.info(f"📦 Payload: {payload}")
            logging.info(f"📦 Response: {response.text}")

            if response.status_code == 200:
                logging.info(f"✅ Score updated successfully for match: {self.matchId}")
            else:
                response.failure(f"❌ Score update failed: {response.text}")

        # Loop back to beginning
        self.interrupt(reschedule=True)

# ---------------------------------------
# Main Locust User
# ---------------------------------------
class CrimsonUser(HttpUser):
    wait_time = between(1, 3)
    tasks = [UserFlow]

