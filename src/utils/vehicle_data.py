import os
import json
import logging
import requests
from dotenv import load_dotenv

load_dotenv() 

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VehicleDataManager:
    """
    Gerenciador de dados de veículos para autocomplete e sugestões.
    Trabalha com banco de dados local, arquivos JSON e API Invertexto.
    """
    
    def __init__(self):
        # Diretório para armazenar modelos de veículos
        self.models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'vehicle_models')
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Diretórios para carros e motos
        self.cars_dir = os.path.join(self.models_dir, 'cars')
        self.motorcycles_dir = os.path.join(self.models_dir, 'motorcycles')
        
        # Garantir que os diretórios existam
        os.makedirs(self.cars_dir, exist_ok=True)
        os.makedirs(self.motorcycles_dir, exist_ok=True)
        
        # Token da API Invertexto
        self.api_token = os.getenv("INVERTEXTO_TOKEN", "").strip()
        
        # Garantir que os arquivos JSON existam
        self._ensure_json_files()
    
    def _ensure_json_files(self):
        """Garante que os arquivos JSON necessários existam"""
        # Arquivo de cores
        color_file = os.path.join(self.models_dir, 'colors.json')
        if not os.path.exists(color_file):
            default_colors = [
                "Preto", "Branco", "Prata", "Cinza", "Vermelho", "Azul", "Verde", 
                "Amarelo", "Marrom", "Bege", "Laranja", "Roxo", "Rosa", "Dourado"
            ]
            with open(color_file, 'w', encoding='utf-8') as f:
                json.dump(default_colors, f, ensure_ascii=False, indent=2)
        
        # Arquivo de marcas
        brands_file = os.path.join(self.models_dir, 'marcas.json')
        if not os.path.exists(brands_file):
            default_brands = {
                "marcas": [
                    {"nome": "Fiat", "id": 21, "tipo": "carro"},
                    {"nome": "Ford", "id": 22, "tipo": "carro"},
                    {"nome": "GM - Chevrolet", "id": 23, "tipo": "carro"},
                    {"nome": "VW - VolksWagen", "id": 59, "tipo": "carro"},
                    {"nome": "Toyota", "id": 56, "tipo": "carro"},
                    {"nome": "Honda", "id": 25, "tipo": "carro"},
                    {"nome": "Honda Motos", "id": 80, "tipo": "moto"},
                    {"nome": "Yamaha", "id": 60, "tipo": "moto"}
                ]
            }
            with open(brands_file, 'w', encoding='utf-8') as f:
                json.dump(default_brands, f, ensure_ascii=False, indent=2)
    
    def load_brands(self):
        """Carrega as marcas do arquivo JSON"""
        try:
            file_path = os.path.join(self.models_dir, 'marcas.json')
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and 'marcas' in data:
                        return data['marcas']
            return []
        except Exception as e:
            logger.error(f"Erro ao carregar marcas: {str(e)}")
            return []
    
    def get_car_brands(self):
        """Retorna apenas as marcas de carros"""
        brands = self.load_brands()
        return [brand for brand in brands if brand.get('tipo') == 'carro']
    
    def get_motorcycle_brands(self):
        """Retorna apenas as marcas de motos"""
        brands = self.load_brands()
        return [brand for brand in brands if brand.get('tipo') == 'moto']
    
    def load_car_models(self):
        """Carrega todos os modelos de carros de todos os arquivos JSON"""
        models = []
        
        if not os.path.exists(self.cars_dir):
            return models
        
        for filename in os.listdir(self.cars_dir):
            if not filename.endswith('.json'):
                continue
            
            file_path = os.path.join(self.cars_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Se for lista de dicionários: extrai data[i]["model"]
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and 'model' in item:
                                models.append(item['model'])
                            elif isinstance(item, str):
                                models.append(item)
                    # Se for dicionário com chave "models": percorre data["models"]
                    elif isinstance(data, dict) and 'models' in data:
                        for item in data['models']:
                            if isinstance(item, dict) and 'model' in item:
                                models.append(item['model'])
                            elif isinstance(item, str):
                                models.append(item)
            except Exception as e:
                logger.error(f"Erro ao carregar arquivo {filename}: {str(e)}")
        
        # Remove duplicatas e ordena a lista de strings
        return sorted(list(set(models)))

    
    def load_motorcycle_models(self):
        """Carrega todos os modelos de motos de todos os arquivos JSON"""
        models = []
        
        # Verificar se o diretório existe
        if not os.path.exists(self.motorcycles_dir):
            return models
        
        # Percorrer todos os arquivos JSON no diretório de motos
        for filename in os.listdir(self.motorcycles_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(self.motorcycles_dir, filename), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            models.extend(data)
                        elif isinstance(data, dict) and 'models' in data:
                            models.extend(data['models'])
                except Exception as e:
                    logger.error(f"Erro ao carregar arquivo {filename}: {str(e)}")
        
        # Remover duplicatas e ordenar
        return sorted(list(set(models)))
    
    def load_colors(self):
        """Carrega cores do arquivo JSON"""
        try:
            file_path = os.path.join(self.models_dir, 'colors.json')
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict) and 'colors' in data:
                        return data['colors']
            return []
        except Exception as e:
            logger.error(f"Erro ao carregar cores: {str(e)}")
            return []
    
    def download_models_from_api(self, brand_id, brand_name, vehicle_type):
        """
        Baixa modelos da API Invertexto e salva em um arquivo JSON
        
        Args:
            brand_id (int): ID da marca na API Invertexto
            brand_name (str): Nome da marca para o arquivo JSON
            vehicle_type (str): Tipo de veículo ('carro' ou 'moto')
            
        Returns:
            tuple: (success, message, models_count)
        """
        try:
            # URL de consulta
            url = f"https://api.invertexto.com/v1/fipe/models/{brand_id}?token={self.api_token}"
            
            # 2) Faz a requisição
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return False, f"Erro na API: código {response.status_code}", 0
            
            # 3) Converte para JSON e LOGA o resultado bruto (para debug)
            data = response.json()
            logger.info(f"DEBUG | Resposta da API Invertexto para marca {brand_name} (id={brand_id}): {data}")
            
            # 4) Agora tentamos extrair a lista de modelos de dois jeitos:
            models_list = []
            # Se vier um dict e tiver a chave 'models', pegamos data['models']
            if isinstance(data, dict) and 'models' in data and isinstance(data['models'], list):
                models_list = data['models']
            # Se já veio uma lista pura, assumimos que data é essa lista
            elif isinstance(data, list):
                models_list = data
            else:
                return False, "Formato de resposta inválido", 0
            
            # 5) A seguir, extraímos apenas o nome/texto de cada modelo
            model_names = []
            for item in models_list:
                if not isinstance(item, dict):
                    continue
                # Algumas APIs retornam campo 'name', outras retornam 'model'
                if 'name' in item and isinstance(item['name'], str):
                    model_names.append(item['name'])
                elif 'model' in item and isinstance(item['model'], str):
                    model_names.append(item['model'])
                # se nenhum desses campos existir, ignora esse item
            # Fim do loop
            
            if not model_names:
                return False, "Nenhum modelo encontrado", 0
            
            # 6) Ordena a lista, prepara o diretório alvo e salva em disco
            model_names = sorted(set(model_names))
            target_dir = self.cars_dir if vehicle_type == 'carro' else self.motorcycles_dir
            os.makedirs(target_dir, exist_ok=True)  # garante que a pasta exista
            file_path = os.path.join(target_dir, f"{brand_name}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({"models": model_names}, f, ensure_ascii=False, indent=2)
            
            return True, f"Modelos baixados com sucesso: {len(model_names)}", len(model_names)
        
        except Exception as e:
            logger.error(f"Erro ao baixar modelos (brand_id={brand_id}): {str(e)}")
            return False, f"Erro ao baixar modelos: {str(e)}", 0

    
    def refresh_data(self):
        """Recarrega todos os dados dos arquivos JSON"""
        self._ensure_json_files()
        return {
            'car_models': self.load_car_models(),
            'motorcycle_models': self.load_motorcycle_models(),
            'colors': self.load_colors(),
            'brands': self.load_brands()
        }
