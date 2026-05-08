import random

PLAYER_MAX_HEALTH = 150

WEAPONS = {
    "Blades of Chaos": {"damage": 8, "defense": 4, "rage_bonus": 2},
    "Leviathan Axe": {"damage": 7, "defense": 6, "rage_bonus": 1},
    "Draupnir Spear": {"damage": 6, "defense": 4, "rage_bonus": 1},
    "Blade of Olympus": {"damage": 9, "defense": 2, "rage_bonus": 0},
    "Claws of Hades": {"damage": 5, "defense": 2, "rage_bonus": 1},
}

ENEMIES = [
    {"name": "Draugr", "health": 55, "attack": (9, 13)},
    {"name": "Hel-Walker", "health": 70, "attack": (11, 15)},
    {"name": "Dark Elf", "health": 85, "attack": (13, 17)},
]

GREEK_BOSSES = [
    {"name": "Ares", "health": 220, "attack": (18, 26), "rage_resist": 3},
    {"name": "Hades", "health": 260, "attack": (16, 24), "rage_resist": 2},
    {"name": "Zeus", "health": 300, "attack": (20, 30), "rage_resist": 4},
]

NORSE_BOSSES = [
    {"name": "Baldur", "health": 240, "attack": (17, 25), "rage_resist": 3},
    {"name": "Thor", "health": 320, "attack": (22, 32), "rage_resist": 4},
    {"name": "Heimdall", "health": 280, "attack": (19, 27), "rage_resist": 5},
]

def kratos_say(text):
    print(f"\nKratos: {text}\n")

def choose_weapon():
    kratos_say("Choose your weapon.")
    for i, weapon in enumerate(WEAPONS.keys(), start=1):
        print(f"{i}. {weapon}")
    choice = int(input("> ")) - 1
    weapon = list(WEAPONS.keys())[choice]
    kratos_say(f"You wield the {weapon}.")
    return weapon

def create_enemy(room):
    if room % 5 == 0:
        boss_pool = GREEK_BOSSES + NORSE_BOSSES
        boss = random.choice(boss_pool).copy()
        boss["is_boss"] = True
        kratos_say(f"A god stands before you. {boss['name']}.")
        return boss

    enemy = random.choice(ENEMIES).copy()
    enemy["health"] += room * 3
    enemy["attack"] = (
        enemy["attack"][0] + room // 2,
        enemy["attack"][1] + room // 2
    )
    enemy["is_boss"] = False
    return enemy

def calculate_player_damage(base, weapon, rage, resist=0):
    dmg = base + weapon["damage"] + rage * 2 - resist
    return max(5, dmg)

def calculate_enemy_damage(raw, defense, rage, dodged):
    mitigation = defense + rage
    if dodged:
        mitigation += 4
    return max(2, raw - mitigation)

def combat(player):
    enemy = create_enemy(player["room"])
    kratos_say(f"You face {enemy['name']}.")

    while enemy["health"] > 0 and player["health"] > 0:
        print(f"Health: {player['health']} | Rage: {player['rage']} | Room: {player['room']}")
        print(f"{enemy['name']} Health: {enemy['health']}")
        print("1. Attack")
        print("2. Dodge")
        print("3. Focus Rage")

        choice = input("> ").strip()
        dodged = False

        if choice == "1":
            resist = enemy.get("rage_resist", 0)
            dmg = calculate_player_damage(
                random.randint(12, 18),
                WEAPONS[player["weapon"]],
                player["rage"],
                resist
            )
            enemy["health"] -= dmg
            player["rage"] += WEAPONS[player["weapon"]]["rage_bonus"]
            kratos_say(f"You strike with fury. Damage: {dmg}")

        elif choice == "2":
            dodged = random.random() < 0.6
            kratos_say("You evade." if dodged else "You brace for impact.")

        elif choice == "3":
            player["rage"] += 3
            kratos_say("Your rage deepens.")

        else:
            kratos_say("Weakness will kill you.")
            continue

        if enemy["health"] > 0:
            raw = random.randint(*enemy["attack"])
            final = calculate_enemy_damage(
                raw,
                WEAPONS[player["weapon"]]["defense"],
                player["rage"],
                dodged
            )
            player["health"] -= final
            kratos_say(f"{enemy['name']} strikes you for {final}.")

    if player["health"] <= 0:
        kratos_say("This is where your story ends.")
        return False

    if enemy.get("is_boss"):
        player["gods_killed"] += 1
        kratos_say(f"A god has fallen. Total gods slain: {player['gods_killed']}")

    heal = random.randint(10, 18)
    player["health"] = min(PLAYER_MAX_HEALTH, player["health"] + heal)
    player["rage"] = max(0, player["rage"] - 2)

    kratos_say(f"{enemy['name']} is defeated. You recover {heal} health.")
    return True

def save_legacy(room, gods_killed):
    try:
        with open("legacy.txt", "r") as f:
            best_room, best_gods = map(int, f.read().split(","))
    except:
        best_room, best_gods = 0, 0

    new_record = False
    if room > best_room:
        with open("legacy.txt", "w") as f:
            f.write(f"{room},{gods_killed}")
        new_record = True

    return best_room, best_gods, new_record

def game():
    player = {
        "health": PLAYER_MAX_HEALTH,
        "rage": 0,
        "room": 1,
        "weapon": choose_weapon(),
        "gods_killed": 0
    }

    kratos_say("The trial begins. It ends only in death.")

    while True:
        if not combat(player):
            break
        player["room"] += 1

    best_room, best_gods, new_record = save_legacy(
        player["room"],
        player["gods_killed"]
    )

    kratos_say(f"You fell in room {player['room']}.")
    kratos_say(f"Gods slain: {player['gods_killed']}")
    kratos_say(f"Best run: Room {best_room} | Gods slain: {best_gods}")

    if new_record:
        kratos_say("A new legacy is carved in blood.")

if __name__ == "__main__":
    game()
