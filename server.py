#!/bin/python3
"""
Серверное приложение для соединений
"""
import asyncio
import time
from asyncio import transports
from collections import deque

class ClientProtocol(asyncio.Protocol):
    login: str
    server: 'Server'
    transport: transports.Transport

    def __init__(self, server: 'Server'):
        self.server = server
        self.login = None

    def data_received(self, data: bytes):
        decoded = data.decode()
        print(decoded, end="")

        if self.login is None and decoded.startswith("login:"):
            new_login = decoded.replace("login:", "").replace("\n", "")

            for exist_client in self.server.clients:
                if exist_client.login == new_login:
                    self.transport.write(f"Логин {new_login} занят, попробуйте другой\n".encode())
                    self.transport.close()
                    break
            else:
                self.login = new_login
                self.transport.write(f"Привет, {self.login}!\n".encode())
                self.server.send_history(self.transport)
        else:
            self.send_message(decoded)

    def send_message(self, message):
        format_string = f"\033[32m{self.login}:\033[0m {message}"
        self.server.append_to_history(format_string)

        encoded = format_string.encode()

        for client in self.server.clients:
            if client.login != self.login:
                client.transport.write(encoded)

    def connection_made(self, transport: transports.Transport):
        self.transport = transport
        self.server.clients.append(self)
        print("Соединение установлено")

    def connection_lost(self, exception):
        self.server.clients.remove(self)
        print("Соединение разорвано")


class Server:
    clients: list
    history_storage: deque

    def __init__(self):
        self.clients = []
        self.history_storage = deque()

    def send_history(self, transport: transports.Transport):
        msg_count = len(self.history_storage)

        if msg_count > 0:
            transport.write(f"\033[36mLast {msg_count} message(s):\033[0m\n".encode())
            for msg in self.history_storage:
                transport.write(f"{msg}\n".encode())

        transport.write("\033[36m↓↓↓↓↓ New messages ↓↓↓↓↓\033[0m\n".encode())

    def append_to_history(self, msg):
        if (len(self.history_storage) > 9):
            self.history_storage.popleft()

        msg = msg.replace("\n", "\033[33m↵\033[0m");
        msg = msg.replace("\r", "\033[33m↞\033[0m");
        msg = time.strftime("[%X] ") + msg
        self.history_storage.append(msg)

    def create_protocol(self):
        return ClientProtocol(self)

    async def start(self):
        loop = asyncio.get_running_loop()

        coroutine = await loop.create_server(
            self.create_protocol,
            "localhost",
            8888
        )

        print("Сервер запущен ...")

        await coroutine.serve_forever()


process = Server()
try:
    asyncio.run(process.start())
except KeyboardInterrupt:
    print("Сервер остановлен вручную")
