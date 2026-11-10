import asyncio
import os
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    InlineQuery, 
    InlineQueryResultArticle, 
    InputTextMessageContent, 
    CallbackQuery, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)
from aiohttp import web

# ---------------------------------------------------------
# ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ (Берутся из настроек Render)
# ---------------------------------------------------------
TOKEN = os.getenv("BOT_TOKEN")
# Render автоматически назначает PORT, мы просто его читаем
PORT = int(os.getenv("PORT", 10000)) 

if not TOKEN:
    raise ValueError("ОШИБКА: BOT_TOKEN не найден в переменных окружения!")

# Инициализация
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

# ---------------------------------------------------------
# ЛОГИКА INLINE РЕЖИМА (via @PisumMiniGamesBot)
# ---------------------------------------------------------
@router.inline_query(F.query.startswith("@"))
async def inline_game_request(inline_query: InlineQuery):
    # Достаем юзернейм противника
    target_username = inline_query.query.strip().replace("@", "")
    challenger = inline_query.from_user

    # Кнопка для старта. В callback_data прячем кто кого вызвал
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"🎮 Принять вызов от {challenger.first_name}", 
            callback_data=f"start_gm:{target_username}:{challenger.id}"
        )]
    ])

    # То, что всплывет над клавиатурой, когда ты напишешь ник бота
    result = InlineQueryResultArticle(
        id="game_req_1",
        title=f"Бросить вызов @{target_username}",
        description="Отправить приглашение на 1v1 игру",
        input_message_content=InputTextMessageContent(
            message_text=f"⚔️ <b>{challenger.first_name}</b> вызывает <b>@{target_username}</b> на дуэль!\n\n<i>Ожидание противника...</i>",
            parse_mode="HTML"
        ),
        reply_markup=kb
    )
    
    await inline_query.answer([result], cache_time=1, is_personal=True)

# ---------------------------------------------------------
# ЛОГИКА КНОПОК И ВИДЖЕТОВ
# ---------------------------------------------------------
@router.callback_query(F.data.startswith("start_gm:"))
async def process_game_accept(callback: CallbackQuery):
    data = callback.data.split(":")
    target_username = data[1]
    
    clicker_username = callback.from_user.username

    # Защита от чужих кликов (Эфемерное сообщение)
    if clicker_username != target_username:
        await callback.answer("❌ Этот вызов не для тебя!", show_alert=True)
        return

    # Запуск игры (API 10.4 HTML-виджет)
    await callback.answer("Игра началась!")
    
    html_widget_ui = f"""
    <widget>
        <h2>Крестики-Нолики 1v1</h2>
        <div class="board" style="display: grid; grid-template-columns: repeat(3, 1fr);">
            <button id="cell_1">-</button>
            <button id="cell_2">-</button>
            <button id="cell_3">-</button>
        </div>
        <p>Ход: <b>@{clicker_username}</b></p>
    </widget>
    """

    await callback.message.edit_text(
        text=f"🎮 <b>Дуэль началась!</b>\n\n{html_widget_ui}",
        parse_mode="HTML"
    )

# ---------------------------------------------------------
# ВЕБ-СЕРВЕР ДЛЯ RENDER (Чтобы бот не падал с ошибкой порта)
# ---------------------------------------------------------
async def health_check(request):
    return web.Response(text="Бот успешно работает!")

async def main():
    dp.include_router(router)
    
    # 1. Запускаем бота (он слушает Telegram)
    asyncio.create_task(dp.start_polling(bot))
    
    # 2. Запускаем заглушку-сервер (он слушает Render)
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    print(f"Сервер запущен на порту {PORT}. Бот работает.")
    await site.start()
    
    # Бесконечный цикл поддержания работы
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    asyncio.run(main())
