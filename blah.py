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
        self.selected_square = None
        
        pygame.mixer.init()
        self.music_on = True
        self.move_history = []
        self.start_time = None
        self.flip_board = False
        self.difficulty = "Medium"
        self.game_timer = {"White": 600, "Black": 600}  # 10-minute timer per player
        self.current_turn = "White"
        self.timer_running = False
        self.connection = None
        self.is_host = False
        self.chat_history = []
        self.spectators = []
        self.achievements = set()
        self.leaderboard = {}
        
        self.load_music()
        self.load_ai_engine()
        self.show_main_menu()
    
    def load_music(self):
        try:
            pygame.mixer.music.load("music/chess.mp3")
            pygame.mixer.music.play(-1)
        except pygame.error:
            print("chess.mp3 file not found.")
    
    def toggle_music(self):
        if self.music_on:
            pygame.mixer.music.stop()
        else:
            pygame.mixer.music.play(-1)
        self.music_on = not self.music_on
    
    def load_ai_engine(self):
        try:
            self.engine = chess.engine.SimpleEngine.popen_uci("stockfish")
        except Exception:
            self.engine = None
            print("Stockfish engine not found.")
    
    def change_theme(self):
        colors = [("#DDB88C", "#A67B5B"), ("#769656", "#EEEED2"), ("#B58863", "#F0D9B5")]
        choice = random.choice(colors)
        self.canvas.configure(bg=choice[0])
        self.draw_board()
    
    def create_game_window(self):
        self.game_window = tk.Toplevel(self.root)
        self.game_window.title("Chess Board - Multiplayer")
        self.game_window.geometry("1000x900")
        self.start_time = time.time()
        self.timer_running = True
        self.create_widgets()
    
    def create_widgets(self):
        self.canvas = tk.Canvas(self.game_window, width=480, height=480, bg="#DDB88C")
        self.canvas.pack()
        self.draw_board()
        self.canvas.bind("<Button-1>", self.on_click)
        
        self.timer_label = tk.Label(self.game_window, text="White: 10:00 | Black: 10:00")
        self.timer_label.pack()
        self.update_timer()
        
        frame = tk.Frame(self.game_window)
        frame.pack(side=tk.BOTTOM, pady=10)
        
        self.hint_button = tk.Button(frame, text="Best Move", command=self.show_best_move)
        self.hint_button.pack(side=tk.LEFT, padx=5)
        
        self.undo_button = tk.Button(frame, text="Undo", command=self.undo_move)
        self.undo_button.pack(side=tk.LEFT, padx=5)
        
        self.theme_button = tk.Button(frame, text="Change Theme", command=self.change_theme)
        self.theme_button.pack(side=tk.LEFT, padx=5)
        
        self.chat_button = tk.Button(frame, text="Chat", command=self.open_chat)
        self.chat_button.pack(side=tk.LEFT, padx=5)
        
        self.sound_toggle_button = tk.Button(frame, text="Toggle Sound", command=self.toggle_sound)
        self.sound_toggle_button.pack(side=tk.LEFT, padx=5)
        
        self.spectate_button = tk.Button(frame, text="Spectate", command=self.enable_spectator_mode)
        self.spectate_button.pack(side=tk.LEFT, padx=5)
        
        self.move_list = tk.Text(self.game_window, height=10, width=40, state=tk.DISABLED)
        self.move_list.pack()
        
        self.exit_button = tk.Button(frame, text="Exit", command=self.exit_game)
        self.exit_button.pack(side=tk.LEFT, padx=5)
    
    def update_timer(self):
        if self.timer_running:
            elapsed_time = time.time() - self.start_time
            white_time = self.game_timer["White"] - elapsed_time if self.current_turn == "White" else self.game_timer["White"]
            black_time = self.game_timer["Black"] - elapsed_time if self.current_turn == "Black" else self.game_timer["Black"]
            self.timer_label.config(text=f"White: {int(white_time // 60)}:{int(white_time % 60):02d} | Black: {int(black_time // 60)}:{int(black_time % 60):02d}")
            self.root.after(1000, self.update_timer)
    
    def enable_spectator_mode(self):
        self.spectators.append("Spectator")
        messagebox.showinfo("Spectator Mode", "You are now spectating the game.")
    
    def update_leaderboard(self, winner):
        self.leaderboard[winner] = self.leaderboard.get(winner, 0) + 1
        messagebox.showinfo("Leaderboard", f"{winner} now has {self.leaderboard[winner]} wins!")
    
    def ai_move(self):
        if self.engine and not self.board.is_game_over() and self.board.turn == chess.BLACK:
            result = self.engine.play(self.board, chess.engine.Limit(time=1.0))
            self.board.push(result.move)
            self.move_history.append(str(result.move))
            self.update_move_list()
            self.draw_board()
            self.check_winner()
    
    def reconnect_multiplayer(self):
        if self.connection:
            try:
                self.connection.close()
            except:
                pass
        self.setup_multiplayer(self.is_host)
    
    def update_move_list(self):
        self.move_list.config(state=tk.NORMAL)
        self.move_list.delete(1.0, tk.END)
        for move in self.move_history:
            self.move_list.insert(tk.END, move + "\n")
        self.move_list.config(state=tk.DISABLED)
    
    def draw_board(self):
        self.canvas.delete("all")
        colors = ["#DDB88C", "#A67B5B"]
        for row in range(8):
            for col in range(8):
                color = colors[(row + col) % 2]
                x1 = col * 60
                y1 = row * 60
                x2 = x1 + 60
                y2 = y1 + 60
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color)
        self.draw_pieces()
    
    def draw_pieces(self):
        pieces = {
            'r': '♜', 'n': '♞', 'b': '♝', 'q': '♛', 'k': '♚', 'p': '♟',
            'R': '♖', 'N': '♘', 'B': '♗', 'Q': '♕', 'K': '♔', 'P': '♙'
        }
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece:
                x = (square % 8) * 60 + 30
                y = (7 - square // 8) * 60 + 30
                self.canvas.create_text(x, y, text=pieces[piece.symbol()], font=("Arial", 32))
    
    def on_click(self, event):
        col = event.x // 60
        row = 7 - event.y // 60
        square = chess.square(col, row)
        
        if self.selected_square is not None:
            move = chess.Move.from_uci(self.selected_square + chess.square_name(square))
            if self.board.is_legal(move):
                self.board.push(move)
                self.move_history.append(move.uci())  # Save move history
                self.selected_square = None
                self.draw_board()
                self.check_winner()
                if self.play_with_bot and not self.board.is_game_over():
                    self.ai_move()
                if self.play_online:
                    self.send_move(move)
            else:
                self.selected_square = chess.square_name(square)
        else:
            self.selected_square = chess.square_name(square)
    
    def undo_move(self):
        if len(self.board.move_stack) > 0:
            self.board.pop()
            self.draw_board()
    
    def show_best_move(self):
        if self.engine and not self.board.is_game_over():
            result = self.engine.play(self.board, chess.engine.Limit(time=1.0))
            best_move = result.move
            messagebox.showinfo("Best Move", f"The best move is: {best_move}")
    
    def open_chat(self):
        chat_popup = tk.Toplevel(self.game_window)
        chat_popup.title("Chat")
        chat_popup.geometry("300x400")
        chat_text = tk.Text(chat_popup, state=tk.DISABLED)
        chat_text.pack(expand=True, fill=tk.BOTH)
        chat_entry = tk.Entry(chat_popup)
        chat_entry.pack(fill=tk.X)
        chat_entry.bind("<Return>", lambda event: self.send_chat_message(chat_text, chat_entry))
    
    def send_chat_message(self, chat_text, chat_entry):
        message = chat_entry.get()
        if message:
            self.chat_history.append(message)
            chat_text.config(state=tk.NORMAL)
            chat_text.insert(tk.END, f"You: {message}\n")
            chat_text.config(state=tk.DISABLED)
            chat_entry.delete(0, tk.END)
            # Send message to opponent if playing online
            if self.play_online:
                self.connection.sendall(json.dumps({"chat": message}).encode())
    
    def receive_chat_message(self, message, chat_text):
        self.chat_history.append(message)
        chat_text.config(state=tk.NORMAL)
        chat_text.insert(tk.END, f"Opponent: {message}\n")
        chat_text.config(state=tk.DISABLED)
    
    def show_main_menu(self):
        self.root.geometry("300x200")
        tk.Button(self.root, text="Play with Bot", command=self.play_bot).pack(pady=10)
        tk.Button(self.root, text="Play 2 Players", command=self.play_two_players).pack(pady=10)
        tk.Button(self.root, text="Play Online", command=self.setup_multiplayer).pack(pady=10)
        tk.Button(self.root, text="Settings", command=self.show_settings).pack(pady=10)
    
    def play_bot(self):
        self.play_with_bot = True
        self.board.reset()
        self.move_history.clear()
        self.create_game_window()
        self.root.withdraw()
    
    def play_two_players(self):
        self.play_with_bot = False
        self.board.reset()
        self.move_history.clear()
        self.create_game_window()
        self.root.withdraw()
    
    def show_settings(self):
        settings_popup = tk.Toplevel(self.root)
        settings_popup.title("Settings")
        settings_popup.geometry("300x150")
        tk.Button(settings_popup, text="Music On", command=lambda: self.set_music(True)).pack(pady=5)
        tk.Button(settings_popup, text="Music Off", command=lambda: self.set_music(False)).pack(pady=5)
        tk.Button(settings_popup, text="Close", command=settings_popup.destroy).pack(pady=10)
    
    def set_music(self, state):
        self.music_on = state
        if self.music_on:
            pygame.mixer.music.play(-1)
        else:
            pygame.mixer.music.stop()
    
    def check_winner(self):
        if self.board.is_checkmate():
            winner = "White" if self.board.turn == chess.BLACK else "Black"
            self.show_winner(winner)
        elif self.board.is_stalemate() or self.board.is_insufficient_material() or self.board.is_seventyfive_moves() or self.board.is_fivefold_repetition():
            messagebox.showinfo("Game Over", "The game is a draw!")
    
    def show_winner(self, winner):
        img_path = f"images/{winner.lower()}.png"
        img = Image.open(img_path)
        img = img.resize((300, 300), Image.ANTIALIAS)
        img = ImageTk.PhotoImage(img)
        popup = tk.Toplevel(self.root)
        popup.title(f"{winner} Wins!")
        label = tk.Label(popup, image=img)
        label.image = img
        label.pack()
        tk.Button(popup, text="Close", command=popup.destroy).pack()
    
    def setup_multiplayer(self):
        self.play_online = True
        self.board.reset()
        self.move_history.clear()
        self.create_game_window()
        self.root.withdraw()
        self.is_host = messagebox.askyesno("Multiplayer", "Do you want to host the game?")
        if self.is_host:
            self.start_server()
        else:
            self.connect_to_server()
    
    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(("0.0.0.0", 65432))
        self.server_socket.listen(1)
        threading.Thread(target=self.accept_connection).start()
    
    def accept_connection(self):
        self.connection, _ = self.server_socket.accept()
        threading.Thread(target=self.receive_data).start()
    
    def connect_to_server(self):
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_ip = simpledialog.askstring("Server IP", "Enter the server IP address:")
        self.connection.connect((server_ip, 65432))
        threading.Thread(target=self.receive_data).start()
    
    def receive_data(self):
        while True:
            data = self.connection.recv(1024)
            if not data:
                break
            message = json.loads(data.decode())
            if "move" in message:
                move = chess.Move.from_uci(message["move"])
                self.board.push(move)
                self.move_history.append(move.uci())
                self.update_move_list()
                self.draw_board()
                self.check_winner()
            elif "chat" in message:
                self.receive_chat_message(message["chat"], self.chat_text)
    
    def send_move(self, move):
        if self.play_online:
            self.connection.sendall(json.dumps({"move": move.uci()}).encode())
    
    def exit_game(self):
        self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    game = ChessGame(root)
    root.mainloop()