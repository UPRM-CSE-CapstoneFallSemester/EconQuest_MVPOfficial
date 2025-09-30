from locust import HttpUser, task, between
class EconQuestUser(HttpUser):
    wait_time = between(1, 3)
    token = None
    def on_start(self):
        res = self.client.post("/auth/api/login", json={"email":"student@econquest.local","password":"student123"})
        if res.status_code == 200:
            self.token = res.json().get("access_token")
    @task(2)
    def view_home(self): self.client.get("/")
    @task(3)
    def view_student_dashboard(self): self.client.get("/student/dashboard")
    @task(1)
    def api_me(self):
        if self.token:
            self.client.get("/auth/api/me", headers={"Authorization": f"Bearer {self.token}"})
