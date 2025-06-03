import os
import json
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VehicleDataManager:
    """
    Gerenciador de dados de veículos para autocomplete e sugestões.
    Trabalha exclusivamente com banco de dados local e arquivos JSON.
    """
    
    def __init__(self):
        # Diretório para armazenar modelos de veículos
        self.models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'vehicle_models')
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Garantir que os arquivos JSON existam
        self._ensure_json_files()
    
    def _ensure_json_files(self):
        """Garante que os arquivos JSON necessários existam"""
        # Arquivo de carros
        car_file = os.path.join(self.models_dir, 'carros.json')
        if not os.path.exists(car_file):
            default_cars = [
                "Gol", "Uno", "Palio", "Celta", "Corsa", "Civic", "Corolla", "Onix", 
                "HB20", "Fiesta", "Focus", "Fusca", "Sandero", "Logan", "Cruze", 
                "Fit", "City", "Siena", "Prisma", "Voyage", "Fox", "Up", "Ka", 
                "Ecosport", "Duster", "Renegade", "Compass", "Tracker", "Creta",
                "Hilux", "Ranger", "S10", "Amarok", "Frontier", "Strada", "Saveiro",
                "Montana", "Toro", "HR-V"
            ]
            with open(car_file, 'w', encoding='utf-8') as f:
                json.dump({"models": default_cars}, f, ensure_ascii=False, indent=2)
        
        # Arquivo de motos
        moto_file = os.path.join(self.models_dir, 'motos.json')
        if not os.path.exists(moto_file):
            default_motos = [
                "CG 125", "CG 150", "CG 160", "Biz", "Factor", "YBR", "Fazer", 
                "CB 300", "XRE 300", "Falcon", "Bros", "Titan", "Fan", "Twister", 
                "Hornet", "CBR", "XJ", "XT", "XTZ", "PCX", "NMax", "Lead"
            ]
            with open(moto_file, 'w', encoding='utf-8') as f:
                json.dump({"models": default_motos}, f, ensure_ascii=False, indent=2)
        
        # Arquivo de cores
        color_file = os.path.join(self.models_dir, 'cores.json')
        if not os.path.exists(color_file):
            default_colors = [
                "Preto", "Branco", "Prata", "Cinza", "Vermelho", "Azul", "Verde", 
                "Amarelo", "Marrom", "Bege", "Laranja", "Roxo", "Rosa", "Dourado"
            ]
            with open(color_file, 'w', encoding='utf-8') as f:
                json.dump(default_colors, f, ensure_ascii=False, indent=2)
    
    def load_car_models(self):
        """Carrega modelos de carros do arquivo JSON"""
        try:
            file_path = os.path.join(self.models_dir, 'carros.json')
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict) and 'models' in data:
                        return data['models']
            return []
        except Exception as e:
            logger.error(f"Erro ao carregar modelos de carros: {str(e)}")
            return []
    
    def load_motorcycle_models(self):
        """Carrega modelos de motos do arquivo JSON"""
        try:
            file_path = os.path.join(self.models_dir, 'motos.json')
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict) and 'models' in data:
                        return data['models']
            return []
        except Exception as e:
            logger.error(f"Erro ao carregar modelos de motos: {str(e)}")
            return []
    
    def load_colors(self):
        """Carrega cores do arquivo JSON"""
        try:
            file_path = os.path.join(self.models_dir, 'cores.json')
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
    
    def refresh_data(self):
        """Recarrega todos os dados dos arquivos JSON"""
        self._ensure_json_files()
        return {
            'car_models': self.load_car_models(),
            'motorcycle_models': self.load_motorcycle_models(),
            'colors': self.load_colors()
        }
