import logging
import json

import uvicorn
from fastapi import FastAPI, WebSocket, Request, Depends, BackgroundTasks

from starlette.websockets import WebSocketDisconnect
from starlette.middleware.cors import CORSMiddleware

from notifier import Notifier

origins = [
    "*",
    "https://losowanko-na-dejli.netlify.app/"
]


app = FastAPI(debug=True)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

notifier = Notifier()


# @app.get("/roll/{room_name}")
# async def get(request: Request, room_name):
#     return await notifier.connections[room_name].roll()
#
#
# @app.get("/get_room/{room_name}")
# async def get(request: Request, room_name):
#     return notifier.get_room(room_name)

@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.websocket("/ws/{room_name}")
async def websocket_endpoint(
    websocket: WebSocket, room_name, background_tasks: BackgroundTasks
):
    await notifier.connect(websocket, room_name)
    try:
        while True:
            data = await websocket.receive_text()
            print(data)
            d = json.loads(data)
            d["room_name"] = room_name

            room_members = (
                notifier.get_members(room_name)
                if notifier.get_members(room_name) is not None
                else []
            )
            websockets = [participant for participant in room_members]
            if websocket not in websockets:
                print("SENDER NOT IN ROOM MEMBERS: RECONNECTING")
                await notifier.connect(websocket, room_name)

            await notifier._notify(websocket, f"{data}", room_name)
    except WebSocketDisconnect:
        notifier.remove(websocket, room_name)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
