import time
from datetime import datetime
import pytz


# Timezone
tz = pytz.timezone('UTC') 


def log_time(func):
    def wrapper(*arg, **kwargs):
        start = time.perf_counter()  
        result = func(*arg, **kwargs)
        end = time.perf_counter()

        log(f'{func.__name__} took {end - start} seconds.', 'files/log_time.txt')  
        return result
    return wrapper


def moment(filename=False) -> str:
    #Get time now
    datetime_now = datetime.now(tz)
    if filename:
         moment = datetime_now.strftime("[%Y-%m-%d] [%H.%M.%S]")
    else:
         moment = datetime_now.strftime("[%Y-%m-%d] [%H:%M:%S]")
    return moment


def log(string, file = 'files/log_general.txt', consoleLog = True):
    log_output = moment() + ' ' + string + '\n'
    if consoleLog:
        print(log_output, end='')
    with open(file, 'a', newline='\n', encoding="utf-8") as file:
            file.write(log_output)
