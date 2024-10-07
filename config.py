env_vars = {
  # Get From my.telegram.org
  "API_HASH": "f757ca005f4a320bcea5ced947bbff5e",
  # Get From my.telegram.org
  "API_ID": "27011028",
  #Get For @BotFather
  "BOT_TOKEN": "7505997121:AAFgGywTfb2-BYIqaRUPTd2W4RJNIn7bHK4",
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

dbname = env_vars.get('DATABASE_URL_PRIMARY') or env_vars.get('DATABASE_URL') or 'sqlite:///test.db'

if dbname.startswith('postgres://'):
    dbname = dbname.replace('postgres://', 'postgresql://', 1)
    
