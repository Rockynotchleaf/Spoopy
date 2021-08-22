from discord.ext.commands import command, Cog
from discord import Embed
from datetime import datetime
import random, time
from discord.errors import HTTPException
from ..channels import TRAILER_CHANNEL_ID, POLL_CHANNEL_ID

from ..db import db
 
numbers = ('👻', '💀', '☠️', '👽', '👺', '🤡', '😈', '👿', '👁️', '🧟', '🧟‍♀️', '🧟‍♂️', '🦄')

class Poll(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.polls = []

    @command(name='summon')
    async def create_poll(self, ctx):
        main_channel = self.bot.get_channel(POLL_CHANNEL_ID)
        if len(self.polls) > 0:
            await ctx.send("Cmon man, we already have a poll going")
            return

        await main_channel.send("The cold winds blow... Your whispers have been heard... A chill runs down your spine...")

        time.sleep(10)

        embed = Embed(title="The hour of Spoopy is upon us...", description="What shall appease this spirit?")

        options = db.records("SELECT MovieName FROM movie_suggestions WHERE Watched = 0 ORDER BY random() LIMIT 4")
        try:
            shuffled_emojis = random.sample(numbers, len(numbers))
        except Exception as e:
            print(e)

        fields = [("Options", "\n".join([f"{shuffled_emojis[index]} {option[0]}" for index, option in enumerate(options)]), False)]

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
        
        message = await main_channel.send(embed=embed)

        for emoji in shuffled_emojis[:len(options)]:
            await message.add_reaction(emoji)

        if len(self.polls) > 0:
            self.polls = []

        self.polls.append((message.channel.id, message.id))

        self.bot.scheduler.add_job(self.complete_poll, "date", run_date=datetime.today().replace(hour=16, minute=30),
                                    args=[message.channel.id, message.id])
    
    @create_poll.error
    async def create_poll_error(self, ctx, exc):
        if isinstance(exc.original, HTTPException):
            await ctx.send("The Great Beyond rejects your request")

    async def complete_poll(self, channel_id, message_id):
        main_channel = self.bot.get_channel(POLL_CHANNEL_ID)
        message = await self.bot.get_channel(channel_id).fetch_message(message_id)

        selected_choice, most_voted = self.find_winner_from_poll(message)
        
        if selected_choice == None:
            await main_channel.send(f"The results are in and, ITS A TIE, FLIP A COIN I DON'T WANT TO (vanishes in ghostly shimmer)")
            self.polls = []
            return

        cleaned_choice = self.clean_choice(selected_choice, most_voted)

        await main_channel.send(f"The results are in and {cleaned_choice} wins")

        await self.remove_winner_from_contention(cleaned_choice)

    @Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.message_id in (poll[1] for poll in self.polls):
            message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)

            for reaction in message.reactions:
                if (not payload.member.bot 
                    and payload.member in await reaction.users().flatten()
                    and reaction.emoji != payload.emoji.name):
                    await message.remove_reaction(reaction.emoji, payload.member)

    def clean_choice(self, selected_choice, most_voted):
        return selected_choice.replace("(", "").replace(")","").replace("\'", "").replace(most_voted.emoji, "").replace("\n", "").strip()
    
    async def remove_winner_from_contention(self, cleaned_choice):
        link = db.record("SELECT TrailerLink FROM movie_suggestions WHERE MovieName LIKE ? LIMIT 1", "{}".format(cleaned_choice[1:]))

        trailer_channel = self.bot.get_channel(TRAILER_CHANNEL_ID)
        try:
            trailer_id = db.record("SELECT TrailerId FROM movie_suggestions WHERE TrailerLink = ?", link[0])

            message_to_delete = await trailer_channel.fetch_message(trailer_id[0])

            await message_to_delete.delete()

            db.execute("UPDATE movie_suggestions SET Watched = 1 WHERE TrailerId = ?", trailer_id[0])
        except Exception:
            self.polls = []
            pass

        self.polls = []

    def find_winner_from_poll(self, message):
        most_voted = self.calculate_winner(message.reactions)
        if most_voted == 'TIE':
            return None, 'TIE'
        else:
            poll_choices = message.embeds[0].fields[0].value

            poll_choices_split = poll_choices.split("\n")

            for choice in poll_choices_split:
                if most_voted.emoji in choice:
                    selected_choice = choice
                    return selected_choice, most_voted

    def calculate_winner(self, message_reactions):
        scores = {}
        high_score = 0
        for key, value in message_reactions.items():
            scores.setdefault(value, []).append(key)
            if value > high_score:
                high_score = value
        results = scores[high_score]
        if len(results) == 1:
            return results[0]
        else:
            return 'TIE', results

def setup(bot):
    bot.add_cog(Poll(bot))