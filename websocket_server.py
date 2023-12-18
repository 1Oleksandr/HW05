import asyncio
from datetime import datetime
import logging
import websockets
from websockets import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosedOK

from aiopath import AsyncPath
from aiofile import async_open
import names

from privat_curr_aiohttp import request, list_dates, data_adapter

logging.basicConfig(level=logging.INFO)


def parse_message(message: str):

    list_data = message.split(' ')
    date_ = list_data[1]
    if len(date_) != 10:
        return 'Дата повинна бути у форматі dd.mm.yyyy', 1000
    else:
        date = date_[:2] + '.' + date_[3:5] + '.' + date_[6:]
    try:
        num_days = int(list_data[2])
        if num_days > 10:
            return 'Кількість днів не повинна бути більше ніж 10.', 1000
    except:
        num_days = 1
    return date, num_days


class Server:
    clients = set()

    async def register(self, ws: WebSocketServerProtocol):
        ws.name = names.get_full_name()
        self.clients.add(ws)
        logging.info(f'{ws.remote_address} connects')

    async def unregister(self, ws: WebSocketServerProtocol):
        self.clients.remove(ws)
        logging.info(f'{ws.remote_address} disconnects')

    async def send_to_clients(self, message: str):
        if self.clients:
            [await client.send(message) for client in self.clients]

    async def ws_handler(self, ws: WebSocketServerProtocol):
        await self.register(ws)
        try:
            await self.distrubute(ws)
        except ConnectionClosedOK:
            pass
        finally:
            await self.unregister(ws)

    async def write_start_log(self, apath):
        if await apath.exists():
            async with async_open(apath, 'a') as afp:
                await afp.write(f'Request started at {datetime.now()}\n')
        else:
            async with async_open(apath, 'w') as afp:
                await afp.write(f'Request started at {datetime.now()}\n')

    async def write_end_log(self, apath):
        async with async_open(apath, 'a') as afp:
            await afp.write(f'Request ended at {datetime.now()}\n')

    async def distrubute(self, ws: WebSocketServerProtocol):
        async for message in ws:
            if message.startswith('exchange'):
                date, num_days = parse_message(message)
                if num_days == 1000:
                    mes = date
                    await self.send_to_clients(mes)
                else:
                    dates = list_dates(date, int(num_days))
                    apath = AsyncPath("exchange.log")
                    await self.write_start_log(apath)
                    r = await request(dates)
                    res = data_adapter(r)
                    if res:
                        for date in sorted(res.keys()):
                            mes = f'Курс валют від Приват Банку на {date}: '
                            for el in res[date]:
                                currency, *_ = el.keys()
                                if currency in ['USD', 'EUR']:
                                    nbu = el.get(currency).get('NBU')
                                    buy = el.get(currency).get('buy')
                                    sale = el.get(currency).get('sale')
                                    mes += f'{currency}: NBU: {nbu}, Buy: {buy}, Sale: {sale}   '
                            await self.send_to_clients(mes)
                        await self.write_end_log(apath)
                    else:
                        await self.send_to_clients('Не корректний формат запросу.')
            else:
                await self.send_to_clients(f"{ws.name}: {message}")


async def main():
    server = Server()
    async with websockets.serve(server.ws_handler, 'localhost', 8080):
        await asyncio.Future()  # run forever

if __name__ == '__main__':
    asyncio.run(main())
