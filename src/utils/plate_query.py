import requests
import json
import os
from datetime import datetime
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlateQueryCascade:
    """
    Sistema de cascata para consulta de placas de veículos.
    Tenta várias APIs em sequência até obter um resultado válido.
    """
    
    def __init__(self):
        self.apis = [
            self._query_brasil_api,
            self._query_placa_fipe,
            self._query_denatran
        ]
        
        # Diretório para armazenar modelos de veículos
        self.models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'vehicle_models')
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Carregar modelos de veículos disponíveis
        self.available_models = self._load_available_models()
    
    def _load_available_models(self):
        """Carrega modelos de veículos disponíveis a partir de arquivos JSON"""
        models = []
        
        # Verifica se existem arquivos JSON no diretório
        if os.path.exists(self.models_dir):
            for filename in os.listdir(self.models_dir):
                if filename.endswith('.json'):
                    try:
                        with open(os.path.join(self.models_dir, filename), 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                models.extend(data)
                            elif isinstance(data, dict) and 'models' in data:
                                models.extend(data['models'])
                    except Exception as e:
                        logger.error(f"Erro ao carregar arquivo de modelos {filename}: {str(e)}")
        
        # Se não houver modelos carregados, adiciona alguns modelos padrão
        if not models:
            models = [
                "Gol", "Uno", "Palio", "Celta", "Corsa", "Civic", "Corolla", "Onix", 
                "HB20", "Fiesta", "Focus", "Fusca", "Sandero", "Logan", "Cruze", 
                "Fit", "City", "Siena", "Prisma", "Voyage", "Fox", "Up", "Ka", 
                "Ecosport", "Duster", "Renegade", "Compass", "Tracker", "Creta",
                "Hilux", "Ranger", "S10", "Amarok", "Frontier", "Strada", "Saveiro",
                "Montana", "Toro", "HR-V", "CG 125", "CG 150", "CG 160", "Biz", 
                "Factor", "YBR", "Fazer", "CB 300", "XRE 300", "Falcon", "Bros", 
                "Titan", "Fan", "Twister", "Hornet", "CBR", "XJ", "XT", "XTZ"
            ]
        
        return sorted(list(set(models)))  # Remove duplicatas e ordena
    
    def _query_brasil_api(self, plate):
        """Consulta a placa na API Brasil"""
        try:
            url = f"https://brasilapi.com.br/api/fipe/preco/v1/{plate}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if 'modelo' in data and 'cor' in data:
                    return {
                        'model': data['modelo'],
                        'color': data['cor'],
                        'source': 'brasilapi'
                    }
            return None
        except Exception as e:
            logger.error(f"Erro ao consultar Brasil API: {str(e)}")
            return None
    
    def _query_placa_fipe(self, plate):
        """Consulta a placa na API Placa FIPE"""
        try:
            url = "https://placa-fipe.apibrasil.com.br/placa/consulta"
            payload = {"placa": plate}
            headers = {"Content-Type": "application/json"}
            
            response = requests.post(url, json=payload, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if 'modelo' in data and 'cor' in data:
                    return {
                        'model': data['modelo'],
                        'color': data['cor'],
                        'source': 'placa-fipe'
                    }
            return None
        except Exception as e:
            logger.error(f"Erro ao consultar Placa FIPE: {str(e)}")
            return None
    
    def _query_denatran(self, plate):
        """Consulta a placa no Denatran (simulado)"""
        # Esta é uma implementação simulada, pois o Denatran não oferece API pública oficial
        try:
            # Simulação de consulta - em um ambiente real, seria substituído pela API real
            return None
        except Exception as e:
            logger.error(f"Erro ao consultar Denatran: {str(e)}")
            return None
    
    def query_plate(self, plate):
        """
        Consulta a placa em várias APIs em cascata.
        Retorna o primeiro resultado válido ou None se todas falharem.
        """
        for api_func in self.apis:
            result = api_func(plate)
            if result:
                logger.info(f"Placa {plate} encontrada via {result['source']}")
                return result
        
        logger.info(f"Placa {plate} não encontrada em nenhuma API")
        return None
    
    def get_available_models(self):
        """Retorna a lista de modelos disponíveis para autocomplete"""
        return self.available_models
    
    def refresh_models(self):
        """Recarrega os modelos disponíveis a partir dos arquivos JSON"""
        self.available_models = self._load_available_models()
        return self.available_models
