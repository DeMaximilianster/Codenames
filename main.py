from random import choice, shuffle
from typing import Dict, Optional, List
import asyncio
from json import load

from aiogram import Dispatcher, Bot, types
from words import WORDS

with open("tokens.json", encoding="utf-8") as FILE:
    TOKEN = load(FILE)["telegram"][0]

BOT = Bot(TOKEN)
DP = Dispatcher(BOT)
GRID_EMOJIS_TO_CODES = {"🟦": "blue", "🟥": "red", "👹": "killer", "😐": "neutral"}
GRID_CODES_TO_EMOJIS = {"blue": "🟦", "red": "🟥", "killer": "👹", "neutral": "😐"}
WORDS_IN_GAME = 24
COLUMNS_IN_GAME = 3
ROWS_IN_GAME = 8
BLUE_HINT = "Сейчас ход синих. Синий капитан, дайте подсказку и количество слов, которые подходят к вашей подсказке," \
            "Например 'Зелёный, 4'. Синяя команда, обсудите какие, как вам кажется, слова относятся к этой" \
            " подсказке и нажмите на них. После чего окончите ход"
RED_HINT = "Сейчас ход красных. Красный капитан, дайте подсказку и количество слов, которые подходят к вашей подсказке," \
           "Например 'Фрукт, 2'. Красная команда, обсудите какие, как вам кажется, слова относятся к этой" \
           " подсказке и нажмите на них. После чего окончите ход"
HELP_STRING = "Игровое поле представляет собой поле 3х8 из некоторых слов. Каждое слово является либо синим агентом "\
              "(🟦), либо красным агентом (🟥), либо прохожим (😐), либо убийцей (👹). Капитаны знают, какое слово " \
              "чем является, остальные участники не знают. Задача капитанов — " \
              "в свой ход давать подсказки своей команде чтоб " \
              "они разгадывали агентов своего цвета. Подсказка должна быть одним словом. Если игрок выбрал " \
              "агента своего цвета, то ход продолжается. " \
              "Если выбран прохожий или агент противника, ход прекращается. Если выбран убийца, то команда " \
              "сразу проигрывает"


class Player:
    def __init__(self, user: types.User):
        self.user_id = user.id
        self.name = user.full_name


class Team:
    def __init__(self):
        self.players: Dict[int, Player] = dict()
        self.captain: Optional[Player] = None

    def add_player(self, user: types.User):
        self.players[user.id] = Player(user)

    def in_team(self, user_id: int) -> bool:
        return user_id in self.players.keys()

    def is_captain(self, user_id: int) -> bool:
        return user_id == self.captain.user_id

    def delete_player(self, user_id: int):
        self.players.pop(user_id)

    def choose_captain(self) -> Player:
        self.captain = choice(list(self.players.values()))
        return self.captain

    def __len__(self):
        return len(self.players)


class Game:
    def __init__(self, chat: types.Chat):
        self.is_finished = False
        self.chat_id: int = chat.id
        self.lobby_message: Optional[types.Message] = None
        self.blue_players = Team()
        self.red_players = Team()
        self.words: List[str] = []
        self.grid: List[str] = []
        self.text_grid: List[str] = []
        self.keyboard = types.InlineKeyboardMarkup(row_width=COLUMNS_IN_GAME)
        self.blue_to_win = 8
        self.red_to_win = 8
        self.blue_points = 0
        self.red_points = 0
        self.current_team = Team()
        self.last_message: types.Message = types.Message()
        self.blue_map: types.Message = types.Message()
        self.red_map: types.Message = types.Message()

    def join_blue(self, user: types.User):
        self.blue_players.add_player(user)
        if self.red_players.in_team(user.id):
            self.red_players.delete_player(user.id)

    def join_red(self, user: types.User):
        self.red_players.add_player(user)
        if self.blue_players.in_team(user.id):
            self.blue_players.delete_player(user.id)

    def is_start_possible(self) -> bool:
        return len(self.blue_players) >= 2 and len(self.red_players) >= 2

    def create_words(self):
        words = list(WORDS)
        shuffle(words)
        words = words[:WORDS_IN_GAME]
        self.words = words

    def update_keyboard(self):
        self.keyboard = types.InlineKeyboardMarkup(row_width=COLUMNS_IN_GAME)
        for i in range(WORDS_IN_GAME):
            callback = GRID_EMOJIS_TO_CODES[self.words[i]] if self.words[i] in GRID_EMOJIS_TO_CODES else f"{i}"
            self.keyboard.insert(types.InlineKeyboardButton(self.words[i], callback_data=callback))
        self.keyboard.insert(types.InlineKeyboardButton("Закончить ход", callback_data="end_turn"))

    async def new_turn(self):
        self.update_keyboard()
        text = BLUE_HINT if self.current_team == self.blue_players else RED_HINT
        self.last_message = await BOT.send_message(self.chat_id, text, reply_markup=self.keyboard)

    async def end_turn(self):
        await asyncio.sleep(1)
        await self.last_message.edit_reply_markup()
        self.current_team = self.blue_players if self.current_team == self.red_players else self.red_players
        await self.new_turn()

    async def end_game(self):
        self.is_finished = True
        GAME_MANAGER.delete_game(self.chat_id)

    async def victory_check(self) -> bool:
        if self.blue_points == self.blue_to_win:
            await BOT.send_message(self.chat_id, "Все синие агенты найдены. Синяя команда победила!")
            await self.end_game()
            return True
        elif self.red_points == self.red_to_win:
            await BOT.send_message(self.chat_id, "Все красные агенты найдены. Красная команда победила!")
            await self.end_game()
            return True
        return False

    async def word_chosen(self, user: types.User, index: int):
        text = ""
        name = user.first_name
        chosen = self.grid[index]
        agent_name = self.words[index]
        self.words[index] = GRID_CODES_TO_EMOJIS[chosen]
        self.update_keyboard()
        if chosen == "neutral":
            text = f"Игроком {name} Был выбран прохожий [{agent_name}]. Ход заканчивается досрочно"
            await self.end_turn()
        elif chosen == "killer" and self.current_team == self.blue_players:
            text = f"Синяя команда ({name}) наткнулась на убийцу [{agent_name}]. Игра завершена победой красной команды"
            await self.end_game()
        elif chosen == "killer":
            text = f"Красная команда ({name}) наткнулась на убийцу [{agent_name}]. Игра завершена победой синей команды"
            await self.end_game()
        elif chosen == "blue" and self.current_team == self.red_players:
            text = f"Красная команда ({name}) наткнулась на синего агента [{agent_name}]. Ход заканчивается досрочно"
            self.blue_points += 1
            if not await self.victory_check():
                await self.end_turn()
        elif chosen == "red" and self.current_team == self.blue_players:
            text = f"Синяя команда ({name}) наткнулась на красного агента [{agent_name}]. Ход заканчивается досрочно"
            self.red_points += 1
            if not await self.victory_check():
                await self.end_turn()
        elif chosen == "blue" and self.current_team == self.blue_players:
            text = f"Синяя команда ({name}) наткнулась на своего агента [{agent_name}]. Ход продолжается"
            self.blue_points += 1
            await self.victory_check()
        elif chosen == "red" and self.current_team == self.red_players:
            text = f"Красная команда ({name}) наткнулась на своего агента [{agent_name}]. Ход продолжается"
            self.red_points += 1
            await self.victory_check()
        else:
            Exception()
        self.text_grid[index] = "✅"
        await self.update_maps()
        await BOT.send_message(self.chat_id, text)

    def get_grid_keyboard(self):
        buttons = [types.InlineKeyboardButton(text, callback_data="boop") for text in self.text_grid]
        buttons_rows = list([buttons[i:i + COLUMNS_IN_GAME] for i in range(0, len(buttons), COLUMNS_IN_GAME)])
        keyboard = types.InlineKeyboardMarkup(row_width=COLUMNS_IN_GAME)
        for buttons_row in buttons_rows:
            keyboard.add(*buttons_row)
        return keyboard

    async def send_maps_to_captains(self):
        keyboard = self.get_grid_keyboard()
        self.blue_map = await BOT.send_message(self.blue_players.captain.user_id,
                                               "Вы капитан синей команды. Вот ваша СЕКРЕТНАЯ карта:",
                                               reply_markup=keyboard)
        self.red_map = await BOT.send_message(self.red_players.captain.user_id,
                                              "Вы капитан красной команды. Вот ваша СЕКРЕТНАЯ карта:",
                                              reply_markup=keyboard)

    async def update_maps(self):
        keyboard = self.get_grid_keyboard()
        await self.blue_map.edit_reply_markup(keyboard)
        await self.red_map.edit_reply_markup(keyboard)

    async def form_lobby_text(self):
        text = 'Игра создана! Жмите кнопки ниже чтобы присоединиться\n\n'
        text += f'🔵Синяя команда: {",".join([player[1].name for player in self.blue_players.players.items()])}\n'
        text += f'🔴Красная команда: {",".join([player[1].name for player in self.red_players.players.items()])}\n'
        return text

    async def start_game(self):
        self.create_words()
        if choice(["blue", "red"]) == "blue":
            self.grid = ["blue"]*9 + ["red"]*8 + ["killer"] + ["neutral"]*(WORDS_IN_GAME-18)
            self.blue_to_win = 9
            self.current_team = self.blue_players
        else:
            self.grid = ["blue"]*8 + ["red"]*9 + ["killer"] + ["neutral"]*(WORDS_IN_GAME-18)
            self.red_to_win = 9
            self.current_team = self.red_players
        shuffle(self.grid)
        self.text_grid = [f"{GRID_CODES_TO_EMOJIS[self.grid[i]]}{self.words[i]}" for i in range(WORDS_IN_GAME)]
        self.blue_players.choose_captain()
        self.red_players.choose_captain()
        await self.send_maps_to_captains()
        self.update_keyboard()


class GameManager:
    def __init__(self):
        self.is_active = True
        self.games: Dict[int, Game] = dict()

    def new_game(self, chat: types.Chat) -> Game:
        self.games[chat.id] = Game(chat)
        return self.games[chat.id]

    def get_game(self, chat_id: int) -> Game:
        return self.games[chat_id]

    def delete_game(self, chat_id: int):
        self.games.pop(chat_id)

    async def delete_finished_games(self):
        while self.is_active:
            await asyncio.sleep(5)
            new_dict = self.games.copy()
            for game in self.games.values():
                if game.is_finished:
                    new_dict.pop(game.chat_id)
            self.games = new_dict.copy()


GAME_MANAGER = GameManager()


@DP.message_handler(commands=["start"])
async def hello_handler(message: types.Message):
    await message.reply("Hello!")


@DP.message_handler(commands=["help"])
async def help_handler(message: types.Message):
    await message.reply(HELP_STRING)


@DP.message_handler(commands=["new_game", "create_game"])
async def new_game_handler(message: types.Message):
    game = GAME_MANAGER.new_game(message.chat)
    text = "Игра создана! Жмите кнопки ниже чтобы присоединиться"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.insert(types.InlineKeyboardButton("Зайти за синих", callback_data="join_blue"))
    keyboard.add(types.InlineKeyboardButton("Зайти за красных", callback_data="join_red"))
    game.lobby_message = await message.reply(text, reply_markup=keyboard)


@DP.callback_query_handler(lambda call: call.data == "join_blue")
async def join_blue_handler(call: types.CallbackQuery):
    game = GAME_MANAGER.get_game(call.message.chat.id)
    game.join_blue(call.from_user)
    await call.answer()
    await BOT.send_message(game.chat_id, f"{call.from_user.first_name} теперь в синей команде")
    keyboard = types.InlineKeyboardMarkup()
    keyboard.insert(types.InlineKeyboardButton("Зайти за синих", callback_data="join_blue"))
    keyboard.add(types.InlineKeyboardButton("Зайти за красных", callback_data="join_red"))
    await BOT.edit_message_text(await game.form_lobby_text(), game.chat_id,
                                game.lobby_message.message_id, reply_markup=keyboard)


@DP.callback_query_handler(lambda call: call.data == "join_red")
async def join_red_handler(call: types.CallbackQuery):
    game = GAME_MANAGER.get_game(call.message.chat.id)
    game.join_red(call.from_user)
    await call.answer()
    await BOT.send_message(game.chat_id, f"{call.from_user.first_name} теперь в красной команде")
    keyboard = types.InlineKeyboardMarkup()
    keyboard.insert(types.InlineKeyboardButton("Зайти за синих", callback_data="join_blue"))
    keyboard.add(types.InlineKeyboardButton("Зайти за красных", callback_data="join_red"))
    await BOT.edit_message_text(await game.form_lobby_text(), game.chat_id,
                                game.lobby_message.message_id, reply_markup=keyboard)


@DP.message_handler(commands=["start_game"])
async def start_game_handler(message: types.Message):
    game = GAME_MANAGER.get_game(message.chat.id)
    if game.is_start_possible():
        await game.start_game()
        await game.new_turn()


@DP.callback_query_handler(lambda call: call.data.isdigit())
async def button_pressed_handler(call: types.CallbackQuery):
    game = GAME_MANAGER.get_game(call.message.chat.id)
    if game.current_team.is_captain(call.from_user.id):
        await call.answer("Капитанам не положено жмакать")
    elif game.current_team.in_team(call.from_user.id):
        await game.word_chosen(call.from_user, int(call.data))
        await call.answer("Засчитано")
        await game.last_message.edit_reply_markup(game.keyboard)
    else:
        await call.answer("Сейчас не твой ход!")


@DP.callback_query_handler(lambda call: call.data == "end_turn")
async def end_turn_handler(call: types.CallbackQuery):
    game = GAME_MANAGER.get_game(call.message.chat.id)
    if game.current_team.is_captain(call.from_user.id):
        await call.answer("Капитанам не положено жмакать")
    elif game.current_team.in_team(call.from_user.id):
        await BOT.send_message(call.message.chat.id, "Была нажата кнопка конца хода. Переходим ко следующему ходу")
        await game.end_turn()
        await call.answer()
    else:
        await call.answer("Сейчас не твой ход!")


async def main():
    await asyncio.gather(asyncio.create_task(DP.start_polling()),
                         asyncio.create_task(GAME_MANAGER.delete_finished_games()))

if __name__ == "__main__":
    asyncio.run(main())

