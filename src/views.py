from datetime import datetime


def get_greeting(datetime_str: str) -> str:
    """
    Функция принимает строку формата YYYY-MM-DD HH:MM:SS и возвращает приветствие
    в зависимости от текущего времени суток
    :param datetime_str:
    :return:
    """
    try:
        dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return "Доброго времени суток!"

    hour = dt.hour
    if 5 <= hour < 12:
        return "Доброе утро"
    elif 12 <= hour < 18:
        return "Добрый день"
    elif 18 <= hour < 23:
        return "Добрый вечер"
    else:
        return "Доброй ночи"



if __name__ == "__main__":
    print(get_greeting("2021-12-25 15:01:01"))