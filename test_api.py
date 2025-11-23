import requests
import random
import pytest
import re

BASE_URL = "https://qa-internship.avito.com"
SELLER_ID = random.randint(111111, 999999)

def parse_uuid_from_status(status):
    match = re.search(r'Сохранили объявление - (.+)', status)
    if match:
        return match.group(1)
    return None

@pytest.fixture
def created_item():
    payload = {
        "sellerID": SELLER_ID,
        "name": "Телефон Xiaomi",
        "price": 15000,
        "statistics": {
            "likes": 10,
            "viewCount": 50,
            "contacts": 3
        }
    }
    response = requests.post(f"{BASE_URL}/api/1/item", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    item_id = parse_uuid_from_status(data["status"])
    assert item_id is not None
    assert len(item_id) == 36
    return item_id

def test_tc001_successful_creation():
    payload = {
        "sellerID": SELLER_ID,
        "name": "Телефон Xiaomi",
        "price": 15000,
        "statistics": {
            "likes": 10,
            "viewCount": 50,
            "contacts": 3
        }
    }
    response = requests.post(f"{BASE_URL}/api/1/item", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"].startswith("Сохранили объявление - ")
    item_id = parse_uuid_from_status(data["status"])
    assert item_id is not None
    assert len(item_id) == 36

def test_tc002_error_missing_sellerid():
    payload = {
        "name": "Телефон Xiaomi",
        "price": 15000,
        "statistics": {
            "likes": 10,
            "viewCount": 50,
            "contacts": 3
        }
    }
    response = requests.post(f"{BASE_URL}/api/1/item", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["result"]["message"] == "поле sellerID обязательно"
    assert data["status"] == "400"

def test_tc003_negative_price():
    payload = {
        "sellerID": SELLER_ID,
        "name": "Товар",
        "price": -100,
        "statistics": {
            "likes": 1,
            "viewCount": 1,
            "contacts": 1
        }
    }
    response = requests.post(f"{BASE_URL}/api/1/item", json=payload)
    assert response.status_code == 200  # Фактическое поведение: создаётся
    data = response.json()
    assert data["status"].startswith("Сохранили объявление - ")

def test_tc004_empty_name():
    payload = {
        "sellerID": SELLER_ID,
        "name": "",
        "price": 500,
        "statistics": {
            "likes": 0,
            "viewCount": 0,
            "contacts": 0
        }
    }
    response = requests.post(f"{BASE_URL}/api/1/item", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["result"]["message"] == "поле name обязательно"
    assert data["status"] == "400"

def test_tc005_missing_statistics():
    payload = {
        "sellerID": SELLER_ID,
        "name": "Товар",
        "price": 5000
    }
    response = requests.post(f"{BASE_URL}/api/1/item", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["result"]["message"] == "поле likes обязательно"  # Фактическое сообщение
    assert data["status"] == "400"

def test_tc006_invalid_sellerid_type():
    payload = {
        "sellerID": "abc",
        "name": "Товар",
        "price": 500,
        "statistics": {
            "likes": 1,
            "viewCount": 2,
            "contacts": 3
        }
    }
    response = requests.post(f"{BASE_URL}/api/1/item", json=payload)
    assert response.status_code == 400  # Предполагаем 400, как в примере
    data = response.json()
    assert data["status"] == "не передано тело объявления"  # Фактическое

def test_tc007_successful_get_item(created_item):
    item_id = created_item
    response = requests.get(f"{BASE_URL}/api/1/item/{item_id}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    item = data[0]
    assert "createdAt" in item
    assert item["id"] == item_id
    assert item["name"] == "Телефон Xiaomi"
    assert item["price"] == 15000
    assert item["sellerId"] == SELLER_ID
    assert item["statistics"]["contacts"] == 3
    assert item["statistics"]["likes"] == 10
    assert item["statistics"]["viewCount"] == 50

def test_tc008_get_nonexistent_item():
    nonexistent_id = "99999999-9999-9999-9999-999999999999"
    response = requests.get(f"{BASE_URL}/api/1/item/{nonexistent_id}")
    assert response.status_code == 404
    data = response.json()
    assert data["result"]["message"] == f"item {nonexistent_id} not found"
    assert data["status"] == "404"

def test_tc009_invalid_uuid_format():
    invalid_id = "abc123"
    response = requests.get(f"{BASE_URL}/api/1/item/{invalid_id}")
    assert response.status_code == 400
    data = response.json()
    assert data["result"]["message"] == f"ID айтема не UUID: {invalid_id}"
    assert data["status"] == "400"

@pytest.fixture
def seller_with_items():
    # Создаём несколько объявлений для sellerID
    ids = []
    for i in range(2):  # Два для теста
        payload = {
            "sellerID": SELLER_ID,
            "name": f"Товар {i}",
            "price": 1000 * (i + 1),
            "statistics": {"likes": i, "viewCount": i*10, "contacts": i}
        }
        response = requests.post(f"{BASE_URL}/api/1/item", json=payload)
        assert response.status_code == 200
        item_id = parse_uuid_from_status(response.json()["status"])
        ids.append(item_id)
    return ids

def test_tc010_successful_get_seller_items(seller_with_items):
    response = requests.get(f"{BASE_URL}/api/1/{SELLER_ID}/item")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # Минимум те, что создали
    for item in data:
        assert item["sellerId"] == SELLER_ID

def test_tc011_invalid_sellerid_format():
    invalid_seller = "abc"
    response = requests.get(f"{BASE_URL}/api/1/{invalid_seller}/item")
    assert response.status_code == 400
    data = response.json()
    assert data["result"]["message"] == "передан некорректный идентификатор продавца"
    assert data["status"] == "400"

def test_tc012_successful_get_statistics(created_item):
    item_id = created_item
    response = requests.get(f"{BASE_URL}/api/1/statistic/{item_id}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    stats = data[0]
    assert stats["contacts"] == 3
    assert stats["likes"] == 10
    assert stats["viewCount"] == 50

def test_tc013_statistics_nonexistent_item():
    nonexistent_id = "99999999-9999-9999-9999-999999999999"
    response = requests.get(f"{BASE_URL}/api/1/statistic/{nonexistent_id}")
    assert response.status_code == 404
    data = response.json()
    assert data["result"]["message"] == f"statistic {nonexistent_id} not found"
    assert data["status"] == "404"

def test_tc014_invalid_id_format_statistics():
    invalid_id = "aaa111"
    response = requests.get(f"{BASE_URL}/api/1/statistic/{invalid_id}")
    assert response.status_code == 400
    data = response.json()
    assert data["result"]["message"] == "передан некорректный идентификатор объявления"
    assert data["status"] == "400"
