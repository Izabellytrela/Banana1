from flask import Flask, request
from pyngrok import ngrok
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from PIL import Image
import numpy as np
import cv2
from sklearn.cluster import KMeans
import gdown

# Substitua "SEU_TOKEN" pelo seu token do ngrok
ngrok.set_auth_token("2lCzOKOIJIv4EzyjZUbn5u3t5D5_LbEFDV95sB6stkAnTNkk")

app = Flask(__name__)

# Função para executar seu código
def executar_meu_codigo():
    # Autenticação com o Google Sheets usando credenciais
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)

    # Abrir a planilha
    spreadsheet_url = 'https://docs.google.com/spreadsheets/d/1uTGil123c-mqMiysxt3-YF-ZPrpx2KXUyK8PvrSU9v8/edit?gid=0'
    sheet = client.open_by_url(spreadsheet_url).sheet1

    # Pegar o número da última linha
    last_row_number = len(sheet.get_all_values())  # Conta todas as linhas com dados

    # Pegar o link da última linha da primeira coluna
    image_url = sheet.cell(last_row_number, 1).value  # Coluna 1 (A) e última linha

    # Verificar se o link é um link válido do Google Drive
    if 'drive.google.com' in image_url:
        # Converter o link para o formato de download direto
        file_id = image_url.split('/')[-2]
        download_url = f'https://drive.google.com/uc?id={file_id}'

        # Baixar a imagem
        output_image = 'image_downloaded.jpg'
        gdown.download(download_url, output_image, quiet=False)

        # Abrir a imagem baixada com o PIL
        try:
            image = Image.open(output_image)
            image.show()  # Exibir a imagem para garantir que foi carregada corretamente

            # Converter a imagem para o formato OpenCV
            image_cv = np.array(image)
            image_cv = cv2.cvtColor(image_cv, cv2.COLOR_RGB2BGR)

            # Funções de processamento
            def obter_cor_dominante(image, k=3):
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                reshaped_image = rgb_image.reshape((-1, 3))
                kmeans = KMeans(n_clusters=k)
                kmeans.fit(reshaped_image)
                cores_dominantes = kmeans.cluster_centers_
                labels = kmeans.labels_
                counts = np.bincount(labels)
                cor_dominante = cores_dominantes[np.argmax(counts)]
                return cor_dominante.astype(int)

            def classificar_maturacao(cor_dominante):
                r, g, b = cor_dominante
                if r < 100 and g > 60 and b < 100:
                    return "c1 - Banana verde (não madura)"
                elif r < 150 and g > 150 and b < 150:
                    return "c2 - Banana verde-amarelada"
                elif r > 140 and g > 145 and b < 30:
                    return "c3 - Banana amarela esverdeada (quase madura)"
                elif r > 200 and g > 170 and b > 0 and b < 80:
                    return "c4 - Banana amarela (madura)"
                elif r > 180 and g > 150 and b < 70:
                    return "c5 - Banana amarela com poucas manchas"
                elif r > 135 and g > 135 and b < 40:
                    return "c6 - Banana madura com muitas manchas"
                elif r > 100 and g > 80 and b < 80:
                    return "c7 - Banana amarela passada"
                else:
                    return "Maturação não identificada"

            def avaliar_venda(fase_maturacao):
                if fase_maturacao in ["c3 - Banana amarela esverdeada (quase madura)", "c4 - Banana amarela (madura)", "c5 - Banana amarela com poucas manchas"]:
                    return "Aprovada para venda"
                else:
                    return "Reprovada para venda"

            # Processar a imagem
            cor_dominante = obter_cor_dominante(image_cv)
            fase_maturacao = classificar_maturacao(cor_dominante)
            status_venda = avaliar_venda(fase_maturacao)

            # Exibir os resultados
            print("Cor dominante (RGB):", cor_dominante)
            print("Fase de maturação:", fase_maturacao)
            print("Status para venda:", status_venda)

            # Atualizar o status na planilha (Coluna 2 da mesma linha)
            sheet.update_cell(last_row_number, 2, status_venda)  # Atualiza na coluna B (2ª coluna)
            print(f"O status '{status_venda}' foi atualizado na linha {last_row_number}, coluna 2.")

        except IOError:
            print("Erro ao abrir a imagem. Verifique se o arquivo é válido.")
    else:
        print("O link fornecido não é um link válido do Google Drive.")

# Definir a rota do webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print('Webhook acionado!')
    print(f'Dados recebidos: {data}')

    # Chamar o código Python que você quer rodar
    executar_meu_codigo()

    return "Webhook recebido e código executado", 200

# Conectar o ngrok à porta 5000
public_url = ngrok.connect(5000)
print(f'Public URL: {public_url}')

# Iniciar o servidor Flask
app.run(port=5000)
