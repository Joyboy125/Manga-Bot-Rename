import os

env_vars = {
  # Get From my.telegram.org
  "API_HASH": "f757ca005f4a320bcea5ced947bbff5e",
  # Get From my.telegram.org
  "API_ID": "27011028",
  #Get For @BotFather
  
  # zoro bot = 7505997121:AAFgGywTfb2-BYIqaRUPTd2W4RJNIn7bHK4
  "BOT_TOKEN": "7505997121:AAFgGywTfb2-BYIqaRUPTd2W4RJNIn7bHK4", # joy boy bot = 7250357906:AAEXZ9nIHLmASZ909wJLCBwadBCiO9xTRD8 

  # Get For tembo.io
  "DATABASE_URL_PRIMARY": "postgresql://postgres:k0edUULYD0G6vZy0@fruitfully-legitimate-lemur.data-1.use1.tembo.io:5432/postgres",
  # Logs Channel Username Without @
  "CACHE_CHANNEL": "",
  # Force Subs Channel username without @
  "CHANNEL": "Manhwa_University",
  # {chap_num}: Chapter Number
  # {chap_name} : Manga Name
  # Ex : Chapter {chap_num} {chap_name} @Manhwa_Arena
  "FNAME": "{chap_num}. {chap_name}"
}

username = "mojawatjay26"
password = "DMSZJakoTKDqZyYD"
db_name = "updatebot"
collection_name = "Channels"
USER = 1355560957


DB_URL  = os.environ.get("DB_URL","mongodb+srv://mojawatjay26:DMSZJakoTKDqZyYD@updatebot.qk2u8.mongodb.net/?retryWrites=true&w=majority&appName=updatebot")

dbname = env_vars.get('DATABASE_URL_PRIMARY') or env_vars.get('DATABASE_URL') or 'sqlite:///test.db'

if dbname.startswith('postgres://'):
    dbname = dbname.replace('postgres://', 'postgresql://', 1)
    
