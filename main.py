import json
import threading
import time

import pygame
from win32api import GetSystemMetrics

from audio import Audio, AudioEngine2D
from data.Scripts.Utils import *

os.system("cls")

# +------------------------------------------------------------+
# |                Made by Jonáš Erlebach                      |
# |  Thanks to third party libraries from https://pypi.org/    |
# |          explosion animation from animatedimages.org       |
# +------------------------------------------------------------+


WORKING_DIR = os.getcwd()
assert os.path.exists(
    WORKING_DIR + "\\" + "data"), "Could not file data folder please open exe file in same folder as where is located data folder"
DATA_DIR = WORKING_DIR + "\\" + "data"

with open(DATA_DIR + "\\Settings\\Game.json", "r") as file:
    GAME_SETTINGS = json.loads(file.read())

pygame.init()
pygame.font.init()

ae = AudioEngine2D()

myfont = pygame.font.SysFont('Arial', 24)

Critical = pygame.font.SysFont("Arial", 40)
SCREENW, SCREENH = GAME_SETTINGS["WIDTH"], GAME_SETTINGS["HEIGHT"]

controls_js = None
running = True
screen = pygame.display.set_mode([SCREENW, SCREENH])
pygame.display.set_caption("AirWarfare")
FPS_LIMIT = 0

clock = pygame.time.Clock()

Vector2 = pygame.math.Vector2
Vector3 = pygame.math.Vector3


# TODO: Problem here
ae.start_engine()

"""
sound effects
"""

EXPLOSION = Audio(
    Name="Explosion",
    Volume=GAME_SETTINGS["VOLUMES"]["EXPLOSION"],
    Position=[0, 0],
    AudioRange=GAME_SETTINGS["VOLUMERANGE"]["EXPLOSION"],
    Sound=pygame.mixer.Sound(DATA_DIR + "\\Sound\\explosion.ogg")
)

SHOOT = Audio(
    Name="Shoot",
    Volume=GAME_SETTINGS["VOLUMES"]["SHOOT"],
    Position=[0, 0],
    AudioRange=GAME_SETTINGS["VOLUMERANGE"]["SHOOT"],
    Sound=pygame.mixer.Sound(DATA_DIR + "\\Sound\\shoot.ogg")
)

HIT = Audio(
    Name="Hit",
    Volume=GAME_SETTINGS["VOLUMES"]["HIT"],
    Position=[0, 0],
    AudioRange=GAME_SETTINGS["VOLUMERANGE"]["HIT"],
    Sound=pygame.mixer.Sound(DATA_DIR + "\\Sound\\hit.ogg")
)

"""
uch_ prefix means that variable is changeable only by user: user changeable
"""

uch_DEBUGGING = False

FPS = 240

BULLET_LIFETIME = 5

entities = []
bullets = []
MAP_RECTANGLE = pygame.Rect((-4000 + 0, -4000 + 0), (2000 * 4, 2000 * 4))

C_X = 0
C_Y = 0

"""
Prefix R = Ray
"""
R_LEN = GAME_SETTINGS["R_LEN"]
R_RANGE = GAME_SETTINGS["R_RANGE"]
R_HITBOX_SIZE = GAME_SETTINGS["R_HITBOX_SIZE"]
R_DEPTH = GAME_SETTINGS["R_DEPTH"]
DRAW_TRACERS = GAME_SETTINGS["DRAW_TRACERS"]

R_VIEWRANGE = GAME_SETTINGS["R_VIEWRANGE"]
R_DRAW_CIRCLES = GAME_SETTINGS["DRAW_ENEMY_RAY_CIRCLES"]

ANGLE_ADDER = 1.75
MOTOR_MINUSER = 50

NEEDED_KEYS = {}
AMMO_INFO = {}

IMPLEMENTED_AMMOTYPES = ["20", "303", "792"]

USER_UUID = make_uuid()

""" Menu """
IN_MENU = True
GAME_STATE = None

""" Multiplayer vars"""
MP_IP = ""
MP_PORT = 0

try:
    with open(WORKING_DIR + "\\" + "data" + "\\" + "NeededKeys.json", "r") as file:
        NEEDED_KEYS = json.loads(file.read())
except Exception as e:
    raise Exception("??: Unknown Exception: ", e)

assert "KEYS" in NEEDED_KEYS.keys(), "LINE: ~58~ -> Could not load file needed keys from data folder make sure you openening exe in same folder as where is data folder "

with open(DATA_DIR + "\\Settings\\AmmoTypes.json", "r") as file:
    AMMO_INFO = json.loads(file.read())

for ammotype in IMPLEMENTED_AMMOTYPES:
    assert ammotype in AMMO_INFO, "AmmoTypes.json is not new enough"

if GetSystemMetrics(43) > 3:
    buttons = 5
else:
    buttons = 3


class EnemyState(Enum):
    PURSUING = auto()
    WONDERING = auto()


class Circle:
    def __init__(self, pos, radius):
        self.pos = Vector2(pos)
        self.radius = radius

    def draw(self):
        pygame.draw.circle(screen, (255, 255, 0), self.pos, self.radius)


class Bullet:
    def __init__(self, angle, startx, starty, _type, owner):
        self.info = AMMO_INFO[_type]
        self.BORNED = time.time()
        self.angle = angle
        self.alive = True
        self.position = [startx, starty]
        self.hitbox = Circle([startx, starty], 1)
        self.owner = owner

    def update(self, dt) -> None:
        self.hitbox = Circle(self.position, self.info["SIZE"])
        for i in entities:
            if circles_collide(i.hitbox, self.hitbox):
                if self.owner == i.uuid:
                    continue
                i.get_hit(self.info["DAMAGE"] / 3 if self.owner != USER_UUID else self.info["DAMAGE"])
                self.alive = False
        self.position[0] += math.cos(self.angle) * self.info["SPEED"] * dt
        self.position[1] += math.sin(self.angle) * self.info["SPEED"] * dt

    def render(self) -> None:
        global drawing
        self.hitbox.draw()


class SpriteSheet:
    """
    from:
    https://github.com/russs123/pygame_tutorials
    """

    def __init__(self, image):
        self.sheet = image

    def get_image(self, frame, width, height, scale) -> pygame.Surface:
        image = pygame.Surface((width, height)).convert_alpha()
        image.blit(self.sheet, (0, 0), ((frame * width), 0, width, height))
        image = pygame.transform.scale(image, (width * scale, height * scale))
        return image


class Player:
    def __init__(self, sprite_info):
        self.position = [SCREENW // 2, SCREENH // 2]
        self.angle = math.pi * 1.5
        self.deltas = [math.cos(self.angle), math.sin(self.angle)]
        self.motor_percentage = 70
        self.guns = {}
        self.hitbox = None

        self.uuid = USER_UUID

        self.constants = {

        }

        self.alive = True
        self.ooc = False
        self.lastooc = False
        self.ooc_timer = 0
        assert sprite_info is not None, "Class Player -> param: spritename -> Error: This parameter cant be None"
        self.sprite_info = {"PLANE_TIMER": time.time()}
        self.load_sprite_info(sprite_info)
        self.sprite = pygame.image.load(DATA_DIR + self.sprite_info["SPRITE_LOCATION"]).convert()
        self.spritesheet = SpriteSheet(self.sprite)
        self.MAX_HP = self.sprite_info["HP"]

    def fire(self) -> None:
        topleft = [
            self.position[0] + math.cos(self.angle - 0.78) * (
                    (self.sprite_info["DIMENSIONS"][0] * self.sprite_info["PLANE_SCALE"]) / 1.41),
            self.position[1] + math.sin(self.angle - 0.78) * (
                    (self.sprite_info["DIMENSIONS"][1] * self.sprite_info["PLANE_SCALE"]) / 1.41)
        ]
        for ammotype in self.guns:
            if self.guns[ammotype]["LAST_SHOT"] + self.guns[ammotype]["TIMEOUT"] <= time.time():
                if self.guns[ammotype]["RESERVE"] <= 0:
                    continue
                self.guns[ammotype]["LAST_SHOT"] = time.time()
                for GUNPOS in self.guns[ammotype]["POSITION"]:
                    righty = [
                        topleft[0] + math.cos(self.angle - math.pi) * (GUNPOS[1] * self.sprite_info["PLANE_SCALE"]),
                        topleft[1] + math.sin(self.angle - math.pi) * (GUNPOS[1] * self.sprite_info["PLANE_SCALE"])]
                    backer = [
                        topleft[0] + math.cos(self.angle - math.pi) * (
                                (GUNPOS[1] - 1) * self.sprite_info["PLANE_SCALE"]),
                        topleft[1] + math.sin(self.angle - math.pi) * (
                                (GUNPOS[1] - 1) * self.sprite_info["PLANE_SCALE"])]
                    from_ = [
                        backer[0] + math.cos(self.angle + (math.pi / 2)) * (
                                (GUNPOS[0]) * self.sprite_info["PLANE_SCALE"]),
                        backer[1] + math.sin(self.angle + (math.pi / 2)) * (GUNPOS[0] * self.sprite_info["PLANE_SCALE"])
                    ]
                    to_ = [
                        righty[0] + math.cos(self.angle + (math.pi / 2)) * (
                                GUNPOS[0] * self.sprite_info["PLANE_SCALE"]),
                        righty[1] + math.sin(self.angle + (math.pi / 2)) * (GUNPOS[0] * self.sprite_info["PLANE_SCALE"])
                    ]
                    self.guns[ammotype]["RESERVE"] -= 1
                    SHOOT.Position = to_
                    pygame.draw.circle(screen, (0, 255, 0), to_, 12)
                    ae.play(SHOOT)
                    bullets.append(Bullet(calculate_angle(to_, from_), to_[0], to_[1], ammotype, self.uuid))

    def load_sprite_info(self, spi) -> None:
        if ".json" not in spi:
            spi += ".json"
        with open(DATA_DIR + "\\" + "SpriteInfo" + "\\" + spi) as file:
            info = json.loads(file.read())
        for key in NEEDED_KEYS["KEYS"]:
            if key not in info.keys():
                raise KeyError("Class Player -> Function load_sprite_info ->", spi,
                               "dosent have all needed keys please check data/NeededKeys.json and insure", spi,
                               "has all keys")
        self.sprite_info = info
        self.guns = info["GUNS"]
        self.update_hitboxes()

    def update_hitboxes(self) -> None:
        if self.hitbox is None:
            for PART in self.sprite_info["HITBOXES"]:
                part_bb = self.sprite_info["HITBOXES"][PART]["BOUNDING_BOX"]
                part_bb[0] = self.position[0]
                part_bb[1] = self.position[1]
                self.hitbox = Circle(Vector2(part_bb), 25 * self.sprite_info["PLANE_SCALE"])

    def get_hit(self, damage) -> None:
        self.sprite_info["HP"] -= damage
        if self.sprite_info["HP"] <= 0:
            self.alive = False

    def render(self) -> None:
        global ang
        if self.sprite_info["PLANE_TIMER"] + self.sprite_info["PLANE_TIMEOUT"] <= time.time():
            self.sprite_info["PLANE_TIMER"] = time.time()
            self.sprite_info["PLANE_FRAME"] += 1
            if self.sprite_info["PLANE_FRAME"] >= self.sprite_info["FRAMES"]:
                self.sprite_info["PLANE_FRAME"] = 1
        IMG = self.spritesheet.get_image(self.sprite_info["PLANE_FRAME"], self.sprite_info["DIMENSIONS"][0],
                                         self.sprite_info["DIMENSIONS"][1], self.sprite_info["PLANE_SCALE"])
        image_copy = pygame.transform.rotate(IMG, -math.degrees(self.angle + 1.57079633))
        image_copy.set_colorkey(self.sprite_info["PLANE_BACKGROUD"])

        screen.blit(image_copy, (
            self.position[0] - int(image_copy.get_width() / 2), self.position[1] - int(image_copy.get_height() / 2)))
        done = [20, 0]
        for GUN in self.guns:
            textsurface = myfont.render(f"{GUN}: {self.guns[GUN]['RESERVE']}", True, (255, 255, 255))
            screen.blit(textsurface, (SCREENW - textsurface.get_size()[0], done[1]))
            done[0] += textsurface.get_size()[0]
            done[1] += textsurface.get_size()[1]
        """
        HP bar
        """
        hp_perc = get_percentage(self.MAX_HP, self.sprite_info["HP"])

        topleft = [
            self.position[0] - (self.sprite_info["DIMENSIONS"][0] * self.sprite_info["PLANE_SCALE"]) / 1.5,
            self.position[1] - percentage((self.sprite_info["DIMENSIONS"][0] * self.sprite_info["PLANE_SCALE"]) / 2,
                                          hp_perc)
        ]
        botleft = [
            self.position[0] - (self.sprite_info["DIMENSIONS"][0] * self.sprite_info["PLANE_SCALE"]) / 1.5,
            self.position[1] + percentage((self.sprite_info["DIMENSIONS"][0] * self.sprite_info["PLANE_SCALE"]) / 2,
                                          hp_perc)
        ]
        pygame.draw.line(screen, (255, 0, 0), botleft, topleft, 5)
        # self.hitbox.draw()
        # pygame.draw.circle(screen, (0, 0, 255), self.position, 3)

    def motor(self, doru, dt) -> None:
        if doru == 1:
            self.motor_percentage += MOTOR_MINUSER * dt
            if self.motor_percentage >= 100:
                self.motor_percentage = 100
        if doru == 0:
            self.motor_percentage -= MOTOR_MINUSER * dt
            if self.motor_percentage <= 60:
                self.motor_percentage = 60

    def move(self, direction: int, dt) -> None:
        """
        :param direction: 0 up, 1 left, 2 down, 3 right
        :param dt: deltatime float or int
        :return:
        """

        if direction == 1:
            self.angle -= ANGLE_ADDER * dt
            if self.angle < 0:
                self.angle += 2 * math.pi
            self.deltas[0] = math.cos(self.angle)
            self.deltas[1] = math.sin(self.angle)
        if direction == 3:
            self.angle += ANGLE_ADDER * dt
            if self.angle > 2 * math.pi:
                self.angle -= 2 * math.pi
            self.deltas[0] = math.cos(self.angle)
            self.deltas[1] = math.sin(self.angle)

    def update(self, dt) -> None:
        global C_X, C_Y
        if not MAP_RECTANGLE.collidepoint(self.position):
            self.ooc = True
        else:
            self.ooc = False

        if not self.lastooc and self.ooc:
            self.ooc_timer = time.time()

        if self.ooc:
            combatz_warn1 = Critical.render(f"Get back to the combat zone!", True, (255, 0, 0))
            combatz_warn2 = Critical.render(f"You have {round(self.ooc_timer + 5 - time.time(), 1)}", True, (255, 0, 0))
            screen.blit(combatz_warn1, (SCREENW // 2 - (combatz_warn1.get_size()[0]) // 2, 0))
            screen.blit(combatz_warn2, (SCREENW // 2 - (combatz_warn2.get_size()[0]) // 2, combatz_warn1.get_size()[1]))
            if self.ooc_timer + 5 < time.time():
                self.alive = False
                self.ooc = False

        self.position[0] += self.deltas[0] * (percentage(self.sprite_info["PLANE_SPEED"], self.motor_percentage)) * dt
        self.position[1] += self.deltas[1] * (percentage(self.sprite_info["PLANE_SPEED"], self.motor_percentage)) * dt
        for ent in entities:
            ent.position[0] -= self.deltas[0] * (
                percentage(self.sprite_info["PLANE_SPEED"], self.motor_percentage)) * dt
            ent.position[1] -= self.deltas[1] * (
                percentage(self.sprite_info["PLANE_SPEED"], self.motor_percentage)) * dt
        for bullet in bullets:
            bullet.position[0] -= self.deltas[0] * (
                percentage(self.sprite_info["PLANE_SPEED"], self.motor_percentage)) * dt
            bullet.position[1] -= self.deltas[1] * (
                percentage(self.sprite_info["PLANE_SPEED"], self.motor_percentage)) * dt
        for exp in explosions:
            exp.position[0] -= self.deltas[0] * (
                percentage(self.sprite_info["PLANE_SPEED"], self.motor_percentage)) * dt
            exp.position[1] -= self.deltas[1] * (
                percentage(self.sprite_info["PLANE_SPEED"], self.motor_percentage)) * dt
        C_X -= self.deltas[0] * (
            percentage(self.sprite_info["PLANE_SPEED"], self.motor_percentage)) * dt
        C_Y -= self.deltas[1] * (
            percentage(self.sprite_info["PLANE_SPEED"], self.motor_percentage)) * dt

        self.update_hitboxes()
        self.render()
        self.lastooc = self.ooc


p = Player(GAME_SETTINGS["PlayerPlane"])
entities.append(p)


class Ray:
    def __init__(self, origin: Vector2, angle: float, plr: Player):
        self.origin = origin
        self.angle = angle
        self.plr = plr

    def search_for_player(self) -> tuple:
        for length in range(0, R_LEN, (self.plr.sprite_info["PLANE_SCALE"] * 25)):
            pos = (
                self.origin[0] + (math.cos(self.angle) * length),
                self.origin[1] + (math.sin(self.angle) * length)
            )
            if R_DRAW_CIRCLES:
                pygame.draw.circle(screen, (0, 0, 255), pos, R_HITBOX_SIZE)
            if circles_collide(Circle(pos, R_HITBOX_SIZE), p.hitbox):
                return True, length, self.angle
        return False, None, None

    def search_for_all(self) -> tuple:
        for ent in entities:
            for length in range(0, R_LEN, (ent.sprite_info["PLANE_SCALE"] * 25)):
                pos = (
                    self.origin[0] + (math.cos(self.angle) * length),
                    self.origin[1] + (math.sin(self.angle) * length)
                )
                # pygame.draw.circle(screen, (0, 0, 255), pos, R_HITBOX_SIZE)
                if circles_collide(Circle(pos, R_HITBOX_SIZE), ent.hitbox):
                    return True, ent.uuid
            return False, None


class Enemy:
    def __init__(self, pos, sprite_info):
        self.position = Vector2(pos)
        self.alive = True
        self.target = None
        self.uuid = make_uuid()
        self.motor_percentage = 70

        self.angle = math.pi * 1.5
        self.DESIRED_ANGLE = None
        self.deltas = [math.cos(self.angle), math.sin(self.angle)]
        self.angle_to_player = None

        self.target_angle = None
        self.STATE = EnemyState.WONDERING
        self.guns = {}
        self.hitbox = Circle(self.position, 0)
        self.sprite_info = {"PLANE_TIMER": time.time()}
        self.load_sprite_info(sprite_info)
        self.sprite = pygame.image.load(DATA_DIR + self.sprite_info["SPRITE_LOCATION"]).convert()
        self.spritesheet = SpriteSheet(self.sprite)
        self.MAX_HP = self.sprite_info["HP"]
        self.last_from_seen = False
        self.going = None

    def fire(self) -> None:
        topleft = [
            self.position[0] + math.cos(self.angle - 0.78) * (
                    (self.sprite_info["DIMENSIONS"][0] * self.sprite_info["PLANE_SCALE"]) / 1.41),
            self.position[1] + math.sin(self.angle - 0.78) * (
                    (self.sprite_info["DIMENSIONS"][1] * self.sprite_info["PLANE_SCALE"]) / 1.41)
        ]
        for ammotype in self.guns:
            if self.guns[ammotype]["LAST_SHOT"] + self.guns[ammotype]["TIMEOUT"] <= time.time():
                if self.guns[ammotype]["RESERVE"] <= 0:
                    continue
                self.guns[ammotype]["LAST_SHOT"] = time.time()
                for GUNPOS in self.guns[ammotype]["POSITION"]:
                    righty = [
                        topleft[0] + math.cos(self.angle - math.pi) * (GUNPOS[1] * self.sprite_info["PLANE_SCALE"]),
                        topleft[1] + math.sin(self.angle - math.pi) * (GUNPOS[1] * self.sprite_info["PLANE_SCALE"])]
                    backer = [
                        topleft[0] + math.cos(self.angle - math.pi) * (
                                (GUNPOS[1] - 1) * self.sprite_info["PLANE_SCALE"]),
                        topleft[1] + math.sin(self.angle - math.pi) * (
                                (GUNPOS[1] - 1) * self.sprite_info["PLANE_SCALE"])]
                    from_ = [
                        backer[0] + math.cos(self.angle + (math.pi / 2)) * (
                                (GUNPOS[0]) * self.sprite_info["PLANE_SCALE"]),
                        backer[1] + math.sin(self.angle + (math.pi / 2)) * (GUNPOS[0] * self.sprite_info["PLANE_SCALE"])
                    ]
                    to_ = [
                        righty[0] + math.cos(self.angle + (math.pi / 2)) * (
                                GUNPOS[0] * self.sprite_info["PLANE_SCALE"]),
                        righty[1] + math.sin(self.angle + (math.pi / 2)) * (GUNPOS[0] * self.sprite_info["PLANE_SCALE"])
                    ]
                    self.guns[ammotype]["RESERVE"] -= 1
                    SHOOT.Position = to_
                    ae.play(SHOOT)
                    bullets.append(Bullet(calculate_angle(to_, from_), to_[0], to_[1], ammotype, self.uuid))

    def get_hit(self, damage) -> None:
        self.sprite_info["HP"] -= damage
        ae.play(HIT)
        if self.sprite_info["HP"] <= 0:
            self.alive = False

    def update_hitboxes(self) -> None:
        self.hitbox = Circle(Vector2(self.position), 25 * self.sprite_info["PLANE_SCALE"])

    def load_sprite_info(self, spi) -> None:
        if ".json" not in spi:
            spi += ".json"
        with open(DATA_DIR + "\\" + "SpriteInfo" + "\\" + spi) as file:
            info = json.loads(file.read())
        for key in NEEDED_KEYS["KEYS"]:
            if key not in info.keys():
                raise KeyError("Class Player -> Function load_sprite_info ->", spi,
                               "dosent have all needed keys please check data/NeededKeys.json and insure", spi,
                               "has all keys")
        self.sprite_info = info
        self.guns = info["GUNS"]
        self.update_hitboxes()

    def draw_vision_cone(self) -> None:
        if R_VIEWRANGE:
            pygame.draw.line(screen, (255, 0, 0), self.position, (
                self.position.x + math.cos(self.angle + (R_RANGE[0] / 100)) * R_LEN,
                self.position.y + math.sin(self.angle + (R_RANGE[0] / 100)) * R_LEN
            ))
            pygame.draw.line(screen, (255, 0, 0), self.position, (
                self.position.x + math.cos(self.angle + (R_RANGE[1] / 100)) * R_LEN,
                self.position.y + math.sin(self.angle + (R_RANGE[1] / 100)) * R_LEN
            ))
            pygame.draw.line(screen, (255, 0, 0), (
                self.position.x + math.cos(self.angle + (R_RANGE[0] / 100)) * R_LEN,
                self.position.y + math.sin(self.angle + (R_RANGE[0] / 100)) * R_LEN
            ),
                             (
                                 self.position.x + math.cos(self.angle + (R_RANGE[1] / 100)) * R_LEN,
                                 self.position.y + math.sin(self.angle + (R_RANGE[1] / 100)) * R_LEN
                             )
                             )

    def update(self, dt) -> None:
        ooc = False
        self.update_hitboxes()
        self.deltas[0] = math.cos(self.angle)
        self.deltas[1] = math.sin(self.angle)

        # negate the camera movement
        self.position[0] += self.deltas[0] * (percentage(self.sprite_info["PLANE_SPEED"], self.motor_percentage)) * dt
        self.position[1] += self.deltas[1] * (percentage(self.sprite_info["PLANE_SPEED"], self.motor_percentage)) * dt

        if not MAP_RECTANGLE.collidepoint(self.position):
            self.angle -= ANGLE_ADDER * dt
            ooc = True
        for x in range(1):
            if not ooc and self.DESIRED_ANGLE is not None:
                if self.angle > self.DESIRED_ANGLE:
                    if self.going is not None and self.going == True:
                        self.DESIRED_ANGLE = None
                        self.going = None
                        break
                    self.angle -= ANGLE_ADDER * dt
                    self.going = False
                if self.angle < self.DESIRED_ANGLE:
                    if self.going is not None and self.going == False:
                        self.DESIRED_ANGLE = None
                        self.going = None
                        break
                    self.angle += ANGLE_ADDER * dt
                    self.going = True

        # actually moving
        self.position[0] += self.deltas[0] * (percentage(self.sprite_info["PLANE_SPEED"], self.motor_percentage)) * dt
        self.position[1] += self.deltas[1] * (percentage(self.sprite_info["PLANE_SPEED"], self.motor_percentage)) * dt

        """
        Get Player and set it into player variable
        """
        player = None
        for entity in entities:
            if entity.uuid != USER_UUID:
                continue
            else:
                player = entity
        if player is None or not player.alive:
            return

        """
        Look for Player
        """
        rays: [Ray] = []
        # if distance(self.position[0], player.position[0], self.position[1], player.position[1]) > R_LEN + (R_LEN / 4):
        #     return
        for i in range(int(R_RANGE[0]), int(R_RANGE[1]), R_DEPTH):
            rays.append(Ray(self.position, self.angle + (i / 100), player))
        if R_VIEWRANGE:
            self.draw_vision_cone()
        saw_player = False
        for ray in rays:
            output = ray.search_for_player()
            if output[0]:
                saw_player = True

        if self.STATE == EnemyState.PURSUING and not saw_player:
            self.STATE = EnemyState.WONDERING
            return

        if self.STATE == EnemyState.WONDERING and saw_player:
            self.STATE = EnemyState.PURSUING
        if saw_player and not ooc:
            self.DESIRED_ANGLE = calculate_angle(self.position, player.position)
        ray = Ray(self.position, self.angle, None)
        foundsmth, _id = ray.search_for_all()
        if foundsmth and _id == USER_UUID:
            self.fire()

    def render(self) -> None:
        if self.sprite_info["PLANE_TIMER"] + self.sprite_info["PLANE_TIMEOUT"] <= time.time():
            self.sprite_info["PLANE_TIMER"] = time.time()
            self.sprite_info["PLANE_FRAME"] += 1
            if self.sprite_info["PLANE_FRAME"] >= self.sprite_info["FRAMES"]:
                self.sprite_info["PLANE_FRAME"] = 1
        IMG = self.spritesheet.get_image(self.sprite_info["PLANE_FRAME"], self.sprite_info["DIMENSIONS"][0],
                                         self.sprite_info["DIMENSIONS"][1], self.sprite_info["PLANE_SCALE"])
        image_copy = pygame.transform.rotate(IMG, -math.degrees(self.angle + 1.57079633))
        image_copy.set_colorkey(self.sprite_info["PLANE_BACKGROUD"])
        screen.blit(image_copy, (
            self.position[0] - int(image_copy.get_width() / 2), self.position[1] - int(image_copy.get_height() / 2)))

        # ent = myfont.render(f"HP: {self.sprite_info['HP']}", True, (255, 255, 255))
        # screen.blit(ent, (self.position.x - ent.get_width() / 2, self.position.y + 64))

        hp_perc = get_percentage(self.MAX_HP, self.sprite_info["HP"])

        topleft = [
            self.position[0] - (self.sprite_info["DIMENSIONS"][0] * self.sprite_info["PLANE_SCALE"]) / 1.5,
            self.position[1] - percentage((self.sprite_info["DIMENSIONS"][0] * self.sprite_info["PLANE_SCALE"]) / 2,
                                          hp_perc)
        ]
        botleft = [
            self.position[0] - (self.sprite_info["DIMENSIONS"][0] * self.sprite_info["PLANE_SCALE"]) / 1.5,
            self.position[1] + percentage((self.sprite_info["DIMENSIONS"][0] * self.sprite_info["PLANE_SCALE"]) / 2,
                                          hp_perc)
        ]
        pygame.draw.line(screen, (255, 0, 0), botleft, topleft, 5)

        if DRAW_TRACERS:
            pygame.draw.line(screen, (0, 0, 255), self.position, p.position, 6)
        # self.hitbox.draw()


for i in range(GAME_SETTINGS["ENEMIES"]):
    entities.append(
        Enemy(Vector2(random.randint(-4000, 4000), random.randint(-4000, 4000)), GAME_SETTINGS["EnemyPlane"]))


def init() -> None:
    """
    innits all the important stuff
    :return: None
    """
    x = gb_controls()
    if x == "EX":
        pass
    else:
        log(LogTypes.INFO, "Created controls.json file")
    load_controls()
    log(LogTypes.INFO, "Controls loaded")
    log(LogTypes.SUCCESS, "Initialized all needed function!")
    loop()


def event_listener() -> None:
    global running
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False


def controls(dt) -> None:
    """
    :param dt: float deltatime
    :return: None
    """
    for funcs in controls_js["keyboard"]:
        if pygame.key.get_pressed()[controls_js["keyboard"][funcs]["kc"]] == 1:
            do_controlaction(funcs, 1, dt)
    for funcs in controls_js["mouse"]:
        if pygame.mouse.get_pressed(buttons)[controls_js["mouse"][funcs]["but"] - 1]:
            do_controlaction(funcs, 0, dt)


def do_controlaction(function, device, dt) -> None:
    """
    :param function: str function name
    :param device: bool, T = Keyboard, F = Mouse
    :param dt: float deltaTime
    :return:
    """
    if device:
        if function == "motor_up":
            p.motor(1, dt)
        if function == "left":
            p.move(1, dt)
        if function == "motor_down":
            p.motor(0, dt)
        if function == "right":
            p.move(3, dt)
        if function == "fire":
            p.fire()


def is_down(kc) -> bool:
    """
    return if the key with certain keycode is pressed
    :param kc: int Key code
    :return bool
    """
    return pygame.key.get_pressed()[kc]


def get_function_key(function) -> None or int:
    """
    :param function: str Name of the function
    :return: kc: int Key code
    """
    for perif in controls_js:
        for c_func in controls_js[perif]:
            if c_func == function:
                if perif == "mouse":
                    return controls_js[perif][c_func]["but"]
                if perif == "keyboard":
                    return controls_js[perif][c_func]["kc"]
    return None


def load_controls() -> None:
    global controls_js
    with open("controls.json") as file:
        controls_js = json.loads(file.read())
        file.close()


def gb_controls() -> None or str:
    """
    generates base controls.json file that can be edited afterwards
    :return:
    """
    if os.path.exists("controls.json"):
        return "EX"
    with open("controls.json", "w") as file:
        base = {
            "keyboard": {
                "left": {"kc": pygame.K_a},
                "right": {"kc": pygame.K_d},
                "motor_up": {"kc": pygame.K_w},
                "motor_down": {"kc": pygame.K_s},
                "fire": {"kc": pygame.K_e},
            },
            "mouse": {
            }

        }
        json.dump(base, file)


def drawfps(fps) -> None:
    fpsmeter = myfont.render(f"{int(fps)} FPS", True, (255, 255, 255))
    screen.blit(fpsmeter, (0, 120))


trp = pygame.image.load(DATA_DIR + "\\Maps\\BG.png").convert()

trp = pygame.transform.scale(trp, (2000 * 4, 2000 * 4))


class Explosion:
    def __init__(self, sprt, pos):
        self.sprite_info = {}
        self.position = pos
        self.load_sprite_info(sprt)
        self.active = True
        self.sprite = pygame.image.load(DATA_DIR + self.sprite_info["SPRITE_LOCATION"]).convert()
        self.spritesheet = SpriteSheet(self.sprite)

    def load_sprite_info(self, spi) -> None:
        if ".json" not in spi:
            spi += ".json"
        with open(DATA_DIR + "\\" + "SpriteInfo" + "\\" + spi) as file:
            info = json.loads(file.read())
        self.sprite_info = info

    def render(self):
        if self.sprite_info["PLANE_TIMER"] + self.sprite_info["PLANE_TIMEOUT"] <= time.time():
            self.sprite_info["PLANE_TIMER"] = time.time()
            self.sprite_info["PLANE_FRAME"] += 1
            if self.sprite_info["PLANE_FRAME"] >= self.sprite_info["FRAMES"]:
                self.active = False
        IMG = self.spritesheet.get_image(self.sprite_info["PLANE_FRAME"], self.sprite_info["DIMENSIONS"][0],
                                         self.sprite_info["DIMENSIONS"][1], self.sprite_info["PLANE_SCALE"])
        IMG.set_colorkey((0, 0, 0))

        screen.blit(IMG, (self.position[0] - int(IMG.get_width() / 2), self.position[1] - int(IMG.get_height() / 2)))


explosions = []


def update(dt) -> None:
    global running
    minimap = pygame.Surface((100, 100))
    minimap_bg = pygame.Surface((110, 110))
    controls(dt)
    minimap.blit(trp, (0, 0))

    for index, bullet in enumerate(bullets):
        if time.time() - bullet.BORNED >= BULLET_LIFETIME:
            bullets.pop(index)
            continue
        bullet.update(dt)
        bullet.render()

    for pos, i in enumerate(entities):
        ent_pos = [
            get_percentage(8000, (i.position[0] - C_X) + 4000),
            get_percentage(8000, (i.position[1] - C_Y) + 4000)
        ]
        pygame.draw.circle(minimap, (255, 0, 0) if i.uuid != USER_UUID else (0, 255, 0), ent_pos, 3)
        i.update(dt)
        i.render()
        if not i.alive:
            explosions.append(Explosion(GAME_SETTINGS["ExplosionSprite"], i.position))
            EXPLOSION.Position = i.position
            ae.play(EXPLOSION)
            entities.pop(pos)

    for pos, exp in enumerate(explosions):
        if not exp.active:
            explosions.pop(pos)
        exp.render()

    if not p.alive:
        running = False
    screen.blit(minimap_bg, (0, 0))
    screen.blit(minimap, (5, 5))
    p.update(dt)


getTicksLastFrame = 0


def render_game():
    global getTicksLastFrame, MAP_RECTANGLE
    screen.fill((50, 50, 50))
    screen.blit(trp, (-4000 + C_X, -4000 + C_Y))
    MAP_RECTANGLE = pygame.Rect((-4000 + C_X, -4000 + C_Y), (2000 * 4, 2000 * 4))
    t = pygame.time.get_ticks()
    dt = (t - getTicksLastFrame) / 1000.0
    getTicksLastFrame = t
    event_listener()
    update(dt)
    ae.set_listener_position(p.position)
    clock.tick(FPS_LIMIT)
    pygame.display.update()


def loop() -> None:
    global running, MAP_RECTANGLE, getTicksLastFrame
    while running:
        render_game()
    pygame.quit()


init()
