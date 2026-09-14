"""Verbatim public-source component for local oracle tests, NOT a full engine.

Source: Kaggle/kaggle-environments/kaggle_environments/envs/kaggriculture/
kaggriculture.py, function _daily_refresh_plants; Git blob
3c202c7ee921da239356789e266b694635103fc4, retrieved 2026-09-12 UTC.
Live mechanics additionally require structural parity with this excerpt.
"""
CROPS = {
    'WHEAT': {'seed':10,'first_yield_day':2,'max_yield_day':4,'interval':0,'max_yield':6,'ongoing':False},
    'CARROT': {'seed':20,'first_yield_day':2,'max_yield_day':3,'interval':0,'max_yield':4,'ongoing':False},
    'TOMATO': {'seed':50,'first_yield_day':8,'max_yield_day':8,'interval':1,'max_yield':4,'ongoing':True},
    'STRAWBERRY': {'seed':100,'first_yield_day':10,'max_yield_day':10,'interval':2,'max_yield':4,'ongoing':True},
    'MELON': {'seed':80,'first_yield_day':10,'max_yield_day':12,'interval':0,'max_yield':6,'ongoing':False},
}

def _daily_refresh_plants(farm, current_day, turns_per_day):
    board_size = len(farm["tiles"])
    next_day = current_day + 1
    for y in range(board_size):
        for x in range(board_size):
            tile = farm["tiles"][y][x]
            if not isinstance(tile, dict) or tile.get("kind") != "PLANT":
                continue
            was_watered = tile["watered_today"]
            if was_watered:
                tile["consecutive_unwatered"] = 0
            else:
                tile["consecutive_unwatered"] += 1
            tile["watered_today"] = False
            if tile["consecutive_unwatered"] >= 2:
                farm["tiles"][y][x] = {"kind": "WEED"}
                continue
            cd = CROPS[tile["crop"]]
            if not cd["ongoing"]:
                continue
            days_since_first = next_day - tile["planted_day"] - cd["first_yield_day"]
            if days_since_first < 0:
                continue
            interval = cd["interval"]
            if days_since_first % interval != 0:
                continue
            production_count = days_since_first // interval + 1
            if production_count > cd["max_yield"]:
                continue
            # Fertilizer bonus only applies on watered days (basic needs first).
            fertilized = was_watered and tile.get("fertilized_until_day", -1) >= current_day
            tile["yield_units"] = min(cd["max_yield"], tile["yield_units"] + (2 if fertilized else 1))
            if production_count == cd["max_yield"]:
                tile["max_lifespan_step"] = (next_day + 1) * turns_per_day
