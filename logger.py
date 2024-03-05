import time
from datetime import datetime
import pytz
from os.path import join

# Timezone
tz = pytz.timezone('UTC') 

def move_log_files_to_logs_folder():
    """
    Old bot versions used to have logs on files
    This function moves the logs to files/logs
    """
    from pathlib import Path
    logs_path = Path(join("files","logs"))

    # If files/logs exist, assume that log moving has happened
    if logs_path.exists():
        return
    
    #Create files/log folder
    logs_path.mkdir()

    #Move all text files from files to files/logs, and rename them to remove the 'log_' part 
    files = Path("files").glob("*.txt")
    prefix = 'log_'
    for file in files:
        if prefix in file.name:
            file.rename(join("files","logs", file.name[len(prefix):]))


def log_time(func):
    def wrapper(*arg, **kwargs):
        start = time.perf_counter()  
        result = func(*arg, **kwargs)
        end = time.perf_counter()

        log(f'{func.__name__} took {end - start} seconds.', join('files', 'logs', 'time.txt'))  
        return result
    return wrapper

def async_log_time(func):
    async def wrapper(*arg, **kwargs):
        start = time.perf_counter()  
        result = await func(*arg, **kwargs)
        end = time.perf_counter()

        log(f'{func.__name__} took {end - start} seconds.', join('files', 'logs', 'time.txt'))  
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


def log(string, file = join('files', 'logs', 'general.txt'), consoleLog = True):
    log_output = moment() + ' ' + string + '\n'
    if consoleLog:
        print(log_output, end='')
    with open(file, 'a', newline='\n', encoding="utf-8") as file:
            file.write(log_output)
