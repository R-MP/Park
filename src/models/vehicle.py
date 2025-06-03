from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import json
from .user import db
import pytz

fuso_brasilia = pytz.timezone('America/Sao_Paulo')

def hora_brasilia():
    return datetime.now(fuso_brasilia)

class Vehicle(db.Model):
    """Modelo para armazenar informações de veículos consultados"""
    __tablename__ = 'vehicles'
    
    id = db.Column(db.Integer, primary_key=True)
    plate = db.Column(db.String(10), unique=True, nullable=False, index=True)
    model = db.Column(db.String(100), nullable=True)
    color = db.Column(db.String(50), nullable=True)
    vehicle_type = db.Column(db.String(10), nullable=False, default='carro')  # carro ou moto
    last_seen = db.Column(db.DateTime, default=hora_brasilia, onupdate=hora_brasilia)
    
    @staticmethod
    def get_by_plate(plate):
        """Busca um veículo pela placa"""
        return Vehicle.query.filter_by(plate=plate.upper()).first()
    
    @staticmethod
    def create_or_update(plate, model=None, color=None, vehicle_type='carro'):
        """Cria ou atualiza um registro de veículo"""
        vehicle = Vehicle.get_by_plate(plate)
        
        if vehicle:
            # Atualiza apenas se os novos dados não forem None
            if model:
                vehicle.model = model
            if color:
                vehicle.color = color
            if vehicle_type:
                vehicle.vehicle_type = vehicle_type
            vehicle.last_seen = hora_brasilia()
        else:
            # Cria um novo registro
            vehicle = Vehicle(
                plate=plate.upper(),
                model=model,
                color=color,
                vehicle_type=vehicle_type
            )
            db.session.add(vehicle)
        
        db.session.commit()
        
        # Atualiza os arquivos JSON se necessário
        if model:
            Vehicle.add_model_to_json(model, vehicle_type)
        if color:
            Vehicle.add_color_to_json(color)
            
        return vehicle
    
    @staticmethod
    def get_car_models():
        """Retorna uma lista de modelos de carros disponíveis"""
        # Busca modelos de carros no banco de dados
        models = db.session.query(Vehicle.model).distinct().filter(
            Vehicle.model.isnot(None),
            Vehicle.vehicle_type == 'carro'
        ).all()
        models = [model[0] for model in models if model[0]]
        
        # Adiciona modelos do arquivo JSON de carros
        json_models = Vehicle._load_json_models('carros.json')
        if json_models:
            models.extend(json_models)
        
        # Remove duplicatas e ordena
        return sorted(list(set(models)))
    
    @staticmethod
    def get_motorcycle_models():
        """Retorna uma lista de modelos de motos disponíveis"""
        # Busca modelos de motos no banco de dados
        models = db.session.query(Vehicle.model).distinct().filter(
            Vehicle.model.isnot(None),
            Vehicle.vehicle_type == 'moto'
        ).all()
        models = [model[0] for model in models if model[0]]
        
        # Adiciona modelos do arquivo JSON de motos
        json_models = Vehicle._load_json_models('motos.json')
        if json_models:
            models.extend(json_models)
        
        # Remove duplicatas e ordena
        return sorted(list(set(models)))
    
    @staticmethod
    def get_available_colors():
        """Retorna uma lista de cores disponíveis"""
        # Busca cores no banco de dados
        colors = db.session.query(Vehicle.color).distinct().filter(Vehicle.color.isnot(None)).all()
        colors = [color[0] for color in colors if color[0]]
        
        # Adiciona cores do arquivo JSON
        json_colors = Vehicle._load_json_colors()
        if json_colors:
            colors.extend(json_colors)
        
        # Remove duplicatas e ordena
        return sorted(list(set(colors)))
    
    @staticmethod
    def get_registered_plates():
        """Retorna uma lista de placas já registradas no sistema"""
        plates = db.session.query(Vehicle.plate).all()
        return [plate[0] for plate in plates]
    
    @staticmethod
    def _load_json_models(filename):
        """Carrega modelos de um arquivo JSON específico"""
        models = []
        models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'vehicle_models')
        
        if os.path.exists(models_dir):
            file_path = os.path.join(models_dir, filename)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            models.extend(data)
                        elif isinstance(data, dict) and 'models' in data:
                            models.extend(data['models'])
                except Exception as e:
                    print(f"Erro ao carregar arquivo {filename}: {str(e)}")
        
        return models
    
    @staticmethod
    def _load_json_colors():
        """Carrega cores do arquivo JSON"""
        colors = []
        models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'vehicle_models')
        
        if os.path.exists(models_dir):
            file_path = os.path.join(models_dir, 'cores.json')
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            colors.extend(data)
                        elif isinstance(data, dict) and 'colors' in data:
                            colors.extend(data['colors'])
                except Exception as e:
                    print(f"Erro ao carregar arquivo de cores: {str(e)}")
        
        return colors
    
    @staticmethod
    def add_model_to_json(model, vehicle_type):
        """Adiciona um modelo ao arquivo JSON correspondente se não existir"""
        if not model:
            return
            
        # Determina qual arquivo JSON usar com base no tipo de veículo
        filename = 'carros.json' if vehicle_type == 'carro' else 'motos.json'
        models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'vehicle_models')
        
        if not os.path.exists(models_dir):
            os.makedirs(models_dir)
            
        file_path = os.path.join(models_dir, filename)
        
        # Carrega os modelos existentes
        existing_models = []
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        existing_models = data
                    elif isinstance(data, dict) and 'models' in data:
                        existing_models = data['models']
            except Exception:
                existing_models = []
        
        # Adiciona o novo modelo se não existir
        if model not in existing_models:
            existing_models.append(model)
            existing_models.sort()
            
            # Salva o arquivo atualizado
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                        # Mantém o formato original do arquivo
                        try:
                            with open(file_path, 'r', encoding='utf-8') as original:
                                original_data = json.load(original)
                                if isinstance(original_data, dict):
                                    json.dump({"models": existing_models}, f, ensure_ascii=False, indent=2)
                                else:
                                    json.dump(existing_models, f, ensure_ascii=False, indent=2)
                        except Exception:
                            json.dump({"models": existing_models}, f, ensure_ascii=False, indent=2)
                    else:
                        # Cria um novo arquivo com formato padrão
                        json.dump({"models": existing_models}, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Erro ao salvar modelo no arquivo JSON: {str(e)}")
    
    @staticmethod
    def add_color_to_json(color):
        """Adiciona uma cor ao arquivo JSON se não existir"""
        if not color:
            return
            
        models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'vehicle_models')
        
        if not os.path.exists(models_dir):
            os.makedirs(models_dir)
            
        file_path = os.path.join(models_dir, 'cores.json')
        
        # Carrega as cores existentes
        existing_colors = []
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        existing_colors = data
                    elif isinstance(data, dict) and 'colors' in data:
                        existing_colors = data['colors']
            except Exception:
                existing_colors = []
        
        # Adiciona a nova cor se não existir
        if color not in existing_colors:
            existing_colors.append(color)
            existing_colors.sort()
            
            # Salva o arquivo atualizado
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                        # Mantém o formato original do arquivo
                        try:
                            with open(file_path, 'r', encoding='utf-8') as original:
                                original_data = json.load(original)
                                if isinstance(original_data, dict):
                                    json.dump({"colors": existing_colors}, f, ensure_ascii=False, indent=2)
                                else:
                                    json.dump(existing_colors, f, ensure_ascii=False, indent=2)
                        except Exception:
                            json.dump(existing_colors, f, ensure_ascii=False, indent=2)
                    else:
                        # Cria um novo arquivo com formato padrão
                        json.dump(existing_colors, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Erro ao salvar cor no arquivo JSON: {str(e)}")
    
    def __repr__(self):
        return f'<Vehicle {self.plate} - {self.model} - {self.color}>'
