import pygame
import sys
import random
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# === Load API Key ===
load_dotenv()
key = os.getenv('api_key')
client = OpenAI(api_key=key)

# === GPT Functions ===
def ask_gpt(prompt, temperature=0.8):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=150
    )
    return response.choices[0].message.content.strip()

def safe_ask_gpt(prompt, attempts=2):
    for _ in range(attempts):
        try:
            return ask_gpt(prompt)
        except Exception as e:
            print("GPT call failed:", e)
    return None

# === Game Classes ===
class Player:
    def __init__(self, hp=100):
        self.hp = hp
        self.inventory = {}
        self.gold = 50
        self.blocks_remaining = 0  
        self.atk_bonus = 0
        self.status_effects = {}

    def attack(self, enemy):
        base_damage = random.randint(5, 15)
        total_damage = base_damage + self.atk_bonus
        enemy.hp -= total_damage
        return f"You hit the {enemy.name} for {total_damage} damage!"
        

    def heal(self, amount):
        self.hp += amount
        return f"You healed for {amount} HP."

    def take_damage(self, damage):
        if self.blocks_remaining > 0:
            self.blocks_remaining -= 1
            block_sound.play()
            return f"You blocked the attack! ({self.blocks_remaining} blocks left)"
        else:
            self.hp -= damage
            random.choice(damage_sounds).play()
            return f"You took {damage} damage!"

    def buy(self, item, cost):
        if self.gold >= cost:
            self.gold -= cost
            

            if item == "Attack Buff":
                self.atk_bonus += 5  
                return f"You bought {item} for {cost} gold. Attack +5!"
            
            self.inventory[item] = self.inventory.get(item, 0) + 1
            return f"You bought {item} for {cost} gold."
        else:
            return "Not enough gold."
    
    def special_attack(self, enemy, effect="burn"):
        base_damage = random.randint(8, 18)
        total_damage = base_damage + self.atk_bonus
        enemy.hp -= total_damage
        if effect == "burn":
            enemy.status_effects["burn"] = 3
            return f"You unleash a fire blast! The {enemy.name} takes {total_damage} damage and is burning!"
        elif effect == "freeze":
            enemy.status_effects["freeze"] = 2
            return f"You freeze the enemy! The {enemy.name} takes {total_damage} damage and may skip actions!"
        else:
            return f"You use a mysterious force! The {enemy.name} takes {total_damage} damage."

class Enemy:
    def __init__(self, name, description, hp, atk, special=None, is_boss=False):
        self.name = name
        self.description = description
        self.hp = hp
        self.atk = atk
        self.is_boss = is_boss
        self.status_effects = {}
        self.special = special 

    def attack(self, player):
        log = []

        # Freeze check
        if self.status_effects.get("freeze", 0) > 0:
            self.status_effects["freeze"] -= 1
            log.append(f"{self.name} is frozen and skips its turn!")
            return "\n".join(log)

        # Base damage
        damage = random.randint(1, self.atk)
        log.append(player.take_damage(damage))

        # Burn damage if enemy is burning
        if self.status_effects.get("burn", 0) > 0:
            burn_dmg = 5
            self.hp -= burn_dmg
            self.status_effects["burn"] -= 1
            log.append(f"{self.name} is burning! (-{burn_dmg} HP)")

        # Attempt special attack (burn/freeze)
        if self.special and random.random() < 0.4:  # 40% chance to use special
            effect = self.special.get("effect")
            if effect == "burn":
                player.status_effects["burn"] = 3
                log.append(self.special.get("description", f"{self.name} scorches you! You are burning!"))
            elif effect == "freeze":
                player.status_effects["freeze"] = 2
                log.append(self.special.get("description", f"{self.name} freezes you solid!"))

        # Boss GPT flavor (optional)
        if self.is_boss:
            try:
                gpt_prompt = (
                    f"Write a short, dramatic description (1–2 sentences) of a fantasy boss named '{self.name}' "
                    f"attacking the player and dealing {damage} damage. Make it vivid and action-packed."
                )
                gpt_description = safe_ask_gpt(gpt_prompt)
                if gpt_description:
                    log.append(gpt_description)
            except:
                log.append(f"{self.name} strikes fiercely for {damage} damage!")  # fallback

        return "\n".join(log)


seen_enemies = set()


# === GPT-Generated Content ===
def generate_room():
    combat_log.append("Generating room description...")
    render_and_flip(temp_room_text="Generating room description...") 
    prompt = "Describe a fantasy dungeon room in 1-3 sentences with atmosphere, lighting, smells, and sounds."
    return safe_ask_gpt(prompt)

def generate_enemy():
    combat_log.append("Summoning an enemy...")
    render_and_flip(temp_room_text="Summoning an enemy...")

    # Scale difficulty based on room count
    min_hp = 20 + room_count * 2
    max_hp = min(70, 30 + room_count * 4)
    min_atk = 5 + room_count // 2
    max_atk = min(25, 10 + room_count * 2)

    prompt = (
    f"Create a fantasy dungeon enemy for room {room_count}. "
    f"Include name, description, HP ({min_hp}-{max_hp}), ATK ({min_atk}-{max_atk}), and an optional special ability. "
    f"Respond ONLY in JSON like:\n"
    '{{"name": "", "description": "", "hp": 50, "atk": 10, '
    '"special": {{"name": "Frost Bite", "effect": "freeze", "description": "The enemy bites with icy fangs!"}}}}'
)

    for _ in range(3):
        response = safe_ask_gpt(prompt)
        if response:
            try:
                enemy_data = json.loads(response)
                if enemy_data["name"] not in seen_enemies:
                    seen_enemies.add(enemy_data["name"])
                    return Enemy(
                        name=enemy_data["name"],
                        description=enemy_data["description"],
                        hp=enemy_data["hp"],
                        atk=enemy_data["atk"],
                        special=enemy_data.get("special")
                    )
            except json.JSONDecodeError:
                continue
    
    if random.random() < 0.3:
        effect = random.choice(["burn", "freeze"])
        description = (
            "The enemy channels flames to scorch you!" if effect == "burn"
            else "The enemy conjures ice to freeze your limbs!"
        )
        special = {"name": effect.title(), "effect": effect, "description": description}
    else:
        special = None

    # Fallback basic enemy
    return Enemy(
    name=enemy_data["name"],
    description=enemy_data["description"],
    hp=enemy_data["hp"],
    atk=enemy_data["atk"],
    special=special
)

def generate_boss():
    combat_log.append("A powerful boss approaches...")
    render_and_flip(temp_room_text="A powerful boss approaches...")

    min_hp = 100 + room_count * 3
    max_hp = 200 + room_count * 4
    min_atk = 15 + room_count // 2
    max_atk = 20 + room_count

    prompt = (
        f"Create a fantasy dungeon boss for room {room_count}. "
        f"Respond ONLY in JSON like:\n"
        '{"name": "", "description": "", "hp": 150, "atk": 20, '
        '"special": {"name": "Flame Burst", "effect": "burn", "description": "You are engulfed in fire!"}}'
    )

    for _ in range(3):
        response = safe_ask_gpt(prompt)
        if response:
            try:
                data = json.loads(response)
                return Enemy(
                    name=data["name"],
                    description=data["description"],
                    hp=data["hp"],
                    atk=data["atk"],
                    special=data.get("special"),
                    is_boss=True
                )
            except Exception:
                continue

    # fallback boss
    return Enemy(
        name="Flame Wraith",
        description="A burning ghost with blazing eyes.",
        hp=180,
        atk=25,
        special={"name": "Flame Burst", "effect": "burn", "description": "You are engulfed in fire!"},
        is_boss=True
    )
    in_combat = True


def generate_quest():
    combat_log.append("Generating a quest...")
    render_and_flip(temp_room_text="Generating a quest...")
    prompt = "Generate a fantasy dungeon quest for a player. Keep it short and exciting (1 sentence)."
    return safe_ask_gpt(prompt)

def loot_drop(player):
    if random.random() < 0.5:
        loot = random.choice(["Healing Potion", "Mysterious Pill", "Shield"])
        player.inventory[loot] = player.inventory.get(loot, 0) + 1
        return f"You found a {loot}!"
    else:
        gold_found = random.randint(5, 30)
        player.gold += gold_found
        return f"You found {gold_found} gold coins!"

def random_event(player):
    event = random.choice(["trap", "blessing"])
    if event == "trap":
        damage = random.randint(5, 15)
        return player.take_damage(damage) + "\n A hidden trap springs!"
    else:
        heal = random.randint(5, 15)
        return player.heal(heal) + "\n A magical aura surrounds you."

def render_and_flip(temp_room_text=None):
    screen.fill((0, 0, 30))
    draw_text(screen, f"HP: {player.hp}    Gold: {player.gold}", 10, color=(255, 215, 0))
    draw_text(screen, f"Room {room_count}", 40, color=(100, 200, 255))
    draw_text(screen, temp_room_text if temp_room_text is not None else room_text, 80, line_spacing=FONT_SIZE + 8)
    pygame.display.flip()

def process_status_effects(player):
    status_msgs = []
    effects_to_remove = []

    for effect, duration in player.status_effects.items():
        if effect == "burn":
            burn_dmg = 5
            player.hp -= burn_dmg
            status_msgs.append(f"You are burning! (-{burn_dmg} HP)")
        elif effect == "freeze":
            status_msgs.append("You are frozen and might skip your action!")
        player.status_effects[effect] -= 1
        if player.status_effects[effect] <= 0:
            effects_to_remove.append(effect)

    for effect in effects_to_remove:
        del player.status_effects[effect]
        status_msgs.append(f"The {effect} effect wears off.")

    return status_msgs
    

# === Shop System ===
shop_items = [
    {"name": "Healing Potion", "cost": 10},
    {"name": "Attack Buff", "cost": 25},
    {"name": "Mysterious Pill", "cost": 15},
    {"name": "Shield", "cost": 20}
]

def enter_shop(player):
    item_descriptions = {
        "Healing Potion": "Restores 20 HP",
        "Attack Buff": "+5 ATK",
        "Mysterious Pill": "???",
        "Shield": "Grants 2 temporary blocks from damage"
    }
    items = []
    for i, item in enumerate(shop_items):
        name = item['name']
        cost = item['cost']
        desc = item_descriptions.get(name, "A mysterious item.")
        label = f"[{i+1}] {name} - {cost} gold"
        items.append((label, desc))

    return items

def enter_hp_shop(player):
    return [
        ("[1] Cursed Blade", "Trade 10 HP for +10 ATK"),
        ("[2] Soul Shield", "Trade 8 HP for +4 blocks"),
        ("[3] Blood Elixir", "Trade 15 HP for +40 HP"),
        ("[4] Leave", "Walk away")
    ]

    # Each entry is (label, description, cost)
    items = []
    for i, item in enumerate(shop_items):
        name = item['name']
        cost = item['cost']
        desc = item_descriptions.get(name, "A mysterious item.")
        label = f"[{i+1}] {name} - {cost} gold"
        items.append((label, desc))

    return items


# === Item usage ===
def use_item(player, item_name):
    if player.inventory.get(item_name, 0) == 0:
        return f"You have no {item_name} to use."

    # Reduce count
    player.inventory[item_name] -= 1
    if player.inventory[item_name] <= 0:
        del player.inventory[item_name]

    if item_name == "Healing Potion":
        heal_amount = 20
        player.hp += heal_amount
        return f"You use a Healing Potion and heal {heal_amount} HP."
    
    elif item_name == "Mysterious Pill":
        result = random.choice(["good", "bad"])
        effect = random.choice(["hp", "atk", "block"])

        # Apply effect
        effect_description = ""
        if result == "good":
            if effect == "hp":
                amount = random.randint(10, 20)
                player.hp += amount
            elif effect == "atk":
                player.atk_bonus += 5
            elif effect == "block":
                player.blocks_remaining += 2

            # Ask GPT for a flavorful good effect description
            combat_log.append("Interpreting the pill's effects...")
            render_and_flip(temp_room_text="Interpreting the pill's effects...")
            gpt_prompt = f"Write a short mysterious and magical-sounding description (1 sentence) of a GOOD effect from taking a fantasy pill that affects {effect}."
            effect_description = safe_ask_gpt(gpt_prompt)

        else:  # bad outcome
            if effect == "hp":
                amount = random.randint(5, 15)
                player.hp -= amount
            elif effect == "atk" and player.atk_bonus > 0:
                player.atk_bonus -= 5
            elif effect == "block" and player.blocks_remaining > 0:
                player.blocks_remaining -= 1

            # Ask GPT for a flavorful bad effect description
            combat_log.append("Interpreting the pill's effects...")
            render_and_flip(temp_room_text="Interpreting the pill's effects...")
            gpt_prompt = f"Write a short disturbing or unsettling description (1 sentence) of a BAD effect from taking a fantasy pill that affects {effect}."
            effect_description = safe_ask_gpt(gpt_prompt)

        return f"You swallow the Mysterious Pill...\n{effect_description or 'Something strange happens.'}"
            
            
        
    elif item_name == "Shield":
        player.blocks_remaining += 2  # Stackable shield blocks
        return f" You equip a Shield. Total blocks: {player.blocks_remaining}"
    else:
        return f"You try to use {item_name}, but nothing happens."

# === Pygame Setup ===
pygame.init()
pygame.mixer.init()
purchase_sound = pygame.mixer.Sound("purchase.mp3")
damage_sounds = [
    pygame.mixer.Sound("damage.wav"),
    pygame.mixer.Sound("damage2.wav"),
    pygame.mixer.Sound("damage3.wav")
    ]
block_sound = pygame.mixer.Sound("block.wav")
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()
pygame.display.set_caption("AI Endless Dungeon")
FONT_SIZE = max(18, int(HEIGHT * 0.025))
FONT = pygame.font.SysFont("serif", FONT_SIZE)

# === UI Elements ===
SHOP_BTN_RECT = pygame.Rect(WIDTH - 360, 20, 150, 40) 
CLOSE_BTN_RECT = pygame.Rect(WIDTH - 180, 80, 150, 40)

INVENTORY_BTN_RECT = pygame.Rect(WIDTH - 180, 20, 150, 40)
INV_CLOSE_BTN_RECT = pygame.Rect(WIDTH - 180, 200, 150, 40)

RESTART_BTN_RECT = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2, 200, 60)

def draw_text(surface, text, y, color=(255, 255, 255), line_spacing=30, max_width=None):
    if max_width is None:
        max_width = WIDTH - 60
    words = text.split(' ')
    lines = []
    line = ""
    for word in words:
        test_line = line + word + " "
        if FONT.size(test_line)[0] < max_width:
            line = test_line
        else:
            lines.append(line.strip())
            line = word + " "
    lines.append(line.strip())

    for i, line in enumerate(lines):
        rendered = FONT.render(line, True, color)
        surface.blit(rendered, (30, y + i * line_spacing))

def draw_text_centered(surface, text, rect, color=(255, 255, 255)):
    rendered = FONT.render(text, True, color)
    text_rect = rendered.get_rect(center=rect.center)
    surface.blit(rendered, text_rect)

def draw_prompt_text(surface, text, y_offset=20, color=(200, 200, 200)):
    rendered = FONT.render(text, True, color)
    surface.blit(rendered, (30, HEIGHT - y_offset))

# === Game State ===
player = Player()
enemy = None
combat_log = []
room_count = 1
special_attack_last_used_room = -4 
room_text = generate_room()
quest_text = generate_quest()
combat_log = [" Quest: " + quest_text]
game_over = False
in_combat = False
shop_mode = False
inventory_mode = False
game_over_music_playing = False
post_boss_shop = False
is_hp_shop = False  
shop_display_lines = []

previous_combat_log = []
previous_room_text = ""

previous_combat_log_inv = []
previous_room_text_inv = ""

# === Game Loop ===
def start_menu():
    pygame.mixer.music.load("background.wav")
    pygame.mixer.music.set_volume(0.5)  # Volume from 0.0 to 1.0
    pygame.mixer.music.play(-1)  # -1 means loop forever
    
    menu_running = True
    title_font = pygame.font.SysFont("serif", int(FONT_SIZE * 2))
    small_font = pygame.font.SysFont("serif", FONT_SIZE)

    start_button = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 - 50, 200, 50)
    quit_button = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 20, 200, 50)

    while menu_running:
        screen.fill((10, 10, 40))

        # Draw title
        title_surf = title_font.render("AI Endless Dungeon", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 4))
        screen.blit(title_surf, title_rect)

        # Draw buttons
        pygame.draw.rect(screen, (70, 130, 180), start_button)
        draw_text_centered(screen, "Start Game", start_button)

        pygame.draw.rect(screen, (180, 70, 70), quit_button)
        draw_text_centered(screen, "Quit", quit_button)

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if start_button.collidepoint(event.pos):
                    menu_running = False
                elif quit_button.collidepoint(event.pos):
                    pygame.quit()
                    sys.exit()

        pygame.display.flip()
        clock.tick(60)

clock = pygame.time.Clock()

start_menu()

while True:
    screen.fill((0, 0, 30))

    # === Event Handling ===
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            if game_over and RESTART_BTN_RECT.collidepoint(mouse_pos):
                # Reset all game state variables
                player = Player()
                enemy = None
                combat_log.clear()
                room_count = 1
                room_text = generate_room()
                quest_text = generate_quest()
                combat_log = [" Quest: " + quest_text]
                game_over = False
                in_combat = False
                shop_mode = False
                inventory_mode = False
                game_over_music_playing = False
                pygame.mixer.music.stop()
                pygame.mixer.music.load("background.wav")
                pygame.mixer.music.play(-1)


            if SHOP_BTN_RECT.collidepoint(mouse_pos) and not shop_mode and not inventory_mode:
                shop_mode = True
                previous_combat_log = combat_log[:]
                previous_room_text = room_text
                shop_display_lines = enter_shop(player)  # <-- only store display info
                combat_log = ["Welcome to the Dungeon Shop!", f"You have {player.gold} gold."]
            elif INVENTORY_BTN_RECT.collidepoint(mouse_pos) and not inventory_mode and not shop_mode:
                inventory_mode = True
                previous_combat_log_inv = combat_log[:]
                previous_room_text_inv = room_text
                if player.inventory:
                    combat_log = ["Inventory:"]
                    for i, (item, count) in enumerate(player.inventory.items()):
                        label = f"{item} x{count}" if count > 1 else item
                        combat_log.append(f"[{i+1}] {label}")
                else:
                    combat_log = ["Inventory is empty."]
            elif CLOSE_BTN_RECT.collidepoint(mouse_pos) and shop_mode:
                shop_mode = False
                combat_log = previous_combat_log[:]
                room_text = previous_room_text
            elif INV_CLOSE_BTN_RECT.collidepoint(mouse_pos) and inventory_mode:
                inventory_mode = False
                combat_log = previous_combat_log_inv[:]
                room_text = previous_room_text_inv

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()

            if game_over:
                if event.key == pygame.K_x:
                    pygame.quit()
                    sys.exit()
                continue

            if shop_mode:
                if event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4]:
                    index = event.key - pygame.K_1
                    if 0 <= index < len(shop_items):
                        item = shop_items[index]
                        result = player.buy(item['name'], item['cost'])
                        combat_log.append(result)
                        if "You bought" in result:
                          purchase_sound.play()
                elif event.key == pygame.K_ESCAPE:
                    shop_mode = False
                    combat_log = previous_combat_log[:]
                    room_text = previous_room_text
                    combat_log.append("You exit the shop.")

            elif inventory_mode:
                if event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9]:
                    idx = event.key - pygame.K_1
                    inventory_keys = list(player.inventory.keys())
                    if 0 <= idx < len(inventory_keys):
                        item_name = inventory_keys[idx]
                        result = use_item(player, item_name)
                        new_log = [result]
                        
                        if player.inventory:
                            new_log.append("Inventory:")
                            for i, (item, count) in enumerate(player.inventory.items()):
                                label = f"{item} x{count}" if count > 1 else item
                                new_log.append(f"[{i+1}] {label}")
                        else:
                            new_log.append("Inventory is empty.")

                        combat_log = new_log
                
                elif event.key == pygame.K_ESCAPE:
                    inventory_mode = False
                    combat_log = previous_combat_log_inv[:]
                    room_text = previous_room_text_inv
                    combat_log.append("You close the inventory.")
            
            elif post_boss_shop:
                if event.key == pygame.K_1:
                    if player.hp > 10:
                        player.hp -= 10
                        player.atk_bonus += 10
                        combat_log = ["You grasp the Cursed Blade. Power surges through your veins."]
                    else:
                        combat_log = ["You don't have enough HP for the Cursed Blade."]
                    post_boss_shop = False
                elif event.key == pygame.K_2:
                    if player.hp > 8:
                        player.hp -= 8
                        player.blocks_remaining += 4
                        combat_log = ["The Soul Shield binds to your aura. You feel protected."]
                    else:
                        combat_log = ["Not enough HP for the Soul Shield."]
                    post_boss_shop = False
                elif event.key == pygame.K_3:
                    if player.hp > 15:
                        player.hp -= 15
                        player.hp += 40
                        combat_log = ["You drink the Blood Elixir. It burns... then heals."]
                    else:
                        combat_log = ["Too little HP to survive the Blood Elixir."]
                    post_boss_shop = False
                elif event.key == pygame.K_4 or event.key == pygame.K_ESCAPE:
                    combat_log = ["You nod to the shopkeeper and walk on."]
                    post_boss_shop = False

            elif not in_combat and not shop_mode and not inventory_mode:
                room_count += 1
                if random.random() < 0.1:
                    room_text = "You find a Golden Room! The walls gleam with treasure!"
                    player.gold += 50
                    combat_log = ["You found a hidden cache and gained 50 gold!"]
                else:
                    room_text = generate_room()
                    if room_count % 10 == 0:
                        enemy = generate_boss()
                        combat_log = [f"⚔️ BOSS ENCOUNTER: {enemy.name} ⚔️",
                                    f"{enemy.description} (HP: {enemy.hp}, ATK: {enemy.atk})"]
                        in_combat = True
                    else:
                        if random.random() < 0.7:
                            enemy = generate_enemy()
                            combat_log = [f"You encounter: {enemy.name}",
                                        f"{enemy.description} (HP: {enemy.hp}, ATK: {enemy.atk})"]
                            in_combat = True
                        else:
                            combat_log = [random_event(player)]
               
                    
            else:
                if in_combat and event.key in [pygame.K_a, pygame.K_s]:
                    status_msgs = process_status_effects(player)

                    if "freeze" in player.status_effects:
                        combat_log = status_msgs + ["You're frozen and skip this turn!"]
                        continue

                    if event.key == pygame.K_a:
                        combat_log = status_msgs + [player.attack(enemy)]
                    elif event.key == pygame.K_s:
                        if room_count - special_attack_last_used_room >= 4:
                            effect = random.choice(["burn", "freeze"])
                            combat_log = status_msgs + [player.special_attack(enemy, effect)]
                            special_attack_last_used_room = room_count
                        else:
                            turns_left = 4 - (room_count - special_attack_last_used_room)
                            combat_log = status_msgs + [f"Special attack not ready! {turns_left} more room(s) needed "]

                    if enemy.hp > 0:
                        combat_log.append(enemy.attack(player))
                    else:
                        combat_log.append(loot_drop(player))
                        if enemy.is_boss:
                            post_boss_shop = True
                            shop_mode = True
                            is_hp_shop = True
                            previous_combat_log = combat_log[:]
                            previous_room_text = room_text
                            shop_display_lines = enter_hp_shop(player)
                            combat_log = ["A shadowy shopkeeper appears...", "Trade your health for power."]
                        in_combat = False
            
            if player.hp <= 0:
                game_over = True
                combat_log.append("Game over...")
                render_and_flip(temp_room_text="Game over...")
                
                # Ask GPT for a dramatic death message
                death_prompt = (
                    f"Write a short, dramatic fantasy-style death narration for a dungeon crawler who just died in room {room_count}. "
                    f"Make it vivid, somber, and 1–2 sentences long."
                )
                try:
                    death_text = safe_ask_gpt(death_prompt)
                except:
                    death_text = "You died in the dungeon, your journey ending in silence."

                combat_log.append(death_text)

                if not game_over_music_playing:
                    pygame.mixer.music.stop()
                    pygame.mixer.music.load("game_over.flac")  # Your game over music
                    pygame.mixer.music.play(-1)
                    game_over_music_playing = True
            
            

            if game_over and event.key == pygame.K_x:
                pygame.quit()
                sys.exit()
            
            elif event.key == pygame.K_r and in_combat:
                # Try to run from combat with 50% success chance
                if random.random() < 0.5:
                    combat_log.append("You successfully ran away!")
                    in_combat = False
                else:
                    combat_log.append("You failed to escape!")
                    combat_log.append(enemy.attack(player))
        

    # === Draw UI ===
    draw_text(screen, f"HP: {player.hp}    Gold: {player.gold}", 10, color=(255, 215, 0))
    draw_text(screen, f"Room {room_count}", 40, color=(100, 200, 255))
    draw_text(screen, room_text or "", 80, line_spacing=FONT_SIZE + 8)

    # Draw buttons
    pygame.draw.rect(screen, (70, 130, 180), SHOP_BTN_RECT)
    draw_text_centered(screen, "Open Shop", SHOP_BTN_RECT)

    pygame.draw.rect(screen, (70, 180, 130), INVENTORY_BTN_RECT)
    draw_text_centered(screen, "Inventory", INVENTORY_BTN_RECT)

    if shop_mode:
        pygame.draw.rect(screen, (20, 20, 50), pygame.Rect(20, 140, WIDTH - 40, HEIGHT - 260))

        # Title
        draw_text(screen, "Welcome to the Dungeon Shop!", 150)
        draw_text(screen, f"You have {player.gold} gold.", 180)

        # Shop items in columns
        col_width = WIDTH // 2
        x_offsets = [40, col_width + 20]  # Left and right columns
        y_start = 220
        y_spacing = FONT_SIZE * 3

        for i, (label, desc) in enumerate(shop_display_lines):
            col = i % 2
            row = i // 2
            x = x_offsets[col]
            y = y_start + row * y_spacing

            label_surf = FONT.render(label, True, (255, 255, 255))
            desc_surf = FONT.render(f"➤ {desc}", True, (180, 180, 180))

            screen.blit(label_surf, (x, y))
            screen.blit(desc_surf, (x + 20, y + FONT_SIZE))

        # Close button
        pygame.draw.rect(screen, (180, 70, 70), CLOSE_BTN_RECT)
        draw_text_centered(screen, "Close Shop", CLOSE_BTN_RECT)

    elif inventory_mode:
        pygame.draw.rect(screen, (20, 20, 50), pygame.Rect(20, 140, WIDTH - 40, HEIGHT - 260))
        draw_text(screen, "\n".join(combat_log[-12:]), 160, line_spacing=FONT_SIZE + 6)

        pygame.draw.rect(screen, (70, 180, 130), INV_CLOSE_BTN_RECT)
        draw_text_centered(screen, "Close Inv.", INV_CLOSE_BTN_RECT)

    elif post_boss_shop:
        pygame.draw.rect(screen, (30, 10, 40), pygame.Rect(20, 140, WIDTH - 40, HEIGHT - 260))
        draw_text(screen, "Shadowy Shopkeeper:", 160)
        draw_text(screen, "Trade HP for powerful artifacts...", 200)

        hp_shop_lines = enter_hp_shop(player)
        y_offset = 240
        for label, desc in hp_shop_lines:
            draw_text(screen, f"{label}  ➤ {desc}", y_offset)
            y_offset += FONT_SIZE * 2

    else:
        draw_text(screen, "\n".join(str(line) for line in combat_log[-6:] if line is not None), 250, line_spacing=FONT_SIZE + 6)

    if game_over:
        draw_text(screen, "GAME OVER - Press [X] To Quit", HEIGHT - 60, color=(255, 100, 100))

        pygame.draw.rect(screen, (50, 150, 50), RESTART_BTN_RECT)
        draw_text_centered(screen, "Restart Game", RESTART_BTN_RECT)
    
    elif in_combat and not shop_mode and not inventory_mode:
        draw_prompt_text(screen, "Press [A] to attack, [S] for special, or [R] to run", y_offset=40)
    elif not in_combat and not shop_mode and not inventory_mode and not game_over:
        draw_prompt_text(screen, "Press any key to continue...", y_offset=40)

    pygame.display.flip()
    clock.tick(60)