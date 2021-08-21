from discord.ext.commands import Cog
from discord.ext.commands import command
from discord.errors import HTTPException
import tmdbsimple as tmdb
from django.core.validators import URLValidator
from channels import TRAILER_CHANNEL_ID

from ..db import db

LANG = 'en-US'

class Suggestion(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.setTMDBKey()
    
    @command(name="spook_me")
    async def spook_me(self, ctx):
        await ctx.send(f"BOO!")
    
    @command(name="suggest")
    async def suggest(self, ctx, *, message):
        if not self.isUrl(message):               
            search = self.searchTMDB(message)
            try:
                movie = search['results'][0]
            except Exception:
                await ctx.send("The Great Beyond could not find this movie")
                return

        else:
            if 'themoviedb.org' not in message:
                await ctx.send("Good try, but that doesn't lead to The Great Beyond")
                return 
            movie = self.buildMovieObject(message)

        if movie:
            videos = self.getVideos(movie['id'])
            if len(videos['results']) == 0:
                await ctx.send("The Great Beyond could not conjure a preview for this movie")
                return
            for item in videos['results']:
                if 'Trailer' in item['type']:
                    link = 'https://www.youtube.com/watch?v=' + item['key']

                    channel = self.bot.get_channel(TRAILER_CHANNEL_ID)

                    exists = db.record("SELECT TrailerLink FROM movie_suggestions WHERE TrailerLink = ?", link)
                    
                    if exists is not None:
                        await ctx.send("That movie already reached it's final resting place")

                        return

                    db.execute("INSERT INTO movie_suggestions VALUES (?,?,?,?)", movie['title'], link, None, False)

                    await channel.send('https://www.youtube.com/watch?v=' + item['key'])
                    
                    db.execute("UPDATE movie_suggestions SET TrailerId = ? WHERE TrailerLink = ?", channel.last_message_id, link)
                    
                    await ctx.send(f"{movie['title'].capitalize()} has been added to the catacombs")
                    
                    break

    def setTMDBKey(self):
        with open("./lib/bot/tmdb_api.0", "r", encoding="utf-8") as tf:
            self.TMDB_API_KEY = tf.read()
    
    def buildMovieObject(self, message):
        if 'https' in message:
            removed_most_url = message.split("/")[4]
        else:
            removed_most_url = message.split("/")[2]

        movie_id = removed_most_url.split("-")[0]

        movie_title = removed_most_url.split("?")[0].replace("-", " ").replace(movie_id, "").lstrip()

        movie = {"id": movie_id, "title": movie_title}

        return movie

    def isUrl(self, message):
        urlValidator = URLValidator()
        try: 
            urlValidator(message)
            return True
        except Exception:
            return False
            
    def searchTMDB(self, query):
        tmdb.API_KEY = self.TMDB_API_KEY
        while True:
            try:
                search = tmdb.Search()
                return search.movie(query=query)
            except Exception as e:
                print(e)

    def getVideos(self, id):
        tmdb.API_KEY = self.TMDB_API_KEY
        while True:
            try:
                movie = tmdb.Movies(id)
                return movie.videos(language=LANG)
            except Exception as e:
                print(e)
            
    @Cog.listener()
    async def on_ready(self):
        print("suggestion cog ready")

def setup(bot):
    bot.add_cog(Suggestion(bot))