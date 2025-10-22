import time
import board
import busio
import socket
import statistics
import json 
from adafruit_mlx90614 import MLX90614

# --- Configurações ---
HOST = '127.0.0.1'
PORT = 65432
AMOSTRAS_PARA_COLETAR = 10
CALIBRACAO_OFFSET = 6.7
TEMPERATURA_MIN_VALIDA = 34.0 # <-- Suas leituras de 25.61°C são menores que isso
TEMPERATURA_MAX_VALIDA = 42.0

def iniciar_sensor():
    """Tenta inicializar o sensor I2C e retorna o objeto do sensor ou None se falhar."""
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        mlx = MLX90614(i2c)
        print("Sensor MLX90614 iniciado com sucesso.")
        return mlx
    except Exception as e:
        print(f"❌ Erro ao iniciar sensor MLX90614: {e}")
        print("    Verifique a conexão física do sensor (SCL, SDA, VCC, GND).")
        return None

def processar_leituras(leituras):
    """Filtra leituras fora do intervalo válido e calcula a mediana."""
    leituras_validas = [
        temp for temp in leituras
        if TEMPERATURA_MIN_VALIDA <= temp <= TEMPERATURA_MAX_VALIDA
    ]

    if not leituras_validas:
        print("Nenhuma leitura válida foi coletada no lote.")
        return None

    mediana = statistics.median(leituras_validas)
    print(f"    Leituras válidas: {leituras_validas}")
    print(f"    Mediana calculada: {mediana:.2f} °C")
    return mediana

def main():
    mlx = iniciar_sensor()
    if not mlx:
        return

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f" Servidor de socket iniciado. Aguardando conexão em {HOST}:{PORT}...")

        while True:
            conn, addr = s.accept()
            with conn:
                print(f"🔗 Conectado por {addr}")
                leituras_temperatura = []

                while True:
                    try:
                        temp_objeto_calibrada = mlx.object_temperature + CALIBRACAO_OFFSET
                        print(f"    Leitura atual: {temp_objeto_calibrada:.2f} °C")
                        leituras_temperatura.append(temp_objeto_calibrada)

                        if len(leituras_temperatura) >= AMOSTRAS_PARA_COLETAR:
                            print("\nProcessando lote de 10 leituras...")
                            temperatura_final = processar_leituras(leituras_temperatura)
                            
                            # Limpa o lote de leituras para começar um novo
                            leituras_temperatura = [] 

                            if temperatura_final is not None:
                                # --- SUCESSO: TEMPERATURA VÁLIDA ---
                                # Cria um dicionário Python com os dados
                                data_json = {
                                    "temperature": round(temperatura_final, 2)
                                }
                                # Converte o dicionário para uma string JSON e depois para bytes
                                mensagem_json = json.dumps(data_json).encode('utf-8')
                                
                                conn.sendall(mensagem_json) # Envia o JSON
                                print(f" JSON enviado para o cliente: {mensagem_json.decode('utf-8')}")
                                print(f"🔌 Desconectando cliente {addr}...\n")
                                
                                # Sai do loop 'while True' interno, fechando a conexão
                                break 
                            
                            else:
                                # --- FALHA: NENHUMA LEITURA VÁLIDA ---
                                # Apenas avisa e continua o loop para tentar de novo
                                print("Nenhuma leitura válida. Coletando novo lote...\n")
                                # --- NENHUM 'break' AQUI ---


                        time.sleep(0.5)

                    except (ConnectionResetError, BrokenPipeError):
                        # Cliente desconectou antes de receber os dados
                        print(f" Cliente {addr} desconectou antes do envio.")
                        break
                    except Exception as e:
                        # Outro erro (ex: falha na leitura do sensor)
                        print(f" Erro durante a execução: {e}")
                        break
            
            # O código chega aqui após a conexão com o cliente ser fechada.
            # O loop 'while True' externo garante que o servidor
            # volte a esperar por uma nova conexão.

if __name__ == "__main__":
    main()
