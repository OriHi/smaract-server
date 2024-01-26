import asyncio
import websockets
import socket

PORT = 5050
SERVER = socket.gethostbyname(socket.gethostname())

async def echo(websocket, path):
    try:
        async for message in websocket:
            print(f"Received message: {message}")
            # Echo the received message back to the client
            await websocket.send(f"Echoed: {message}")
    except websockets.ConnectionClosedError:
        print("Connection closed.")

async def main():
    server = await websockets.serve(echo, SERVER, PORT)
    print("Server started...")
    await server.wait_closed()
    


if __name__ == "__main__":
    asyncio.run(main())
 
    

    
