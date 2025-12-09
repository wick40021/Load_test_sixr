import logging
from locust import HttpUser, task, between

# ---------------------------------------
# Logging setup
# ---------------------------------------
logging.basicConfig(
    filename="login_test.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

class LoginUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def login_user(self):
        url = "/api/v1/auth/login"
        payload = {
            "identifier": "wick40021+1@gmail.com",
            "password": "Welcome@123"
        }

        with self.client.post(url, json=payload, catch_response=True) as response:
            logging.info(f"🔍 [POST] {url} -> Status: {response.status_code}")
            logging.info(f"📦 Payload: {payload}")
            logging.info(f"📦 Response: {response.text}")

            if response.status_code == 200:
                data = response.json().get("data", {})
                self.token = data.get("tokens", {}).get("accessToken")
                self.user_id = data.get("user", {}).get("id")

                logging.info(f"🎉 Login success -> user_id: {self.user_id}, token: {self.token}")
                response.success()
            else:
                logging.error("❌ Login failed")
                response.failure("Login failed")
