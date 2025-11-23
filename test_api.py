import random
import pytest
import requests
import re

BASE_URL = "https://qa-internship.avito.com"
SELLER_ID = random.randint(111111, 999999)  


def parse_uuid_from_status(status_text):
    match = re.search(r"Сохранили объявление - ([a-f0-9-]{36})", status_text)
    return match.group(1) if match else None


@pytest.fixture(scope="session")
def created_item_id():
    """Создаёт одно объявление и возвращает его UUID"""
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
    assert response.status_code == 200, f"Создание упало: {response.text}"
    uuid = parse_uuid_from_status(response.json()["status"])
    assert uuid is not None and len(uuid) == 36
    return uuid


@pytest.fixture(scope="session")
def seller_with_multiple_items():
    ids = []
    for i in range(1, 3):  
        payload = {
            "sellerID": SELLER_ID,
            "name": f"Товар {i}",
            "price": 1000 * i,
            "statistics": {
                "likes": i,           
                "viewCount": i * 10,
                "contacts": i
            }
        }
        response = requests.post(f"{BASE_URL}/api/1/item", json=payload)
        assert response.status_code == 200, f"Не удалось создать item {i}: {response.text}"
        item_id = parse_uuid_from_status(response.json()["status"])
        assert item_id is not None
        ids.append(item_id)
    return ids


def test_tc001_successful_creation():
    payload = {
        "sellerID": SELLER_ID,
        "name": "Тестовое объявление",
        "price": 999,
        "statistics": {"likes": 5, "viewCount": 20, "contacts": 1}
    }
    r = requests.post(f"{BASE_URL}/api/1/item", json=payload)
    assert r.status_code == 200
    assert "Сохранили объявление -" in r.json()["status"]


def test_tc002_error_missing_sellerid():
    payload = {"name": "Без sellerID", "price": 100, "statistics": {"likes": 1, "viewCount": 1, "contacts": 1}}
    r = requests.post(f"{BASE_URL}/api/1/item", json=payload)
    assert r.status_code == 400
    assert r.json()["result"]["message"] == "поле sellerID обязательно"


def test_tc003_negative_price_with_zero_stats():
    payload = {
        "sellerID": SELLER_ID,
        "name": "Отрицательная цена",
        "price": -100,
        "statistics": {"likes": 0, "viewCount": 0, "contacts": 0}
    }
    r = requests.post(f"{BASE_URL}/api/1/item", json=payload)
    assert r.status_code == 400
    assert "поле likes обязательно" in r.json()["result"]["message"]


def test_tc003_negative_price_with_nonzero_stats():
    payload = {
        "sellerID": SELLER_ID,
        "name": "Отрицательная цена 2",
        "price": -500,
        "statistics": {"likes": 1, "viewCount": 1, "contacts": 1}
    }
    r = requests.post(f"{BASE_URL}/api/1/item", json=payload)
    assert r.status_code == 200  # ← баг: должно быть 400


def test_tc004_empty_name():
    payload = {
        "sellerID": SELLER_ID,
        "name": "",
        "price": 500,
        "statistics": {"likes": 1, "viewCount": 0, "contacts": 0}
    }
    r = requests.post(f"{BASE_URL}/api/1/item", json=payload)
    assert r.status_code == 400
    assert r.json()["result"]["message"] == "поле name обязательно"


def test_tc005_missing_statistics():
    payload = {"sellerID": SELLER_ID, "name": "Без статистики", "price": 777}
    r = requests.post(f"{BASE_URL}/api/1/item", json=payload)
    assert r.status_code == 400
    assert "поле likes обязательно" in r.json()["result"]["message"]


def test_tc006_invalid_sellerid_type():
    payload = {
        "sellerID": "abc",
        "name": "Неверный тип",
        "price": 100,
        "statistics": {"likes": 1, "viewCount": 1, "contacts": 1}
    }
    r = requests.post(f"{BASE_URL}/api/1/item", json=payload)
    assert r.status_code == 400
    assert r.json()["status"] == "не передано тело объявления"


def test_tc007_successful_get_item(created_item_id):
    r = requests.get(f"{BASE_URL}/api/1/item/{created_item_id}")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) == 1
    assert data[0]["id"] == created_item_id
    assert data[0]["name"] == "Телефон Xiaomi"


def test_tc008_get_nonexistent_item():
    fake_id = "11111111-1111-1111-1111-111111111111"
    r = requests.get(f"{BASE_URL}/api/1/item/{fake_id}")
    assert r.status_code == 404
    assert "not found" in r.json()["result"]["message"]


def test_tc009_invalid_uuid_format():
    r = requests.get(f"{BASE_URL}/api/1/item/invalid-uuid")
    assert r.status_code == 400
    assert "не UUID" in r.json()["result"]["message"]


def test_tc010_successful_get_seller_items(seller_with_multiple_items):
    r = requests.get(f"{BASE_URL}/api/1/{SELLER_ID}/item")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    assert all(item["sellerId"] == SELLER_ID for item in data)


def test_tc011_invalid_sellerid_format():
    r = requests.get(f"{BASE_URL}/api/1/abc123/item")
    assert r.status_code == 400
    assert "некорректный идентификатор продавца" in r.json()["result"]["message"]


def test_tc012_successful_get_statistics(created_item_id):
    r = requests.get(f"{BASE_URL}/api/1/statistic/{created_item_id}")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) == 1
    stats = data[0]
    assert stats["likes"] == 10 and stats["viewCount"] == 50 and stats["contacts"] == 3


def test_tc013_statistics_nonexistent_item():
    fake_id = "22222222-2222-2222-2222-222222222222"
    r = requests.get(f"{BASE_URL}/api/1/statistic/{fake_id}")
    assert r.status_code == 404


def test_tc014_invalid_id_format_statistics():
    r = requests.get(f"{BASE_URL}/api/1/statistic/invalid123")
    assert r.status_code == 400
    assert "некорректный идентификатор объявления" in r.json()["result"]["message"]
