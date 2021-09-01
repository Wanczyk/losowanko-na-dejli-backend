import time
import json
import random

from starlette.websockets import WebSocket


class Room:
    def __init__(self):
        self.remaining: list = list()
        self.participants: list = list()
        self.last_roll_time: time = time.time()

    async def send_message(self, message):
        return_message = json.dumps(message)
        for participant in self.participants:
            await participant.send_text(return_message)

    async def add_person(self, name: str):
        self.remaining.append(name)
        await self.send_message(self.get_room())

    def pop_person(self, name: str):
        self.remaining.remove(name)

    def get_participants(self):
        return [participant.name for participant in self.participants]

    def get_room(self):
        body = {
            "remaining": self.remaining
        }
        return body

    async def roll(self):
        print(self.remaining)
        people = self.remaining.copy()
        if time.time() - self.last_roll_time < 10:
            return self.get_room()
        if len(self.remaining):
            picked_person_index = random.randrange(0, len(self.remaining))
            self.last_roll_time = time.time()
            self.pop_person(self.remaining[picked_person_index])
            body = {
                "remaining": people,
                "picked": picked_person_index
            }
        else:
            body = {
                "remaining": people,
                "picked": 0
            }
        await self.send_message(body)
        return body


class Notifier:
    """
        Manages chat room sessions and members along with message routing
    """

    def __init__(self):
        self.connections: dict = dict()
        self.generator = self.get_notification_generator()

    async def get_notification_generator(self):
        while True:
            message = yield
            msg = message["message"]
            room_name = message["room_name"]
            name = message["name"]
            await self._notify(msg, room_name, name)

    def get_members(self, room_name):
        try:
            return self.connections[room_name].participants
        except Exception:
            return None

    def get_room(self, room_name):
        try:
            self.connections[room_name]
        except Exception:
            self.connections[room_name] = Room()
        return self.connections[room_name].get_room()

    async def push(self, msg: str, room_name: str = None):
        message_body = {"message": msg, "room_name": room_name}
        await self.generator.asend(message_body)

    async def connect(self, websocket: WebSocket, room_name: str):
        await websocket.accept()
        try:
            self.connections[room_name]
        except Exception:
            self.connections[room_name] = Room()
        if self.connections[room_name].participants == {} or len(self.connections[room_name].participants) == 0:
            self.connections[room_name].participants = list()
            self.connections[room_name].remaining = list()
        self.connections[room_name].participants.append(websocket)
        await websocket.send_text(json.dumps(self.connections[room_name].get_room()))

    def remove(self, websocket: WebSocket, room_name: str):
        to_be_removed: websocket = None
        for participant in self.connections[room_name].participants:
            if participant == websocket:
                to_be_removed = websocket
        self.connections[room_name].participants.remove(to_be_removed)

    async def _notify(self, websocket, message: str, room_name: str):
        message = json.loads(message)
        if message["message"] == "spin":
            await self.connections[room_name].roll()
        elif message["message"] == "get_room":
            websocket.send_text(json.dumps(self.connections[room_name].get_room()))
        elif message["message"] == "join_room":
            await self.connections[room_name].add_person(name=message["name"])
            self.connections[room_name].get_room()
