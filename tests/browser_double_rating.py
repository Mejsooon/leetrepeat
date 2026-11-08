"""Scenariusz przeglądarki (uruchamiany ręcznie, wymaga Chrome + playwright):
szybkie naciśnięcie 1 i 3 zapisuje tylko jedną ocenę.
Użycie: LEETREPEAT_DB=/tmp/race.db python main.py  (w innym oknie), potem:
        python tests/browser_double_rating.py /tmp/race.db"""
import asyncio
import sqlite3
import sys

from playwright.async_api import async_playwright

db = sys.argv[1]


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path="/usr/bin/google-chrome")
        page = await browser.new_page()
        await page.goto("http://127.0.0.1:8000/task.html?session=python")
        await page.wait_for_timeout(2000)
        await page.click("#title")
        await page.keyboard.press("1")
        await page.keyboard.press("3")
        await page.wait_for_timeout(800)
        await browser.close()
    rows = sqlite3.connect(db).execute("SELECT rating FROM reviews").fetchall()
    print("reviews:", rows)
    assert len(rows) == 1, "zapisano więcej niż jedną ocenę"
    print("OK")

asyncio.run(main())
