GRID_CODES_TO_EMOJIS = {"blue": "🟦", "red": "🟥", "killer": "👹", "neutral": "😐"}
GRID_EMOJIS_TO_CODES = {value: key for key, value in GRID_CODES_TO_EMOJIS.items()}

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