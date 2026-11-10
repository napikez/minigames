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
# ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ
# ---------------------------------------------------------
TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000)) 

if not TOKEN:
    raise ValueError("ОШИБКА: BOT_TOKEN не найден в переменных окружения!")

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

# ---------------------------------------------------------
# СПИСОК ДОСТУПНЫХ МИНИ-ИГР
# ---------------------------------------------------------
GAMES = {
    "ttt": {
        "name": "Крестики-Нолики", 
        "desc": "Классика 3х3 на HTML-виджете", 
        "emoji": "❌⭕"
    },
    "rps": {
        "name": "Камень, Ножницы, Бумага", 
        "desc": "Угадай, что выберет друг", 
        "emoji": "✊✌️✋"
    },
    "dice": {
        "name": "Кубики", 
        "desc": "У кого выпадет больше", 
        "emoji": "🎲"
    }
}

# ---------------------------------------------------------
# ЛОГИКА INLINE РЕЖИМА (via)
# ---------------------------------------------------------
@router.inline_query(F.query.startswith("@"))
async def inline_game_request(inline_query: InlineQuery):
    target_username = inline_query.query.strip().replace("@", "")
    challenger = inline_query.from_user

    # Если юзернейм еще не ввели (или ввели только @), ничего не показываем
    if not target_username:
        return

    results = []
    
    # Перебираем все игры из словаря и создаем для каждой пункт меню
    for game_id, game_info in GAMES.items():
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"🎮 Принять вызов ({game_info['name']})", 
                # Передаем game_id в callback_data, чтобы знать, во что играем
                callback_data=f"start_gm:{game_id}:{target_username}:{challenger.id}"
            )]
        ])

        results.append(
            InlineQueryResultArticle(
                id=f"req_{game_id}",
                title=f"{game_info['emoji']} {game_info['name']}",
                description=f"{game_info['desc']} (против @{target_username})",
                input_message_content=InputTextMessageContent(
                    message_text=f"⚔️ <b>{challenger.first_name}</b> вызывает <b>@{target_username}</b> сыграть в <b>{game_info['name']}</b>!\n\n<i>Ожидание противника...</i>",
                    parse_mode="HTML"
                ),
                reply_markup=kb
            )
        )
    
    # Отправляем список игр в Telegram (появятся над полем ввода)
    await inline_query.answer(results, cache_time=1, is_personal=True)

# ---------------------------------------------------------
# ЛОГИКА КНОПОК И ВИДЖЕТОВ
# ---------------------------------------------------------
@router.callback_query(F.data.startswith("start_gm:"))
async def process_game_accept(callback: CallbackQuery):
    # Разбираем callback_data (теперь там 4 элемента)
    data = callback.data.split(":")
    action = data[0]
    game_id = data[1]
    target_username = data[2]
    challenger_id = data[3]
    
    clicker_username = callback.from_user.username

    # Защита от чужих кликов (Эфемерное сообщение)
    if clicker_username != target_username:
        await callback.answer("❌ Этот вызов не для тебя!", show_alert=True)
        return

    await callback.answer("Игра началась!")
    
    # Генерация UI в зависимости от того, какую игру выбрали в меню
    game_name = GAMES[game_id]["name"]
    
    if game_id == "ttt":
        html_widget_ui = f"""
        <widget>
            <h2>{game_name} 1v1</h2>
            <div class="board" style="display: grid; grid-template-columns: repeat(3, 1fr);">
                <button id="c1">-</button> <button id="c2">-</button> <button id="c3">-</button>
                <button id="c4">-</button> <button id="c5">-</button> <button id="c6">-</button>
                <button id="c7">-</button> <button id="c8">-</button> <button id="c9">-</button>
            </div>
            <p>Ход: <b>@{clicker_username}</b></p>
        </widget>
        """
    elif game_id == "rps":
        html_widget_ui = f"""
        <widget>
            <h2>{game_name} 1v1</h2>
            <div class="buttons">
                <button id="rock">✊ Камень</button>
                <button id="scissors">✌️ Ножницы</button>
                <button id="paper">✋ Бумага</button>
            </div>
            <p>Выбор делает: <b>@{clicker_username}</b></p>
        </widget>
        """
    else:
        # Для кубиков или других игр
        html_widget_ui = f"""
        <widget>
            <h2>{game_name} 1v1</h2>
            <button id="roll">🎲 Бросить кубик</button>
        </widget>
        """

    await callback.message.edit_text(
        text=f"🎮 <b>Дуэль началась!</b>\n\n{html_widget_ui}",
        parse_mode="HTML"
    )

# ---------------------------------------------------------
# ВЕБ-СЕРВЕР ДЛЯ RENDER
# ---------------------------------------------------------
async def health_check(request):
    return web.Response(text="Бот успешно работает!")

async def main():
    dp.include_router(router)
    
    await bot.delete_webhook(drop_pending_updates=True)
    
    asyncio.create_task(dp.start_polling(bot))
    
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    print(f"Сервер запущен на порту {PORT}. Бот работает.")
    await site.start()
    
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    asyncio.run(main())
