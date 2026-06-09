import socket
import threading
import concurrent.futures

SERVER_HOST = "192.168.1.13"   #from ipconfig command
TCP_PORT = 6000
UDP_PORT = 6001
player_name = None
game_started = threading.Event()  # Flag to track game start
game_over = threading.Event()

TCPSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
TCPSocket.connect((SERVER_HOST, TCP_PORT))
print(f"[DEBUG] Connected to TCP server at {(SERVER_HOST, TCP_PORT)}")

UDPSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
UDPSocket.settimeout(1)
print(f"[DEBUG] UDP socket created with timeout 12s")

def register_player():
    global player_name
    while True:
        name = input("Enter your player name: ")
        join_msg = f"JOIN {name}"
        print(f"[DEBUG] Sending JOIN message: {join_msg}")
        TCPSocket.sendall(join_msg.encode())

        response = TCPSocket.recv(1024).decode()
        print(f"[DEBUG] Received TCP response: {response}")
        if "use another player name" in response:
            print("Player name already taken. Try a different name.")
            
        else:
            instructions = TCPSocket.recv(1024).decode()
            print(f"[DEBUG] Game instructions received:\n{instructions}")
            hello_msg = f"HELLO_UDP {name}"
            print(f"[DEBUG] Sending UDP hello message: {hello_msg}")
            UDPSocket.sendto(hello_msg.encode(), (SERVER_HOST, UDP_PORT))
            break

def listen_for_udp_messages():
    global UDPSocket
    print("[DEBUG] Listening for UDP messages...")
    while True:
        try:
            msg, _ = UDPSocket.recvfrom(1024)
            decoded_msg = msg.decode().strip()
            print(f"[DEBUG] UDP message received: {decoded_msg}")

            if "Game started!" in decoded_msg:
                print("[DEBUG] Detected game start signal.")
                game_started.set()  # Set the flag to mark game started
                break

            if "Correct" in decoded_msg or "Game Over" in decoded_msg:
                print(decoded_msg)
                print("[DEBUG] Game over message received. Closing sockets.")
                game_over.set()
                
                response = input("Do you want to play another round? (yes/no): ")
                UDPSocket.sendto(response.strip().lower().encode(), (SERVER_HOST, UDP_PORT)) 
                break

        except socket.timeout:
            print("[DEBUG] Timeout! No UDP response from server.")
            continue 

        except Exception as e:
            print(f"[ERROR] Error receiving UDP message: {e}")
            break


def send_guesses():
    if player_name is None:  # Check if player_name is not set
        player_name = input("Enter your player name: ")
    while not game_over.is_set():
        try:
            guess = input("Enter your guess: ")
            if not guess.isdigit():
                print("Please enter a valid number. Try again.")
                continue
            guess = int(guess)
            if guess < 1 or guess > 100:
                print("Warning: Out of range! Please enter a number between 1 and 100.")
                continue
            print(f"[DEBUG] Sending guess {guess}")
            
            guess_msg = f"{player_name}:{guess}"
            UDPSocket.sendto(guess_msg.encode(), (SERVER_HOST, UDP_PORT))
            try:
                response, _ = UDPSocket.recvfrom(1024)  
                decoded_response = response.decode()
                print(f"[DEBUG] Server response: {decoded_response}")

                if "Correct" in decoded_response or "Game Over" in decoded_response:
                    print(decoded_response)
                    game_over.set()
                    break  
            except socket.timeout:
                print("Timeout while waiting for response!")
                continue
        except Exception as e:
            print(f"[ERROR] Error while sending guess: {e}")
            continue

def start_guessing_phase():
    if game_started.is_set():  # Ensure the game has started before proceeding
        print("[DEBUG] Starting guessing phase...")
        print("You can now start guessing.")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.submit(send_guesses)

# ==================== MAIN ====================

def main():
    register_player()
    print(f"Player {player_name} registered successfully!")

    # Start listening for game start via UDP in background
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.submit(listen_for_udp_messages)
        print("[DEBUG] Waiting for game to start...")
        game_started.wait()  # block until flag is set

        print("[DEBUG] Game started. Starting guessing phase...")
        start_guessing_phase() 

if __name__ == "__main__":
    main()
