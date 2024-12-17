import json
import logging
import requests
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# настройки пользователей
SETTINGS_FILE = 'user_settings.json'


def load_settings():
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_settings(settings):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)


# словарь сообщений на разных языках
MESSAGES = {
    'en': {
        'welcome': "Hello! I am a bot to get information about countries. Choose an option:",
        'country_info': "Enter the name of the country:",
        'settings_prompt': "Enter your preferred language (e.g., en, ru):",
        'language_set_en': "Language set to English.",
        'language_set_ru': "Language set to Russian.",
        'country_not_found': "Country not found. Please try again.",
        'error_occurred': "An error occurred while processing your request.",
        'language_invalid': "Invalid language code. Please enter 'en' or 'ru'.",
        'language_options': [['Country Information', 'Settings']],
        'country_info_option': 'Country Information',
        'settings_option': 'Settings',
        'enter_country_name': "Please enter the name of the country:",
        'enter_language': "Please enter your preferred language (e.g., en, ru):",
        'country_info_response': (
            "**Country:** {name}\n"
            "**Capital:** {capital}\n"
            "**Region:** {region}\n"
            "**Population:** {population}\n"
            "**Languages:** {languages}"
        ),
    },
    'ru': {
        'welcome': "Привет! Я бот для получения информации о странах. Выберите опцию:",
        'country_info': "Введите название страны (на английском языке):",
        'settings_prompt': "Введите предпочитаемый язык (например, en, ru):",
        'language_set_en': "Язык установлен на английский.",
        'language_set_ru': "Язык установлен на русский.",
        'country_not_found': "Страна не найдена. Пожалуйста, попробуйте снова.",
        'error_occurred': "Произошла ошибка при обработке вашего запроса.",
        'language_invalid': "Неверный код языка. Пожалуйста, введите 'en' или 'ru'.",
        'language_options': [['Информация о стране', 'Настройки']],
        'country_info_option': 'Информация о стране',
        'settings_option': 'Настройки',
        'enter_country_name': "Пожалуйста, введите название страны:",
        'enter_language': "Пожалуйста, введите предпочитаемый язык (например, en, ru):",
        'country_info_response': (
            "**Страна:** {name}\n"
            "**Столица:** {capital}\n"
            "**Регион:** {region}\n"
            "**Население:** {population}\n"
            "**Языки:** {languages}"
        ),
    }
}


def get_message(user_lang, key):
    return MESSAGES.get(user_lang, MESSAGES['en']).get(key, '')


# команда /start
async def start(update, context):
    user = update.effective_user
    settings = load_settings()
    if str(user.id) not in settings:
        settings[str(user.id)] = {'language': 'en'}
        save_settings(settings)
    user_lang = settings[str(user.id)].get('language', 'en')

    language_options = MESSAGES[user_lang]['language_options']
    markup = ReplyKeyboardMarkup(language_options, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        get_message(user_lang, 'welcome'),
        reply_markup=markup
    )


# обработка текстовых сообщений
async def handle_message(update, context):
    text = update.message.text.strip()
    user = update.effective_user
    settings = load_settings()
    user_settings = settings.get(str(user.id), {'language': 'en'})
    user_lang = user_settings.get('language', 'en')

    # какая опция выбрана
    if text == MESSAGES[user_lang][
        'country_info_option'].lower() or text.lower() == 'country information' or text.lower() == 'информация о стране':
        await update.message.reply_text(get_message(user_lang, 'enter_country_name'))
        return
    elif text == MESSAGES[user_lang][
        'settings_option'].lower() or text.lower() == 'settings' or text.lower() == 'настройки':
        await update.message.reply_text(get_message(user_lang, 'enter_language'))
        return
    elif len(text) == 2 and text.lower() in ['en', 'ru']:
        # устанавливаем язык
        new_lang = text.lower()
        settings[str(user.id)]['language'] = new_lang
        save_settings(settings)
        if new_lang == 'en':
            response = get_message(new_lang, 'language_set_en')
            language_options = MESSAGES[new_lang]['language_options']
        else:
            response = get_message(new_lang, 'language_set_ru')
            language_options = MESSAGES[new_lang]['language_options']
        markup = ReplyKeyboardMarkup(language_options, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(response, reply_markup=markup)
        return
    else:
        country_name = update.message.text
        try:
            response = requests.get(f'https://restcountries.com/v3.1/name/{country_name}')
            response.raise_for_status()
            data = response.json()[0]
            name = data.get('name', {}).get('common', 'N/A')
            capital = data.get('capital', ['N/A'])[0]
            region = data.get('region', 'N/A')
            population = data.get('population', 'N/A')
            languages = ', '.join(data.get('languages', {}).values()) if data.get('languages') else 'N/A'

            info_template = get_message(user_lang, 'country_info_response')
            info = info_template.format(
                name=name,
                capital=capital,
                region=region,
                population=population,
                languages=languages
            )
            await update.message.reply_text(info, parse_mode='Markdown')
        except requests.exceptions.HTTPError:
            await update.message.reply_text(get_message(user_lang, 'country_not_found'))
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await update.message.reply_text(get_message(user_lang, 'error_occurred'))


# обработчик ошибок
async def error_handler(update, context):
    logger.error(msg="Ошибка:", exc_info=context.error)
    if isinstance(update, Update) and update.message:
        user = update.effective_user
        settings = load_settings()
        user_settings = settings.get(str(user.id), {'language': 'en'})
        user_lang = user_settings.get('language', 'en')
        await update.message.reply_text(get_message(user_lang, 'error_occurred'))


def main():
    TOKEN = '7949867257:AAE8JewrZhOkidRpyo64uqlbdbu4jrlo3XA'

    # создаем приложение
    application = Application.builder().token(TOKEN).build()

    # обработчики команд
    application.add_handler(CommandHandler("start", start))

    # обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # обработчик ошибок
    application.add_error_handler(error_handler)

    application.run_polling()


if __name__ == '__main__':
    main()
