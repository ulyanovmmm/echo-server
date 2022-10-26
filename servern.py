#!/usr/bin/env python
# coding: utf-8

# In[1]:


import socket
from datetime import datetime
import hashlib
import json
import pickle
from threading import Thread
import sys
import logging

def port_validation(port, isfree=False):
    try:
        if 1 <= int(port) <= 65535:
            if isfree:
                return is_free_port(port)
            return True
        print(f"Некорректное значение для порта")
        return False

    except ValueError:
        return False


def is_free_port(port):
    try:
        sock = socket.socket()
        sock.bind(("", port))
        sock.close()
        return True
    except OSError:
        return False


PORT_DEFAULT = 9090
logging.basicConfig(format="%(asctime)s [%(levelname)s] %(funcName)s: %(message)s",
                    handlers=[logging.FileHandler("log/server.log"), logging.StreamHandler()], level=logging.INFO)


class Server():
    def __init__(self, port, clients=[], status=None):
        self.users = "users.json"
        self.clients = clients
        self.server_port = port
        self.all_Users = []
        self.status = status
        self.server_boot()

    def readJSON(self):
        with open(self.users, 'r') as f:
            users = json.load(f)
        return users

    def writeJSON(self):
        with open(self.users, 'w') as f:
            json.dump(self.all_Users, f, indent=4)

    def server_boot(self):
        sock = socket.socket()
        sock.bind(('', self.server_port))
        sock.listen(5)
        self.sock = sock
        logging.info(f"Сервер стартанул, слушаем порт {self.server_port}")
        while True:
            conn, addr = self.sock.accept()
            Thread(target=self.listenToClient, args=(conn, addr)).start()
            logging.info(f"Подключение клиента {addr}")
            self.clients.append(conn)
            

    def checkPassword(self, passwd, userkey):
        key = hashlib.md5(passwd.encode() + b'salt').hexdigest()
        return key == userkey

    def generateHash(self, passwd):
        key = hashlib.md5(passwd.encode() + b'salt').hexdigest()
        return key

    def listenToClient(self, conn, address):
        self.authorization(address, conn)
        while True:
            try:
                data = conn.recv(1024)
            except ConnectionResetError:
                conn.close()
                self.clients.remove(conn)
                logging.info(f"Отключение клиента {address}")
                break

            if data:
                status, data, username = pickle.loads(data)
                logging.info(f"Прием данных от клиента '{username}_{address[1]}': {data}")
                if status == "message":
                    self.broadcast(data, conn, address, username)
                    
            else:
                # Закрываем соединение
                conn.close()
                self.clients.remove(conn)
                logging.info(f"Отключение клиента {address}")
                break
    
    def broadcast(self, msg, conn, address, username):
        username += "_"+str(address[1])
        for sock in self.clients:
            if sock != conn:
                data = pickle.dumps(["message", msg, username])
                sock.send(data)
                logging.info(f"Отправка данных клиенту {sock.getsockname()}: {msg}")

                
    def registration(self, addr, conn):
        conn.send(pickle.dumps(
            ["auth", ""]))
        name = pickle.loads(conn.recv(1024))[1]
        conn.send(pickle.dumps(["passwd", "Введите свой пароль: "]))
        passwd = self.generateHash(pickle.loads(conn.recv(1024))[1])
        conn.send(pickle.dumps(["success", f"Приветствую, {name}"]))
        self.all_Users.append({addr[0]: {'name': name, 'password': passwd}})
        # Запись в файл при регистрации пользователя
        self.writeJSON()
        self.all_Users = self.readJSON()
        
    def authorization(self, addr, conn):
        # Проверка есть ли в файле данные
        try:
            self.all_Users = self.readJSON()
        except json.decoder.JSONDecodeError:
            self.registration(addr, conn)

        user_flag = False
        for user in self.all_Users:
            if addr[0] in user:
                for k, v in user.items():
                    if k == addr[0]:
                        name = v['name']
                        password = v['password']
                        conn.send(pickle.dumps(["passwd", "Введите свой пароль: "]))
                        passwd = pickle.loads(conn.recv(1024))[1]
                        conn.send(pickle.dumps(["success", f"Здравствуйте, {name}"])) if self.checkPassword(
                            passwd, password) else self.authorization(addr, conn)
                        user_flag = True
        # Если пользователь не найден в файле
        if not user_flag:
            self.registration(addr, conn)
    




def main():
    # Подбор порта
    server_port = PORT_DEFAULT
    if not port_validation(PORT_DEFAULT, True):
        if not is_free_port(PORT_DEFAULT):
            logging.info(f"Порт по умолчанию {PORT_DEFAULT} занят")
            free_port = False
            # перебор порта
            while not free_port:
                server_port += 1
                free_port = is_free_port(server_port)
    try:
        Server(server_port)
    except KeyboardInterrupt:
        logging.info(f"Остановка сервера")

if __name__ == "__main__":
    main()


# In[ ]:




