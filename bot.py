import asyncio
import re
from dataclasses import dataclass

import pyrogram.errors
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from img2pdf.core import fld2pdf
from plugins import MangaClient, ManhuaKoClient, MangaCard, MangaChapter, ManhuaPlusClient, TMOClient, MangaDexClient
import os

from pyrogram import Client, filters
from typing import Dict, Tuple, List

from models.db import DB, ChapterFile, Subscription, LastChapter, MangaName
from pagination import Pagination

mangas: Dict[str, MangaCard] = {}
chapters: Dict[str, MangaChapter] = {}
pdfs: Dict[str, str] = {}
paginations: Dict[int, Pagination] = {}
queries: Dict[str, Tuple[MangaClient, str]] = {}
full_pages: Dict[str, List[str]] = {}
favourites: Dict[str, MangaCard] = {}

plugins: Dict[str, MangaClient] = {
    "[EN] MangaDex": MangaDexClient(),
    "[EN] Manhuaplus": ManhuaPlusClient(),
    "[ES] MangaDex": MangaDexClient(language="es-la"),
    "[ES] ManhuaKo": ManhuaKoClient(),
    "[ES] TMO": TMOClient()
}


def split_list(li):
    return [li[x: x+2] for x in range(0, len(li), 2)]


bot = Client('bot',
             api_id=int(os.getenv('API_ID')),
             api_hash=os.getenv('API_HASH'),
             bot_token=os.getenv('BOT_TOKEN'))


@bot.on_message(filters=filters.private)
async def on_message(client, message: Message):
    for identifier, manga_client in plugins.items():
        queries[f"query_{identifier}_{hash(message.text)}"] = (manga_client, message.text)
    await bot.send_message(message.chat.id, "Select search plugin", reply_markup=InlineKeyboardMarkup(
        split_list([InlineKeyboardButton(identifier, callback_data=f"query_{identifier}_{hash(message.text)}")
         for identifier, manga_client in plugins.items()])
    ))


async def plugin_click(client, callback: CallbackQuery):
    manga_client, query = queries[callback.data]
    results = await manga_client.search(query)
    if not results:
        await bot.send_message(callback.from_user.id, "No manga found for given query.")
        return
    for result in results:
        mangas[result.unique()] = result
    await bot.send_message(callback.from_user.id,
                           "This is the result of your search",
                           reply_markup=InlineKeyboardMarkup([
                               [InlineKeyboardButton(result.name, callback_data=result.unique())] for result in results
                           ]))


async def manga_click(client, callback: CallbackQuery, pagination: Pagination = None):
    if pagination is None:
        pagination = Pagination()
        paginations[pagination.id] = pagination

    if pagination.manga is None:
        manga = mangas[callback.data]
        pagination.manga = manga
        
    results = await pagination.manga.client.get_chapters(pagination.manga, pagination.page)

    if not results:
        await callback.answer("Ups, no chapters there.", show_alert=True)
        return

    full_page_key = f'full_page_{hash("".join([result.unique() for result in results]))}'
    full_pages[full_page_key] = []
    for result in results:
        chapters[result.unique()] = result
        full_pages[full_page_key].append(result.unique())

    db = DB()
    subs = await db.get(Subscription, (pagination.manga.url, str(callback.from_user.id)))

    prev = [InlineKeyboardButton('<<', f'{pagination.id}_{pagination.page - 1}')]
    next_ = [InlineKeyboardButton('>>', f'{pagination.id}_{pagination.page + 1}')]
    footer = [prev + next_] if pagination.page > 1 else [next_]

    fav = [[InlineKeyboardButton(
        "Unsubscribe" if subs else "Subscribe",
        f"{'unfav' if subs else 'fav'}_{pagination.manga.unique()}"
    )]]
    favourites[f"fav_{pagination.manga.unique()}"] = pagination.manga
    favourites[f"unfav_{pagination.manga.unique()}"] = pagination.manga

    full_page = [[InlineKeyboardButton('Full Page', full_page_key)]]
    
    buttons = InlineKeyboardMarkup(fav + footer + [
        [InlineKeyboardButton(result.name, result.unique())] for result in results
    ] + full_page + footer)
    
    if pagination.message is None:
        try:
            message = await bot.send_photo(callback.from_user.id,
                                           pagination.manga.picture_url,
                                           f'{pagination.manga.name}\n'
                                           f'{pagination.manga.get_url()}', reply_markup=buttons)
            pagination.message = message
        except pyrogram.errors.BadRequest as e:
            file_name = f'pictures/{pagination.manga.unique()}.jpg'
            await pagination.manga.client.get_url(pagination.manga.picture_url, cache=True, file_name=file_name)
            message = await bot.send_photo(callback.from_user.id,
                                           f'./cache/{pagination.manga.client.name}/{file_name}',
                                           f'{pagination.manga.name}\n'
                                           f'{pagination.manga.get_url()}', reply_markup=buttons)
            pagination.message = message
    else:
        await bot.edit_message_reply_markup(
            callback.from_user.id,
            pagination.message.message_id,
            reply_markup=buttons
        )


async def chapter_click(client, data, chat_id):
    chapter = chapters[data]
    db = DB()
    
    chapterFile: ChapterFile = await db.get(ChapterFile, chapter.url)

    caption = '\n'.join([
        f'{chapter.manga.name} - {chapter.name}',
        f'{chapter.get_url()}'
    ])
    
    if not chapterFile:
        pictures_folder = await chapter.client.download_pictures(chapter)
        pdf = fld2pdf(pictures_folder, f'{chapter.manga.name} - {chapter.name}')
        message = await bot.send_document(chat_id, pdf, caption=caption)
        await db.add(ChapterFile(url=chapter.url, file_id=message.document.file_id))
    else:
        message = await bot.send_document(chat_id, chapterFile.file_id, caption=caption)


async def pagination_click(client: Client, callback: CallbackQuery):
    pagination_id, page = map(int, callback.data.split('_'))
    pagination = paginations[pagination_id]
    pagination.page = page
    await manga_click(client, callback, pagination)


async def full_page_click(client: Client, callback: CallbackQuery):
    chapters_data = full_pages[callback.data]
    for chapter_data in reversed(chapters_data):
        try:
            await chapter_click(client, chapter_data, callback.from_user.id)
        except Exception as e:
            print(e)
        await asyncio.sleep(0.1)


async def favourite_click(client: Client, callback: CallbackQuery):
    action, data = callback.data.split('_')
    fav = action == 'fav'
    manga = favourites[callback.data]
    db = DB()
    subs = await db.get(Subscription, (manga.url, str(callback.from_user.id)))
    if not subs and fav:
        await db.add(Subscription(url=manga.url, user_id=str(callback.from_user.id)))
    if subs and not fav:
        await db.erase(subs)
    if subs and fav:
        await callback.answer("You are already subscribed", show_alert=True)
    if not subs and not fav:
        await callback.answer("You are not subscribed", show_alert=True)
    reply_markup = callback.message.reply_markup
    keyboard = reply_markup.inline_keyboard
    keyboard[0] = [InlineKeyboardButton(
        "Unsubscribe" if fav else "Subscribe",
        f"{'unfav' if fav else 'fav'}_{data}"
    )]
    await bot.edit_message_reply_markup(callback.from_user.id, callback.message.message_id, InlineKeyboardMarkup(keyboard))
    db_manga = await db.get(MangaName, manga.url)
    if not db_manga:
        await db.add(MangaName(url=manga.url, name=manga.name))


def is_pagination_data(callback: CallbackQuery):
    data = callback.data
    match = re.match(r'\d+_\d+', data)
    if not match:
        return False
    pagination_id = int(data.split('_')[0])
    if pagination_id not in paginations:
        return False
    pagination = paginations[pagination_id]
    if pagination.message.chat.id != callback.from_user.id:
        return False
    if pagination.message.message_id != callback.message.message_id:
        return False
    return True


@bot.on_callback_query()
async def on_callback_query(client, callback: CallbackQuery):
    if callback.data in queries:
        await plugin_click(client, callback)
    elif callback.data in mangas:
        await manga_click(client, callback)
    elif callback.data in chapters:
        await chapter_click(client, callback.data, callback.from_user.id)
    elif callback.data in full_pages:
        await full_page_click(client, callback)
    elif callback.data in favourites:
        await favourite_click(client, callback)
    elif is_pagination_data(callback):
        await pagination_click(client, callback)
    else:
        await bot.answer_callback_query(callback.id, 'This is an old button, please redo the search', show_alert=True)
        return
    try:
        await callback.answer()
    except BaseException as e:
        print(e)


async def update_mangas():
    db = DB()
    subscriptions = await db.get_all(Subscription)
    last_chapters = await db.get_all(LastChapter)
    manga_names = await db.get_all(MangaName)

    subs_dictionary = dict()
    chapters_dictionary = dict()
    client_dictionary = dict()
    manga_dict = dict()

    for subscription in subscriptions:
        if subscription.url not in subs_dictionary:
            subs_dictionary[subscription.url] = []
        subs_dictionary[subscription.url].append(subscription.user_id)

    for last_chapter in last_chapters:
        chapters_dictionary[last_chapter.url] = last_chapter

    for manga in manga_names:
        manga_dict[manga.url] = manga

    for url in subs_dictionary:
        for client in plugins.values():
            if await client.contains_url(url):
                client_dictionary[url] = client

    updated = dict()

    for url, client in client_dictionary.items():
        try:
            print(url)
            if url not in manga_dict:
                continue
            manga_name = manga_dict[url].name
            if url not in chapters_dictionary:
                agen = client.iter_chapters(url, manga_name)
                last_chapter = await anext(agen)
                await db.add(LastChapter(url=url, chapter_url=last_chapter.url))
            else:
                last_chapter = chapters_dictionary[url]
                new_chapters: List[MangaChapter] = []
                async for chapter in client.iter_chapters(url, manga_name):
                    if chapter.url == last_chapter.chapter_url:
                        break
                    new_chapters.append(chapter)
                new_chapters = new_chapters[:20]
                if new_chapters:
                    last_chapter.chapter_url = new_chapters[0].url
                    await db.add(last_chapter)
                    updated[url] = list(reversed(new_chapters))
                    for chapter in new_chapters:
                        print(chapter.unique())
                        if chapter.unique() not in chapters:
                            chapters[chapter.unique()] = chapter
        except BaseException as e:
            print(f'An exception occurred getting new chapters: {e}')

    print("got here")

    for url, chapter_list in updated.items():
        for chapter in chapter_list:
            print(f'{chapter.manga.name} - {chapter.name}')
            for sub in subs_dictionary[url]:
                await chapter_click(bot, chapter.unique(), sub)
                await asyncio.sleep(0.1)


async def manga_updater():
    while True:
        print('Waiting 60 seconds')
        await asyncio.sleep(10)
        try:
            print('Updating Mangas')
            await update_mangas()
        except BaseException as e:
            print(f'An exception occurred during chapters update: {e}')
            # raise e
