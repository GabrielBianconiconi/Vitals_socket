import socket
import json
import time

# --- Configurações (DEVEM ser as mesmas do servidor) ---
HOST = '127.0.0.1'
PORT = 65433

def main():
    print("Iniciando cliente de teste para Oximetria...")
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            print(f"Tentando conectar a {HOST}:{PORT}...")
            s.connect((HOST, PORT))
            print(" Conectado com sucesso ao servidor do sensor!")
            print("Aguardando o recebimento dos dados (após ~15 amostras)...")

            while True:
                data = s.recv(1024)
                if not data:
                    print(" Conexão fechada pelo servidor.")
                    break

                try:
                    sensor_data = json.loads(data.decode('utf-8'))
                    bpm = sensor_data.get('bpm', 'N/A')
                    spo2 = sensor_data.get('spo2', 'N/A')
                    print(f"   --->  DADO RECEBIDO: BPM = {bpm}, SpO2 = {spo2} %")
                except json.JSONDecodeError:
                    # Ignora mensagens que não são JSON (como o "ping" de conexão)
                    pass

    except ConnectionRefusedError:
        print("\n ERRO DE CONEXÃO: Verifique se o script do servidor do sensor já está rodando.")
    except KeyboardInterrupt:
        print("\nCliente encerrado pelo usuário.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

if __name__ == "__main__":
    main()
