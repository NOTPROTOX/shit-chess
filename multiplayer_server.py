import tkinter as tk
from tkinter import messagebox, simpledialog
from PIL import Image, ImageTk
import chess
import chess.engine
import pygame
import time
import random
import json
import socket
import threading

class ChessGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Ultimate Chess Game - Multiplayer Edition")
        self.root.geometry("1000x900")
        self.board = chess.Board()
        self.play_with_bot = False
        self.play_online = False
        self.start_time = None  # Track game duration
        self.setup_ui()
        self.client = None  # Multiplayer client
        self.server = None  # Multiplayer server
    
    def setup_ui(self):
        self.start_menu()
    
    def start_menu(self):
        self.menu_frame = tk.Frame(self.root)
        self.menu_frame.pack()
        
        tk.Label(self.menu_frame, text="Chess Game", font=("Arial", 24)).pack()
        tk.Button(self.menu_frame, text="Play vs Bot", command=self.start_bot_game).pack()
        tk.Button(self.menu_frame, text="Play Online", command=self.start_multiplayer_game).pack()
        tk.Button(self.menu_frame, text="Host Game", command=self.host_multiplayer_game).pack()
        tk.Button(self.menu_frame, text="Exit", command=self.root.quit).pack()
    
    def start_bot_game(self):
        self.play_with_bot = True
        self.menu_frame.destroy()
        self.start_game()
    
    def start_multiplayer_game(self):
        self.play_online = True
        self.menu_frame.destroy()
        self.connect_to_server()
    
    def host_multiplayer_game(self):
        self.play_online = True
        self.menu_frame.destroy()
        self.start_server()
    
    def start_server(self):
        self.server = MultiplayerServer()
        self.server.start()
        self.start_game()
    
    def connect_to_server(self):
        self.client = MultiplayerClient()
        self.client.connect()
        self.start_game()
    
    def start_game(self):
        self.start_time = time.time()  # Start timer
        self.game_frame = tk.Frame(self.root)
        self.game_frame.pack()
        
        self.timer_label = tk.Label(self.game_frame, text="Game Time: 0s")
        self.timer_label.pack()
        self.update_timer()
        
        tk.Button(self.game_frame, text="Undo Move", command=self.undo_move).pack()
        tk.Button(self.game_frame, text="Exit Game", command=self.exit_game).pack()
        tk.Button(self.game_frame, text="Hint", command=self.show_hint).pack()
    
    def update_timer(self):
        if self.start_time:
            elapsed_time = int(time.time() - self.start_time)
            self.timer_label.config(text=f"Game Time: {elapsed_time}s")
        self.root.after(1000, self.update_timer)
    
    def undo_move(self):
        if self.board.move_stack:
            self.board.pop()
            messagebox.showinfo("Undo", "Last move undone!")
    
    def exit_game(self):
        self.root.quit()
    
    def show_hint(self):
        messagebox.showinfo("Hint", "Try controlling the center of the board!")
    
    def check_winner(self):
        if self.board.is_checkmate():
            winner = "White" if self.board.turn == chess.BLACK else "Black"
            self.show_winner_popup(winner)
    
    def show_winner_popup(self, winner):
        img_path = "white.png" if winner == "White" else "black.png"
        popup = tk.Toplevel(self.root)
        popup.title("Game Over")
        img = Image.open(img_path)
        img = img.resize((200, 200))
        img = ImageTk.PhotoImage(img)
        tk.Label(popup, image=img).pack()
        tk.Label(popup, text=f"{winner} Wins!", font=("Arial", 16)).pack()
        tk.Button(popup, text="OK", command=popup.destroy).pack()
        popup.mainloop()

class MultiplayerServer:
    def __init__(self, host="0.0.0.0", port=65432):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen(2)
        self.clients = []
        self.board = chess.Board()
        self.lock = threading.Lock()
        print("Server started, waiting for connections...")

    def accept_connections(self):
        while len(self.clients) < 2:
            client_socket, addr = self.server_socket.accept()
            self.clients.append(client_socket)
            print(f"Client connected from {addr}")
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()

    def handle_client(self, client_socket):
        while True:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break
                message = json.loads(data.decode())
                if "move" in message:
                    with self.lock:
                        move = chess.Move.from_uci(message["move"])
                        if self.board.is_legal(move):
                            self.board.push(move)
                            self.broadcast_move(move.uci())
                elif "chat" in message:
                    self.broadcast_chat(message["chat"])
            except:
                break
        client_socket.close()

    def broadcast_move(self, move):
        for client in self.clients:
            client.sendall(json.dumps({"move": move}).encode())

    def broadcast_chat(self, chat):
        for client in self.clients:
            client.sendall(json.dumps({"chat": chat}).encode())

if __name__ == "__main__":
    server = MultiplayerServer()
    server.accept_connections()

class MultiplayerClient:
    def __init__(self, host="localhost", port=65432):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.port = port
    
    def connect(self):
        self.client_socket.connect((self.host, self.port))
        print("Connected to server")

if __name__ == "__main__":
    root = tk.Tk()
    game = ChessGame(root)
    root.mainloop()
