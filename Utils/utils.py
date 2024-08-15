from Config import lc


def valid_number(text):
    try:
        int(float(text))
        return True
    except ValueError:
        return False


async def valid_time(user_time):
    try:
        hours, minutes = user_time.split(":")
        if hours.isdigit() and minutes.isdigit():
            hours = int(hours)
            minutes = int(minutes)
            if 0 <= hours <= 23 and 0 <= minutes <= 59:
                return f'{hours:02}:{minutes:02}'
            else:
                return False
        else:
            return False
    except ValueError:
        return False
