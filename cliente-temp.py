import socket
import json
import time

# --- Configurações (DEVEM ser as mesmas do servidor) ---
HOST = '127.0.0.1'  # O endereço do servidor
PORT = 65432       # A porta do servidor

def main():
    """
    Cliente que se conecta ao servidor do sensor para receber leituras de temperatura.
    """
    print("Iniciando cliente de teste...")
    
    # Cria o socket e tenta se conectar
    try:
        # A instrução 'with' garante que o socket seja fechado automaticamente
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            print(f"Tentando conectar a {HOST}:{PORT}...")
            s.connect((HOST, PORT))
            print("Conectado com sucesso ao servidor do sensor!")
            print("Aguardando o recebimento dos dados (o servidor envia a cada 10 leituras)...")

            # Loop infinito para continuar recebendo dados do servidor
            while True:
                # Espera por dados, o buffer de 1024 bytes é mais que suficiente
                data = s.recv(1024)
                
                # Se recv() retornar uma string de bytes vazia, significa que o servidor fechou a conexão
                if not data:
                    print(" Conexão fechada pelo servidor.")
                    break

                # Os dados chegam como bytes, então decodificamos para uma string
                json_string = data.decode('utf-8')

                try:
                    # Tentamos converter a string JSON em um objeto Python (dicionário)
                    sensor_data = json.loads(json_string)
                    temperatura = sensor_data.get('temperature', 'N/A') # .get() é mais seguro que []
                    print(f"   --->  DADO RECEBIDO: Temperatura = {temperatura} °C")
                except json.JSONDecodeError:
                    print(f" Erro: Dado recebido não é um JSON válido: '{json_string}'")

    except ConnectionRefusedError:
        print("\n ERRO DE CONEXÃO: Não foi possível se conectar.")
        print("   Verifique se o script do servidor (com o sensor) já está rodando.")
    except KeyboardInterrupt:
        print("\nCliente encerrado pelo usuário.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")


if __name__ == "__main__":
    main()
