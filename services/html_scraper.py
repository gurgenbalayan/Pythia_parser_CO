import aiohttp
from bs4 import BeautifulSoup
from utils.logger import setup_logger
import os
from selenium.common import WebDriverException, TimeoutException
from selenium import webdriver
import undetected_chromedriver as uc
from typing import Dict
from dotenv import load_dotenv
load_dotenv()

STATE = os.getenv("STATE")
logger = setup_logger("scraper")

async def get_cookies_from_website(url: str) -> Dict[str, str]:
    cookies_dict = {}
    driver = None
    try:
        options = webdriver.ChromeOptions()
        options.headless = True
        options.page_load_strategy = 'eager'
        driver = uc.Chrome(options=options)
        try:
            driver.get(url)
            cookies_raw = driver.get_cookies()
            cookies_dict = {cookie['name']: cookie['value'] for cookie in cookies_raw}
        except TimeoutException as e:
            logger.error(f"Page load error {url}: {e}")
        except WebDriverException as e:
            logger.error(f"WebDriver error: {e}")
        finally:
            driver.quit()
    except Exception as e:
        logger.error(f"Ошибка при запуске Selenium: {e}")
    return cookies_dict
async def fetch_company_details(url: str) -> dict:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                html = await response.text()
                return await parse_html_details(html)
    except Exception as e:
        logger.error(f"Error fetching data for query '{url}': {e}")
        return []
async def fetch_company_data(query: str) -> list[dict]:
    try:
        url = "https://www.coloradosos.gov/biz/BusinessEntityCriteriaExt.do"
        payload = f'searchName={query}&cmd=Search'
        cookies = await get_cookies_from_website(url)
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        async with aiohttp.ClientSession(cookies=cookies, headers=headers) as session:
            async with session.post(url, data=payload) as response:
                response.raise_for_status()
                html = await response.text()
                return await parse_html_search(html)
    except Exception as e:
        logger.error(f"Error fetching data for query '{query}': {e}")
        return []
async def parse_html_search(html: str) -> list[dict]:
    soup = BeautifulSoup(html, 'html.parser')
    results = []

    # Ищем таблицу с данными о компаниях
    tables = soup.find_all('table')
    for table in tables:
        headers = [th.get_text(strip=True) for th in table.find_all('th')]
        if 'ID Number' in headers and 'Name' in headers:
            rows = table.find_all('tr')[1:]  # Пропускаем заголовок
            for row in rows:
                cols = row.find_all('td')
                if len(cols) == 8:  # Убедимся, что строка действительно содержит все 8 столбцов
                    link_tag = cols[1].find('a')
                    if link_tag:
                        results.append({
                            "state": STATE,
                            "name": cols[3].get_text(strip=True).replace('\xa0', ' '),
                            "status": cols[5].get_text(strip=True).replace('\xa0', ' '),
                            "id": cols[1].get_text(strip=True),
                            "url": 'https://www.coloradosos.gov/biz/' + link_tag['href'].replace('&amp;', '&'),
                        })
            break
    if not results:
        error_list = soup.find_all('li', class_='page_messages')
        if error_list:
            errors = [li.text.strip() for li in error_list if 'Error' in li.text]
            if errors:
                print("Поиск не дал результатов. Ошибки:", errors)
                return []
    return results

async def parse_html_details(html: str) -> dict:
    soup = BeautifulSoup(html, 'html.parser')
    name = soup.find('th', text='Name').find_next('td').get_text()
    entity_type = soup.find('th', text='Form').find_next('td').get_text()
    status = soup.find('th', text='Status').find_next('td').get_text()
    date_registered = soup.find('th', text='Formation date').find_next('td').get_text()
    registration_number = soup.find('th', text='ID number').find_next('td').get_text()
    principal_address = soup.find('th', text='Principal office street address').find_next('td').get_text().strip()
    mailing_address = soup.find('th', text='Principal office mailing address').find_next('td').get_text().strip()
    agent_name = soup.find_all('th', text='Name')[1].find_next('td').get_text()


    #Documents
    document_images = []

    return {
        "state": STATE,
        "name": name,
        "status": status,
        "registration_number": registration_number,
        "date_registered": date_registered,
        "entity_type": entity_type,
        "agent_name": agent_name,
        "principal_address": principal_address,
        "mailing_address": mailing_address,
        "document_images": document_images
    }