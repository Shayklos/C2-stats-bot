import aiosqlite, asyncio, pytz
from datetime import datetime
from time import perf_counter

tz = pytz.timezone('UTC') 

async def log(db: aiosqlite.Connection, table: str, **kwargs):
    datetime_now = datetime.now(tz)
    date = int(datetime_now.timestamp())
    match table.lower():
        case 'general':
            await db.execute("insert into General values (?, ?, ?, ?)", 
                            (date, kwargs.get('kind'), kwargs.get('value'), kwargs.get('name'))
                            )
            print(f"{datetime_now.strftime('[%Y-%m-%d] [%H:%M:%S]')} ")
        case 'namechanges':
            await db.execute("insert into Namechanges values (?, ?, ?)", 
                            (date, kwargs.get('before'), kwargs.get('after'))
                            )
        case 'times':
            await db.execute("insert into Times values (?, ?, ?)", 
                            (date, kwargs.get('function'), kwargs.get('time'))
                            )
        case 'errors':
            await db.execute("insert into Errors values (?, ?, ?)", 
                            (date, kwargs.get('function'), kwargs.get('error'))
                            )
        case 'discord':
            await db.execute("insert into Discord values (?, ?, ?,  ?, ?)", 
                            (date, kwargs.get('function'), kwargs.get('name'), kwargs.get('display_name'), kwargs.get('command'), kwargs.get('details'))
                            )
                
    await db.commit()


#@d
#def f

# == 

#f = d(f)


#@d(a)
#def f

# == 

#f = d(a)(f)
def log_time(db):
    def log_time_dec(func):
        def wrapper(*arg, **kwargs):
            start = perf_counter()  
            result = func(*arg, **kwargs)
            end = perf_counter()

            print(f'{func.__name__} took {end - start} seconds.', 'files/log_time.txt')  
            # log(db)
            return result
        return wrapper
    return log_time_dec

def async_log_time(func):
    async def wrapper(*arg, **kwargs):
        start = perf_counter()  
        result = await func(*arg, **kwargs)
        end = perf_counter()

        log(f'{func.__name__} took {end - start} seconds.', 'files/log_time.txt')  
        return result
    return wrapper

@log_time(1)
def testfunc(a,b):
    for x in range(100000):
        x*x*x

async def main():
    db = await aiosqlite.connect("files/log.db")
    # await log(db, 'general', kind='Test', value=3, name='Shay')
    testfunc(2,5)



if __name__ == '__main__':
    asyncio.run(main())
    print("bop")