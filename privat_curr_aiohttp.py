import asyncio
from datetime import date, datetime, timedelta
import logging
import platform

import aiohttp
import argparse


def datestring(string):
    if len(string) != 10:
        print('Дата повинна бути у форматі dd.mm.yyyy')
        exit()
    else:
        str = string[:2] + '.' + string[3:5] + '.' + string[6:]
    return str


def list_dates(date, nums) -> list:
    dates = [date]
    date_d = datetime.strptime(date, '%d.%m.%Y')
    while nums != 1:
        date_d -= timedelta(1)
        date_s = date_d.strftime('%d.%m.%Y')
        dates.append(date_s)
        nums -= 1
    return dates


def data_adapter(data):
    datas = {}
    for cur in data:
        if cur:
            datas[cur['date']] = [{f"{el.get('currency')}": {"NBU": float(el.get('purchaseRateNB')), "buy": float(
                el.get('purchaseRate', 0.0)), "sale": float(el.get('saleRate', 0.0))}} for el in cur['exchangeRate']]
        else:
            logging.error('Не має данних')
            datas['01.01.1900'] = [
                {"Currency": {"NBU": None, "buy": None, "sale": None}}]
    return datas


def pretty_view(data):
    for date in sorted(data.keys()):
        pattern = '|{:^10}|{:^10}|{:^10}|{:^10}|'
        print(f'  Курс валют від Приват Банку на {date} ')
        print(' -------------------------------------------')
        print(pattern.format('Currency', 'NBU', 'Sale', 'Buy'))
        for el in data[date]:
            currency, *_ = el.keys()
            if currency in currencies:
                nbu = el.get(currency).get('NBU')
                buy = el.get(currency).get('buy')
                sale = el.get(currency).get('sale')
                print(pattern.format(currency, nbu, sale, buy))
        print(' -------------------------------------------\n')


async def days_get(session, date):
    url = 'https://api.privatbank.ua/p24api/exchange_rates?json&date='+date
    async with session.get(url) as response:
        try:
            if response.status == 200:
                result = await response.json()
                return result
            logging.error(f'Error status {response.status} for {url}')
        except aiohttp.ClientConnectionError() as e:
            logging.error(f'Connection error {url} as {e}')
        return None


async def request(dates):
    async with aiohttp.ClientSession() as session:
        urls = []
        for date in dates:
            # создаем задачи
            url = days_get(session, date)
            # складываем задачи в список
            urls.append(url)

        # планируем одновременные вызовы
        result = await asyncio.gather(*urls, return_exceptions=True)
        return result if result else ''

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Currency rate from NBU and Privat Bank')
    parser.add_argument('-d', '--date', required=True, type=datestring,
                        help='currency on date')
    parser.add_argument('-n', '--nums', default=1, type=int,
                        help='get currencies for "nums" day from date, by default=1')
    parser.add_argument('-c', '--currency', default=['EUR', 'USD'], action='extend', nargs='+',
                        help='list of added currencies separated by space, by dafault EUR, USD')
    parser.parse_args()
    args = vars(parser.parse_args())
    date = args.get('date')
    num_days = args.get('nums')
    if num_days > 10:
        print('Запит на курс валют може бути не більше ніж на 10 днів')
        exit()
    currencies = args.get('currency')
    currencies = [c.upper() for c in currencies]

    dates = list_dates(date, num_days)

    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    r = asyncio.run(request(dates))
    # обрабатываем и выводим результат
    res = data_adapter(r)
    if res:
        pretty_view(res)
    else:
        logging.error('Не корректний формат запросу.')
