# Bot.py - Kerakli Narsa Professional Bot

import os
import json
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import CommandStart
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

DATA_FILE = "content.json"
USER_FILE = "users.json"
SECTIONS = ["Animelar (top 25 ta)", "Kinolar (top 25 ta Eng+Uz tarjimasi bilan)", "Musiqalar (ingilizcha )", "Ingliz tili darslar(Teacher azamniki!)", "Kitoblar (top 25 ta Eng+Uz)"]

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({sec: {} for sec in SECTIONS}, f)

if not os.path.exists(USER_FILE):
    with open(USER_FILE, "w") as f:
        json.dump({}, f)


def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_users():
    with open(USER_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f, indent=2)

@dp.message(CommandStart())
async def start(message: types.Message):
    users = load_users()
    if str(message.from_user.id) not in users:
        users[str(message.from_user.id)] = {
            "username": message.from_user.username,
            "first_name": message.from_user.first_name
        }
        save_users(users)

    kb = InlineKeyboardBuilder()
    for sec in SECTIONS:
        kb.button(text=sec, callback_data=f"view_{sec}")
    kb.button(text="👨‍💻 Admin panel", callback_data="admin")
    await message.answer("O'zingizga Kerakli narsalarni tanlang marxamat:", reply_markup=kb.adjust(1).as_markup())

@dp.callback_query(F.data.startswith("view_"))
async def view_section(callback: types.CallbackQuery):
    sec = callback.data.split("_", 1)[1]
    data = load_data()
    items = data.get(sec, {})
    kb = InlineKeyboardBuilder()
    for k in items:
        kb.button(text=k, callback_data=f"play_{sec}_{k}")
    kb.button(text="🔙 Ortga", callback_data="back")
    await callback.message.edit_text(f"📂 {sec} bo‘limidan tanlang:", reply_markup=kb.adjust(1).as_markup())

@dp.callback_query(F.data.startswith("play_"))
async def play(callback: types.CallbackQuery):
    _, sec, name = callback.data.split("_", 2)
    data = load_data()
    file_id = data[sec][name]["file_id"]
    file_type = data[sec][name]["type"]

    if file_type == "video":
        await callback.message.answer_video(file_id, caption=name)
    elif file_type == "audio":
        await callback.message.answer_audio(file_id, caption=name)
    elif file_type == "document":
        await callback.message.answer_document(file_id, caption=name)
    elif file_type == "photo":
        await callback.message.answer_photo(file_id, caption=name)
    else:
        await callback.message.answer("❗ Nomaʼlum fayl turi")

@dp.callback_query(F.data == "back")
async def go_back(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    for sec in SECTIONS:
        kb.button(text=sec, callback_data=f"view_{sec}")
    kb.button(text="👨‍💻 Admin panel", callback_data="admin")
    await callback.message.edit_text("O'zingizga Kerakli narsalarni tanlang:", reply_markup=kb.adjust(1).as_markup())

@dp.callback_query(F.data == "admin")
async def admin_panel(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("Faqat admin uchun!", show_alert=True)
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Fayl qo‘shish", callback_data="admin_add")
    kb.button(text="✏️ Nomini o‘zgartirish", callback_data="admin_edit")
    kb.button(text="❌ O‘chirish", callback_data="admin_delete")
    kb.button(text="📊 Statistika", callback_data="admin_stat")
    kb.button(text="🔙 Ortga", callback_data="back")
    await callback.message.edit_text("🔧 Admin panel:", reply_markup=kb.adjust(1).as_markup())

@dp.callback_query(F.data == "admin_add")
async def choose_section_to_add(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    kb = InlineKeyboardBuilder()
    for sec in SECTIONS:
        kb.button(text=sec, callback_data=f"addto_{sec}")
    await callback.message.edit_text("Qaysi bo‘limga fayl qo‘shilsin?", reply_markup=kb.adjust(1).as_markup())

add_temp = {}

@dp.callback_query(F.data.startswith("addto_"))
async def ask_name(callback: types.CallbackQuery):
    sec = callback.data.split("_", 1)[1]
    add_temp[callback.from_user.id] = {"section": sec}
    await bot.send_message(callback.from_user.id, "Yangi fayl nomini yuboring:")

@dp.message(F.text)
async def get_name(message: types.Message):
    if message.from_user.id != ADMIN_ID or message.from_user.id not in add_temp:
        return
    add_temp[message.from_user.id]["name"] = message.text
    await message.answer("Endi faylni yuboring (video, audio, rasm yoki document):")

@dp.message(F.video | F.audio | F.document | F.photo)
async def get_file(message: types.Message):
    if message.from_user.id != ADMIN_ID or message.from_user.id not in add_temp:
        return
    temp = add_temp.pop(message.from_user.id)
    sec, name = temp["section"], temp["name"]
    data = load_data()

    if message.video:
        file_id = message.video.file_id
        file_type = "video"
    elif message.audio:
        file_id = message.audio.file_id
        file_type = "audio"
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
    else:
        await message.answer("❗ Noto‘g‘ri fayl turi")
        return

    data[sec][name] = {"file_id": file_id, "type": file_type}
    save_data(data)
    await message.answer(f"✅ {sec} bo‘limiga qo‘shildi: {name}")

@dp.callback_query(F.data == "admin_stat")
async def stat(callback: types.CallbackQuery):
    users = load_users()
    await callback.message.answer(f"👥 Foydalanuvchilar soni: {len(users)} ta")

@dp.callback_query(F.data == "admin_edit")
async def choose_edit_section(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    kb = InlineKeyboardBuilder()
    for sec in SECTIONS:
        kb.button(text=sec, callback_data=f"edit_{sec}")
    await callback.message.edit_text("Qaysi bo‘limdan fayl nomini o‘zgartiramiz?", reply_markup=kb.adjust(1).as_markup())

@dp.callback_query(F.data.startswith("edit_"))
async def select_to_edit(callback: types.CallbackQuery):
    sec = callback.data.split("_", 1)[1]
    data = load_data()
    kb = InlineKeyboardBuilder()
    for name in data[sec]:
        kb.button(text=name, callback_data=f"rename_{sec}_{name}")
    await callback.message.edit_text(f"{sec} bo‘limidan tanlang:", reply_markup=kb.adjust(1).as_markup())

rename_temp = {}

@dp.callback_query(F.data.startswith("rename_"))
async def ask_new_name(callback: types.CallbackQuery):
    _, sec, old = callback.data.split("_", 2)
    rename_temp[callback.from_user.id] = {"section": sec, "old": old}
    await bot.send_message(callback.from_user.id, f"Yangi nom kiriting ({old} uchun):")

@dp.message(F.text)
async def rename_file(message: types.Message):
    if message.from_user.id not in rename_temp:
        return
    t = rename_temp.pop(message.from_user.id)
    data = load_data()
    file_info = data[t["section"].pop(t["old"])]
    data[t["section"]][message.text] = file_info
    save_data(data)
    await message.answer("✅ Nom o‘zgartirildi.")

@dp.callback_query(F.data == "admin_delete")
async def choose_del_section(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    kb = InlineKeyboardBuilder()
    for sec in SECTIONS:
        kb.button(text=sec, callback_data=f"del_{sec}")
    await callback.message.edit_text("Qaysi bo‘limdan o‘chiramiz?", reply_markup=kb.adjust(1).as_markup())

@dp.callback_query(F.data.startswith("del_"))
async def del_file(callback: types.CallbackQuery):
    sec = callback.data.split("_", 1)[1]
    data = load_data()
    kb = InlineKeyboardBuilder()
    for name in data[sec]:
        kb.button(text=f"❌ {name}", callback_data=f"dodel_{sec}_{name}")
    await callback.message.edit_text(f"{sec} bo‘limidan o‘chirish:", reply_markup=kb.adjust(1).as_markup())

@dp.callback_query(F.data.startswith("dodel_"))
async def do_delete(callback: types.CallbackQuery):
    _, sec, name = callback.data.split("_", 2)
    data = load_data()
    if name in data[sec]:
        del data[sec][name]
        save_data(data)
        await callback.message.answer("❌ O‘chirildi.")

if __name__ == '__main__':
    import asyncio
    asyncio.run(dp.start_polling(bot))
