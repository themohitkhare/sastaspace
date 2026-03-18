"""Tests for SastaHero API endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestSastaHeroClasses:
    def test_list_classes_returns_all_six(self, client: TestClient) -> None:
        response = client.get("/api/v1/sastahero/classes")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 6

    def test_list_classes_structure(self, client: TestClient) -> None:
        response = client.get("/api/v1/sastahero/classes")
        assert response.status_code == 200
        classes = response.json()
        for cls in classes:
            assert "id" in cls
            assert "name" in cls
            assert "icon" in cls
            assert "desc" in cls
            assert "base_stats" in cls
            stats = cls["base_stats"]
            for stat in ["STR", "DEX", "INT", "WIS", "VIT", "LCK"]:
                assert stat in stats
                assert isinstance(stats[stat], int)
                assert stats[stat] > 0

    def test_list_classes_contains_expected_classes(self, client: TestClient) -> None:
        response = client.get("/api/v1/sastahero/classes")
        data = response.json()
        ids = {cls["id"] for cls in data}
        assert ids == {"WARRIOR", "MAGE", "ROGUE", "RANGER", "NECRO", "PALADIN"}

    def test_warrior_base_stats(self, client: TestClient) -> None:
        response = client.get("/api/v1/sastahero/classes")
        classes = {cls["id"]: cls for cls in response.json()}
        warrior = classes["WARRIOR"]
        assert warrior["base_stats"]["STR"] == 8
        assert warrior["base_stats"]["VIT"] == 8


class TestSastaHeroGenerate:
    def test_generate_random_hero(self, client: TestClient) -> None:
        response = client.post("/api/v1/sastahero/generate", json={})
        assert response.status_code == 200
        data = response.json()
        assert "hero_class" in data
        assert "stats" in data
        assert "total_power" in data

    def test_generate_with_specific_class(self, client: TestClient) -> None:
        response = client.post("/api/v1/sastahero/generate", json={"hero_class": "MAGE"})
        assert response.status_code == 200
        data = response.json()
        assert data["hero_class"] == "MAGE"

    def test_generate_stats_are_positive(self, client: TestClient) -> None:
        response = client.post("/api/v1/sastahero/generate", json={})
        data = response.json()
        for stat_val in data["stats"].values():
            assert stat_val > 0

    def test_generate_total_power_matches_stats(self, client: TestClient) -> None:
        response = client.post("/api/v1/sastahero/generate", json={})
        data = response.json()
        expected_total = sum(data["stats"].values())
        assert data["total_power"] == expected_total

    def test_generate_stats_at_least_base(self, client: TestClient) -> None:
        """Generated stats should be >= base stats (bonus points only add)."""
        classes_resp = client.get("/api/v1/sastahero/classes")
        classes = {cls["id"]: cls for cls in classes_resp.json()}

        for _ in range(5):
            resp = client.post("/api/v1/sastahero/generate", json={})
            data = resp.json()
            hero_class = data["hero_class"]
            base = classes[hero_class]["base_stats"]
            for stat, val in data["stats"].items():
                assert val >= base[stat], f"{stat} {val} < base {base[stat]}"

    def test_generate_all_classes_work(self, client: TestClient) -> None:
        for cls in ["WARRIOR", "MAGE", "ROGUE", "RANGER", "NECRO", "PALADIN"]:
            resp = client.post("/api/v1/sastahero/generate", json={"hero_class": cls})
            assert resp.status_code == 200
            assert resp.json()["hero_class"] == cls

    def test_generate_invalid_class_returns_422(self, client: TestClient) -> None:
        response = client.post("/api/v1/sastahero/generate", json={"hero_class": "INVALID"})
        assert response.status_code == 422

    @pytest.mark.parametrize("_", range(10))
    def test_generate_stats_do_not_exceed_max(self, client: TestClient, _: int) -> None:
        response = client.post("/api/v1/sastahero/generate", json={})
        data = response.json()
        for stat, val in data["stats"].items():
            assert val <= 20, f"{stat}={val} exceeds max 20"
