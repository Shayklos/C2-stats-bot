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
        fs = ' {} took {} seconds.'

        #Get time now
        datetime_Spain = datetime.now(tz)
        moment = datetime_Spain.strftime("[%Y-%m-%d] [%H:%M:%S]")
        log_output = moment + fs.format(func.__name__, (end - start)) + '\n'
        print(log_output, end='')
        with open('files/log.txt', 'a', newline='\n') as file:
              file.write(log_output)      
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


def log(string):
    log_output = moment() + ' ' + string + '\n'
    print(log_output, end='')
    with open('files/log.txt', 'a', newline='\n', encoding="utf-8") as file:
            file.write(log_output)
