import traceback
import sys
from os import sep
sys.path.append(f'..{sep}c2-stats-bot-dev')

import sqlite3, aiosqlite, asyncio, aiohttp
from settings import LIVEINFO_URL, BASE_USER_URL, BASE_ROUNDS_URL, ACHIEVEMENTS_URL


class APIResponse:
    def __init__(self, data: dict, status: int):
        self.data = data
        self.status = status

    def has_error(self):
        return self.status > 399 


class Endpoint:
    @classmethod
    async def get_data(cls, url)-> APIResponse:
        try: 
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    data = await response.json()
                    return APIResponse(data, response.status)

        except aiohttp.ClientError as e:
            # This handles network-related issues (like DNS failures, connection errors, etc.)
            return APIResponse({'error':
                {'message': f"Network error: {e}"}
            }, 400)
            
        except asyncio.TimeoutError:
            # This handles request timeouts (if the server takes too long to respond)
            return APIResponse({'error':
                {'message': "Request timed out"}
            }, 400)

        except aiohttp.client_exceptions.ContentTypeError:
            # This handles invalid JSON responses
            return APIResponse({'error':
                {'message': "Invalid JSON response"}
            }, 400)

        except aiohttp.ClientResponseError as e:
            # This handles specific HTTP response errors
            return APIResponse({'error':
                {'message': f"HTTP Error: {e.status} - {e.message}"}
            }, e.status)

        except Exception as e:
            # This will catch any other unexpected errors
            return APIResponse({'error':
                {'message': f"An unexpected error occurred: {e}"}
            }, 400)

    @classmethod
    async def achievements(cls):
        return await Endpoint.get_data(ACHIEVEMENTS_URL)

    @classmethod
    async def user(cls, id):
        return await Endpoint.get_data(BASE_USER_URL + str(id))
        
    @classmethod
    async def liveinfo(cls):
        return await Endpoint.get_data(LIVEINFO_URL)

    @classmethod
    async def rounds(cls, id):
        return await Endpoint.get_data(BASE_ROUNDS_URL + str(id))


if __name__ == '__main__':
    async def main():
        x = await Endpoint.achievements()
        print(x)


    try:
        asyncio.run(main())
    except Exception as e:
        print(traceback.format_exc())
        print("Cancelled")