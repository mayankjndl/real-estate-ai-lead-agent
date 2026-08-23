"""Seed IREIOS 4.0 digital-twin demo inventory (1 project × 2 towers × 10 floors × 2 units).

Usage:
    python seed_twin_demo.py --client-id 1
    python seed_twin_demo.py --client-id 1 --clear
"""
from __future__ import annotations

import argparse
import random

from database import SessionLocal
from models import InventoryUnit

PROJECT = "The Summit"
LOCATION = "Downtown"
TOWERS = ("Tower A", "Tower B")
FLOORS = range(1, 11)
UNITS_PER_FLOOR = 2
# ~50% available / 25% hold / 25% sold
_STATUS_WEIGHTS = [("available", 50), ("hold", 25), ("sold", 25)]


def _pick_status(rng: random.Random) -> str:
    roll = rng.randint(1, 100)
    acc = 0
    for status, weight in _STATUS_WEIGHTS:
        acc += weight
        if roll <= acc:
            return status
    return "available"


def seed_twin_demo(client_id: int, *, clear: bool = False, seed: int = 42) -> int:
    rng = random.Random(seed)
    db = SessionLocal()
    try:
        if clear:
            db.query(InventoryUnit).filter(
                InventoryUnit.client_id == client_id,
                InventoryUnit.project_name == PROJECT,
            ).delete()
            db.commit()

        created = 0
        for tower in TOWERS:
            letter = tower.split()[-1]  # A / B
            for floor in FLOORS:
                for u in range(1, UNITS_PER_FLOOR + 1):
                    unit_code = f"{letter}-{floor}0{u}"  # A-101, A-102, A-201, …
                    exists = (
                        db.query(InventoryUnit)
                        .filter(
                            InventoryUnit.client_id == client_id,
                            InventoryUnit.unit_code == unit_code,
                        )
                        .first()
                    )
                    if exists:
                        exists.project_name = PROJECT
                        exists.tower = tower
                        exists.location = LOCATION
                        exists.meta_json = {**(exists.meta_json or {}), "floor": floor}
                        if not exists.list_price:
                            exists.list_price = rng.randint(12_000_000, 25_000_000)
                        if not exists.bhk:
                            exists.bhk = rng.choice(["2", "3", "4"])
                        if not exists.status:
                            exists.status = _pick_status(rng)
                        continue

                    db.add(
                        InventoryUnit(
                            client_id=client_id,
                            project_name=PROJECT,
                            tower=tower,
                            unit_code=unit_code,
                            bhk=rng.choice(["2", "3", "4"]),
                            location=LOCATION,
                            list_price=rng.randint(12_000_000, 25_000_000),
                            status=_pick_status(rng),
                            carpet_sqft=rng.randint(900, 1800),
                            meta_json={"floor": floor},
                        )
                    )
                    created += 1

        db.commit()
        total = (
            db.query(InventoryUnit)
            .filter(
                InventoryUnit.client_id == client_id,
                InventoryUnit.project_name == PROJECT,
            )
            .count()
        )
        print(
            f"Twin seed client={client_id} project={PROJECT!r}: "
            f"created={created} total={total} (target 40)"
        )
        return total
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed The Summit twin inventory (40 units)")
    parser.add_argument("--client-id", type=int, default=1)
    parser.add_argument("--clear", action="store_true", help="Delete existing Summit units first")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for prices/status")
    args = parser.parse_args()
    seed_twin_demo(args.client_id, clear=args.clear, seed=args.seed)
