import random

from locust import HttpUser, task, between

MIN_USER_ID = 1
MAX_USER_ID = 10**6


class InventoryUser(HttpUser):
    wait_time = between(1, 2)  # Wait between 1 and 2 seconds between tasks
    inventory_items = ('test_item', 'bfg', 'bla')

    @task
    def get_inventory(self):
        player_id = random.randint(MIN_USER_ID, MAX_USER_ID)
        self.client.post("/v1/inventory/get", json={"player_id": player_id})

    @task
    def grant_item(self):
        item_code = random.choice(InventoryUser.inventory_items)
        item_amount = random.randint(1, 10)
        player_id = random.randint(MIN_USER_ID, MAX_USER_ID)
        data = {"player_id": player_id, "item_code": item_code, "amount": item_amount}
        self.client.post("/v1/inventory/grant", json=data)

