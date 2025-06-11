from flask import (
    Blueprint,
    request,
    jsonify,
    session,
    redirect,
    url_for,
    render_template,
    flash,
)
from datetime import datetime
import string
import random
import pytz
from src.models.parking import ParkingRecord
from src.models.price import PriceConfiguration
from src.models.user import User, db
from src.models.vehicle import Vehicle
from src.utils.vehicle_data import VehicleDataManager
from src.routes.auth import login_required, admin_required

parking_bp = Blueprint("parking", __name__)

fuso_brasilia = pytz.timezone("America/Sao_Paulo")
vehicle_data = VehicleDataManager()

def generate_code(n=5):
    """Gera um código aleatório de n caracteres (A–Z, 0–9)."""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=n))

@parking_bp.route("/entrada", methods=["GET", "POST"])
@login_required
def register_entry():
    # Carregar modelos e cores disponíveis para autocomplete
    car_models = Vehicle.get_car_models()
    motorcycle_models = Vehicle.get_motorcycle_models()
    available_colors = Vehicle.get_available_colors()
    registered_plates = Vehicle.get_registered_plates()

    if request.method == "POST":
        plate = request.form.get("plate")
        vehicle_type = request.form.get("vehicle_type", "carro")
        is_daily = request.form.get("is_daily") == "on"

        if not plate:
            flash("A placa do veículo é obrigatória.", "danger")
            return render_template(
                "parking/entry.html",
                car_models=car_models,
                motorcycle_models=motorcycle_models,
                available_colors=available_colors,
                registered_plates=registered_plates,
            )

        existing_entry = ParkingRecord.query.filter_by(
            plate=plate, exit_time=None
        ).first()

        if existing_entry:
            flash("Este veículo já está registrado no estacionamento.", "warning")
            return render_template(
                "parking/entry.html",
                car_models=car_models,
                motorcycle_models=motorcycle_models,
                available_colors=available_colors,
                registered_plates=registered_plates,
            )

        car_model = request.form.get("car_model", "")
        car_color = request.form.get("car_color", "")

        # Registrar o veículo no banco de dados local
        # Isso também atualizará os arquivos JSON automaticamente
        Vehicle.create_or_update(
            plate=plate.upper(),
            model=car_model,
            color=car_color,
            vehicle_type=vehicle_type,
        )

        new_entry = ParkingRecord(
            plate=plate.upper(),
            user_id=session["user_id"],
            vehicle_type=vehicle_type,
            is_daily=is_daily,
            parking_code=generate_code()
        )

        db.session.add(new_entry)
        db.session.commit()

        flash(f"Veículo com placa {plate.upper()} registrado com sucesso!", "success")
        return redirect(url_for("parking.active_entries"))

    return render_template(
        "parking/entry.html",
        car_models=car_models,
        motorcycle_models=motorcycle_models,
        available_colors=available_colors,
        registered_plates=registered_plates,
    )


@parking_bp.route("/saida/<int:record_id>", methods=["GET", "POST"])
@login_required
def register_exit(record_id):
    # Busca o registro
    record = ParkingRecord.query.get_or_404(record_id)

    # Timezone de São Paulo
    fuso_brasilia = pytz.timezone("America/Sao_Paulo")
    now = datetime.now(fuso_brasilia)

    # Se já saiu, não deixa repetir
    if record.exit_time:
        flash("Este veículo já foi registrado como saída.", "warning")
        return redirect(url_for("parking.active_entries"))

    # Pega a configuração mais recente (ou cria defaults com tolerância = 5)
    price_config = PriceConfiguration.query.order_by(PriceConfiguration.id.desc()).first()
    if not price_config:
        price_config = PriceConfiguration(
            first_hour_car_price=10.0,
            additional_hour_car_price=5.0,
            daily_car_price=50.0,
            first_hour_motorcycle_price=5.0,
            additional_hour_motorcycle_price=3.0,
            daily_motorcycle_price=25.0,
            first_hour_price=10.0,
            additional_hour_price=5.0,
            time_tolerance=5,
            user_id=session['user_id']
        )
        db.session.add(price_config)
        db.session.commit()

    if request.method == "POST":
        # Marca saída oficial, calcula e salva
        record.exit_time = now
        record.calculate_total(price_config)
        db.session.commit()

        flash(
            f"Saída registrada com sucesso! Valor a cobrar: R$ {record.total_value:.2f}",
            "success",
        )
        return redirect(url_for("parking.receipt", record_id=record.id))

    # Para GET: estimativa de preço usando calculate_total
    # (não altera o registro definitivo)
    original_exit = record.exit_time
    record.exit_time = now
    estimated_price = record.calculate_total(price_config)
    record.exit_time = original_exit

    # Duração em horas para exibir na tela
    entry_time = record.entry_time.astimezone(fuso_brasilia)
    duration = (now - entry_time).total_seconds() / 3600

    return render_template(
        "parking/exit.html",
        record=record,
        duration=duration,
        estimated_price=estimated_price,
    )

@parking_bp.route("/codigo", methods=["GET", "POST"])
@login_required
def exit_by_code():
    """
    Página simples para o cliente digitar o código de 5 caracteres.
    Ao submeter, procura o ParkingRecord com parking_code = código
    e exit_time=None, registra saída e calcula total.
    """
    now = datetime.now(fuso_brasilia)

    if request.method == "POST":
        code = request.form.get("parking_code", "").upper().strip()
        if len(code) != 5:
            flash("Código deve ter exatamente 5 caracteres.", "danger")
            return render_template("parking/park_code.html")

        record = ParkingRecord.query.filter_by(parking_code=code, exit_time=None).first()
        print(record)
        print(code)
        if not record:
            flash("Código não encontrado ou já utilizado.", "danger")
            return render_template("parking/park_code.html")

        # encontra price_config
        price_config = PriceConfiguration.query.order_by(PriceConfiguration.id.desc()).first()
        if not price_config:
            # cria defaults se necessário…
            price_config = PriceConfiguration(
                first_hour_car_price=10.0,
                additional_hour_car_price=5.0,
                daily_car_price=50.0,
                first_hour_motorcycle_price=5.0,
                additional_hour_motorcycle_price=3.0,
                daily_motorcycle_price=25.0,
                first_hour_price=10.0,
                additional_hour_price=5.0,
                time_tolerance=5,
                user_id=session["user_id"],
            )
            db.session.add(price_config)
            db.session.commit()

        # registra saída
        record.exit_time = now
        record.calculate_total(price_config)
        db.session.commit()

        flash(f"Saída registrada! Placa: {record.plate} — Total: R$ {record.total_value:.2f}", "success")
        return redirect(url_for("parking.receipt", record_id=record.id))

    # GET
    return render_template("parking/park_code.html")


@parking_bp.route("/recibo/<int:record_id>")
@login_required
def receipt(record_id):
    record = ParkingRecord.query.get_or_404(record_id)

    if not record.exit_time:
        flash("Este veículo ainda não saiu do estacionamento.", "warning")
        return redirect(url_for("parking.active_entries"))

    duration_seconds = (record.exit_time - record.entry_time).total_seconds()
    hours = int(duration_seconds // 3600)
    minutes = int((duration_seconds % 3600) // 60)

    # Buscar informações adicionais do veículo
    vehicle = Vehicle.get_by_plate(record.plate)

    return render_template(
        "parking/receipt.html",
        record=record,
        vehicle=vehicle,
        hours=hours,
        minutes=minutes,
    )


@parking_bp.route("/ativos")
@login_required
def active_entries():
    active_records = (
        ParkingRecord.query.filter_by(exit_time=None)
        .order_by(ParkingRecord.entry_time.desc())
        .all()
    )

    # Buscar informações adicionais dos veículos
    vehicles = {}
    for record in active_records:
        vehicles[record.plate] = Vehicle.get_by_plate(record.plate)

    return render_template(
        "parking/active.html", records=active_records, vehicles=vehicles
    )


@parking_bp.route("/historico")
@login_required
def history():
    plate = request.args.get("plate", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    query = ParkingRecord.query

    if plate:
        query = query.filter(ParkingRecord.plate.like(f"%{plate}%"))

    if date_from:
        try:
            date_from = fuso_brasilia.localize(datetime.strptime(date_from, "%Y-%m-%d"))
            query = query.filter(ParkingRecord.entry_time >= date_from)
        except ValueError:
            pass

    if date_to:
        try:
            date_to = fuso_brasilia.localize(datetime.strptime(date_to, "%Y-%m-%d"))
            query = query.filter(ParkingRecord.entry_time <= date_to)
        except ValueError:
            pass

    records = query.order_by(ParkingRecord.entry_time.desc()).all()

    # Buscar informações adicionais dos veículos
    vehicles = {}
    for record in records:
        vehicles[record.plate] = Vehicle.get_by_plate(record.plate)

    return render_template(
        "parking/history.html",
        records=records,
        vehicles=vehicles,
        plate=plate,
        date_from=date_from,
        date_to=date_to,
    )

@parking_bp.route("/consulta_placa", methods=["POST"])
@login_required
def consulta_placa():
    data = request.get_json()
    placa = data.get("plate", "").upper().strip()

    if not placa:
        return jsonify({"error": "Placa não enviada"}), 400

    # Verificar se já temos o veículo no banco de dados local
    vehicle = Vehicle.get_by_plate(placa)
    if vehicle and vehicle.model and vehicle.color:
        return jsonify(
            {
                "modelo": vehicle.model,
                "cor": vehicle.color,
                "tipo": vehicle.vehicle_type,
            }
        )
    else:
        return (
            jsonify(
                {
                    "error": "Veículo não encontrado no banco de dados",
                    "require_manual": True,
                }
            ),
            404,
        )


# Rota para obter modelos de carros para autocomplete
@parking_bp.route("/modelos_carros", methods=["GET"])
@login_required
def get_car_models():
    models = Vehicle.get_car_models()
    return jsonify(models)


# Rota para obter modelos de motos para autocomplete
@parking_bp.route("/modelos_motos", methods=["GET"])
@login_required
def get_motorcycle_models():
    models = Vehicle.get_motorcycle_models()
    return jsonify(models)


# Rota para obter cores disponíveis para autocomplete
@parking_bp.route("/cores_disponiveis", methods=["GET"])
@login_required
def get_available_colors():
    colors = Vehicle.get_available_colors()
    return jsonify(colors)


# Rota para obter placas registradas para autocomplete
@parking_bp.route("/placas_registradas", methods=["GET"])
@login_required
def get_registered_plates():
    plates = Vehicle.get_registered_plates()
    return jsonify(plates)


# Rota para atualizar as listas de modelos e cores (recarregar arquivos JSON)
@parking_bp.route("/atualizar_dados", methods=["POST"])
@login_required
@admin_required
def refresh_data():
    vehicle_data.refresh_data()
    flash("Dados de veículos atualizados com sucesso!", "success")
    return redirect(url_for("parking.register_entry"))
