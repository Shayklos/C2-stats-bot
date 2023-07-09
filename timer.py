import time
from functools import wraps
from datetime import datetime
import pytz


# Timezone
tz = pytz.timezone('UTC') 


def log_time(func):

    @wraps(func)  # improves debugging
    def wrapper(*arg):
        start = time.perf_counter()  # needs python3.3 or higher
        result = func(*arg)
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
    with open('files/log.txt', 'a', newline='\n') as file:
            file.write(log_output)
