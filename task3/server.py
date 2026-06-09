
import socket
import threading
import random
import time
import concurrent.futures

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
SERVER_HOST = s.getsockname()[0]
s.close() 

TCP_PORT = 6000
UDP_PORT = 6001
MIN_PLAYERS = 2
MAX_PLAYERS = 4
players = {} 
UDP_addresses = {}  
secret_number = None
game_started = False

to_enter_your_guess = 10 
game_duration = 60 
game_over = threading.Event()
countdown_started = False

#TCP CONNECTION
TCPSocket = socket.socket(socket.AF_INET ,socket.SOCK_STREAM) 
TCPSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
TCPSocket.bind((SERVER_HOST ,TCP_PORT))
TCPSocket.listen(5)

#UDP CONNECTION
UDPSocket = socket.socket(socket.AF_INET ,socket.SOCK_DGRAM)
UDPSocket.bind((SERVER_HOST ,UDP_PORT))

players_lock = threading.Lock()
udp_lock = threading.Lock()


instructions = """
Welcome to the Number Guessing Game!

Instructions:
- A random number between 1 and 100 has been selected.
- You have 60 seconds to guess the number.
- If your guess is out of range, you lose that turn.
- You will receive feedback after each guess:
    - 'Higher': the number is greater.
    - 'Lower': the number is smaller.
    - 'Correct': you guessed it!
- First to guess correctly wins the round!
- We will wait for 30 seconds for more players to join.
- If no other players join, the game will start with the current players.
Get ready!
"""

def broadcast_tcp(message):
        for player in players.values():
            try:
                player.sendall(message.encode())
            except:
                pass

def broadcast_udp(message):
    print(f"[DEBUG] Broadcasting message: {message}")
    for addr in UDP_addresses.values():
        print(f"[DEBUG] Sending to address: {addr}")
        UDPSocket.sendto(message.encode(), addr)
    print("[DEBUG] Finished broadcasting UDP message.")

def handle_register_tcp_client(client_socket, addr):
    global players, players_lock
    try:
        print(f"[DEBUG] Waiting for client from {addr} to send JOIN message.")
        while True:
            data_client = client_socket.recv(1024).decode().strip()
            print(f"[DEBUG] Received data from {addr}: {data_client}")
            
            if not data_client.startswith("JOIN "):
                client_socket.sendall("Invalid format. Use JOIN <name>\n".encode())
                continue

            name = data_client[5:].strip()
            print(f"[DEBUG] Player name received: {name}")

            with players_lock:
                if name in players:
                    print(f"[DEBUG] Player name '{name}' is already taken.")
                    client_socket.sendall("This name is already taken. Please use another name.\n".encode())
                    continue
                else:
                    players[name] = client_socket
                    print(f"[DEBUG] Player '{name}' joined from {addr}")
                    message = f"Player registered successfully!\n{instructions}\n<END>"
                    client_socket.sendall(message.encode())
                    break
    except Exception as e:
        print(f"[ERROR] Error while handling TCP registration: {e}")

def generate_secret_number():
    return random.randint(1, 100)

def start_game():
    global game_started, secret_number, countdown_started, players

    if len(players) < MIN_PLAYERS:
        message = "Not enough players to start the game. Game canceled."
        broadcast_tcp(message)
        print("[DEBUG] Not enough players to start the game.")
        return

    print(f"[DEBUG] Minimum players reached. Waiting for 30 seconds to allow more players...")
    countdown_started = True
    broadcast_tcp("Minimum players reached. Waiting 30 seconds for others to join...")

    time.sleep(30)  

    if len(players) < MIN_PLAYERS:
        broadcast_tcp("Not enough players after wait. Game canceled.")
        print("[DEBUG] Still not enough players after 30 seconds.")
        return

    secret_number = generate_secret_number()
    game_started = True
    print("[DEBUG] Game has started.")

def listen_udp_addr():
    while True:
        data, addr = UDPSocket.recvfrom(1024)
        message = data.decode().strip()
        print(f"[DEBUG] Received UDP message from {addr}: {message}")
        if message.startswith("HELLO_UDP "):
            name = message.split()[1]
            with udp_lock:
                UDP_addresses[name] = addr
            print(f"[DEBUG] Player {name} is reachable at {addr} for UDP")

def handle_player_guess(player_name, start_time, timeout):
    global game_started, players, UDP_addresses, secret_number
    addr = UDP_addresses[player_name]
    while (time.time() - start_time < timeout):
        try:
            print(f"[DEBUG] Waiting for player {player_name}'s guess.")
            data, sender_addr = UDPSocket.recvfrom(1024)
            decoded_guess = data.decode().strip()

            if ":" in decoded_guess:
                try:
                    player_name_received, guess = decoded_guess.split(":")
                    player_name_received = player_name_received.strip()
                    guess = int(guess.strip())

                    if player_name_received != player_name :
                        print(f"[DEBUG] Warning: The guess is not from the expected player {player_name} the recieve is{player_name_received} and guess {guess}.")
                        continue
                    else:
                        print(f"[DEBUG] Player {player_name} guessed: {guess}")

                except ValueError:
                    print(f"[DEBUG] Invalid guess format from {player_name}.")
                    continue

                if guess < secret_number:
                    print(f"[DEBUG] Guess from {player_name} is too low.")
                    UDPSocket.sendto("Higher".encode(), addr)
                elif guess > secret_number:
                    print(f"[DEBUG] Guess from {player_name} is too high.")
                    UDPSocket.sendto("Lower".encode(), addr)
                else:
                    print(f"[DEBUG] Player {player_name} guessed correctly!")
                    UDPSocket.sendto("Correct! You win.".encode(), addr)

                    broadcast_tcp(f"Player {player_name} won the round! The number was {secret_number}.")
                    for addr in UDP_addresses.values():
                        UDPSocket.sendto("Game Over".encode(), addr)

                    game_started = False
                    with players_lock:
                        for player_socket in players.values():
                            try:
                                player_socket.sendall("Game Over\n".encode())
                                player_socket.close()
                            except Exception as e:
                                print(f"[ERROR] Error closing connection for player: {e}")

                        players.clear()
                    with udp_lock:
                        UDP_addresses.clear()
                    break

        except Exception as e:
            print(f"[ERROR] Error handling guess from {player_name}: {e}")
            leave_msg = f"Player {player_name} has left the game due to an error or disconnection."
            with udp_lock:
                for other_name, other_addr in UDP_addresses.items():
                    if other_name != player_name:
                        UDPSocket.sendto(leave_msg.encode(), other_addr)
                if player_name in UDP_addresses:
                    del UDP_addresses[player_name]
            with players_lock:
                if player_name in players:
                    try:
                        players[player_name].close()
                    except Exception as e:
                        print(f"[ERROR] Failed to close socket: {e}")
                    del players[player_name]
            break

def run_game():
    global secret_number, game_started
    print("[DEBUG] Game starting...")
    secret_number = generate_secret_number()
    print(f"[DEBUG] Secret number generated: {secret_number}")

    game_started = True
    broadcast_udp("Game started! Start guessing the number between 1 and 100 now!")
    start_time = time.time()
    timeout = 60

    with concurrent.futures.ThreadPoolExecutor() as executor:
        with udp_lock:
            for player_name in UDP_addresses:
                executor.submit(handle_player_guess, player_name, start_time, timeout)
    game_over.set()
    broadcast_tcp("Game over! Time's up. No more guesses.")

def ask_for_another_round():
    global game_started, countdown_started, players, UDP_addresses
    votes = {}
    broadcast_tcp("\nDo you want to play another round? (yes/no)")
    with players_lock:
        for name, sock in players.items():
            try:
                sock.settimeout(15)
                response = sock.recv(1024).decode().strip().lower()
                print(f"[DEBUG] Player {name} response: {response}")
                votes[name] = (response == "yes")
            except socket.timeout:
                print(f"[DEBUG] Player {name} did not respond in time.")
                votes[name] = False

        yes_votes = sum(votes.values())
        if yes_votes >= 2:
            print("[DEBUG] Starting a new round.")
            broadcast_tcp("\nStarting a new round!")
            broadcast_tcp("\nNew players can join now. You have 20 seconds to join before the next round starts.")

            game_started = False
            countdown_started = False
            game_over.clear()

            with concurrent.futures.ThreadPoolExecutor() as executor:
                print("[DEBUG] Waiting for new players to join...")
                executor.submit(accept_TCP_clients)
                executor.submit(listen_udp_addr)

            wait_and_start_game()
        else:
            print("[DEBUG] Ending the game.")
            broadcast_tcp("\nGame ended. Thank you for playing!")
            with players_lock:
                for player_socket in players.values():
                    player_socket.close()
                players.clear()
            with udp_lock:
                for addr in UDP_addresses.values():
                    UDPSocket.sendto("Game End".encode(), addr)
                UDP_addresses.clear()

def accept_TCP_clients():
    global TCPSocket
    with concurrent.futures.ThreadPoolExecutor() as executor:
        while True:
            try:
                client_socket, addr = TCPSocket.accept()
                print(f"[DEBUG] Accepted connection from {addr}")
                executor.submit(handle_register_tcp_client, client_socket, addr)
            except Exception as e:
                print(f"[ERROR] Error accepting client connection: {e}")

def wait_and_start_game():
    global countdown_started, players, game_started
    print("[DEBUG] Waiting for minimum number of players to join...")
    while len(players) < MIN_PLAYERS:
        time.sleep(1)

    print("[DEBUG] Minimum number of players reached. Starting countdown...")
    time.sleep(15)
    countdown_started = True
    start_game()
    print(f"GAME STARTED***** {game_started}")
    if game_started:
        run_game()
        ask_for_another_round()

def main():
    global TCPSocket, UDPSocket, game_started
    print(f"[INFO] Server is running on {SERVER_HOST}:{TCP_PORT} ...") 
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.submit(accept_TCP_clients)
            executor.submit(listen_udp_addr)
            print("[DEBUG] Waiting for players to join...")
            while True:
                wait_and_start_game()
    except Exception as e:
        print(f"[ERROR] Error in main game loop: {e}")
    finally:
        TCPSocket.close()
        UDPSocket.close()


if __name__ == "__main__":
    main()




