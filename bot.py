import os
import discord
from discord.ext import commands
import spacy
from imdb import Cinemagoer
import justwatch
from dotenv import load_dotenv
from functools import cache

load_dotenv()

AUTH_TOKEN = os.getenv('DISCORD_TOKEN')
# Initialize spaCy for NLP
nlp = spacy.load("en_core_web_sm")
# Initialize IMDbPY client
ia = Cinemagoer()

# Initialize JustWatch client
justwatch_api = justwatch.JustWatch(country='US')

# Define bot client
client = discord.Client(intents=discord.Intents().all())
client = commands.Bot(command_prefix='!', intents=discord.Intents().all())
client.remove_command('help')

# Define function to extract mood from user message
@cache
def extract_mood(message):
    doc = nlp(message)
    keywords = []
    for token in doc:
        if token.pos_ in ["NOUN", "ADJ", "VERB"] and not token.is_stop and token.lemma_.lower() != "movie" and token.lemma_.lower() != "film":
            keywords.append(token.lemma_.lower())
    return keywords

# Define function to search for movies or TV series based on mood and streaming service availability
def search_content(content_type, mood, streaming_services):
    # Retrieve top 250 movies or TV series from IMDbPY
    global made_after
    global how_many
    top_content = []

    if content_type == 'movie':
        top_content = ia.get_top250_movies()
    #elif content_type == 'tv':
    #    top_content = ia.get_top250_tv()
    #elif content_type == 'either':
    #    top_content.append(ia.get_top250_movies())
    #    top_content.append(ia.get_top250_tv())
    else:
        return 
    
    content_dict = {"movie": "movie", "tv": "show"}
    streaming_services_dict = {"netflix": "nfx", 
                            "hulu": "hlu", 
                            "hbomax": "hbm", 
                            "amazonprime": "amp", 
                            "disneyplus": "dnp", 
                            "appletvplus": "atp", 
                            "peacocktv": "pct", 
                            "paramountplus": "pmp", 
                            }
    short_stream_names = []
    if not any_svc:
        for x in streaming_services:
            short_stream_names.append(streaming_services_dict[x])

    # Filter content based on mood
    filtered_content = []
    found = False
    for content in top_content:
        if 'keywords' not in content:
            ia.update(content, 'keywords') # only works for movies :(
        found = False
        for cnt, keyword in enumerate(content["keywords"]):
            if cnt == 200:
                break
            if found:
                break
            for x in mood:
                if keyword.find(x) != -1:
                    filtered_content.append(content)
                    found = True
                    break
    
    # Filter content based on streaming service availability using JustWatch API
    available_content = []
    counter = 0
    for content in filtered_content:
        counter = 0
        results = justwatch_api.search_for_item(query=content['title'])
        for result in results['items']:
            if 'object_type' not in result:
                continue            
            if 'offers' not in result:
                continue                

            # if content_type == "either" and result['title'].lower() == content['title'].lower() and result['offers'] and result['original_release_year'] >= made_after:
            #     if any_svc:
            #         available_content.append(content)
            #         break
            #     for offer in result['offers']:
            #         if offer['package_short_name'] in short_stream_names:
            #             available_content.append(content)
            #             break
            #     break
            if result['object_type'] == content_dict[content_type] and result['title'].lower() == content['title'].lower() and result['offers'] and int(result['original_release_year']) >= int(made_after):
                if any_svc:
                    available_content.append(content)
                    break
                for offer in result['offers']:
                    if offer['package_short_name'] in short_stream_names:
                        available_content.append(content)
                        break
                break
            counter += 1
            if counter > 2:
                break
    
    # Sort content by IMDb rating and return top 5 results
    sorted_content = sorted(available_content, key=lambda x: x['rating'], reverse=True)
    return sorted_content[:how_many]

# Global variables to store user preferences
user_content_type = 'movie'
user_streaming_services = ["any"]
any_svc = True
made_after = 0
how_many = 5

@client.command(name='any')
async def any_stream(ctx):
    global any_svc
    any_svc = True
    user_streaming_services = ["any"]
    await ctx.send("Enabled results for all streaming services.")

# # Command to set content type
# @client.command(name='content')
# async def set_content(ctx, content=None):
#     global user_content_type

#     if not content:
#         await ctx.send('Select an option: \n(1) TV \n(2) Movie')
#         content_type = await client.wait_for('message', check=lambda m: m.author == ctx.author)
#         content_type = content_type.content
#     else: 
#         content_type = content


#     if content_type == "1" or content_type.lower() == "tv":
#         user_content_type = "tv"
#     elif content_type == "2" or content_type.lower() == "movie":
#         user_content_type = "movie"
#     else:
#         return None

#     await ctx.send(f"Content type set to {user_content_type}.")

# Command to set streaming services
@client.command(name='stream')
async def add_services(ctx, service=None):
    global user_streaming_services
    global any_svc

    if not service:
        await ctx.send("Select a streaming service to add to the list: \n(1) Netflix \n(2) Hulu \n(3) HBO Max \n(4) Amazon Prime Video \n(5) Disney+ \n(6) Apple TV+ \n(7) Peacock \n(8) Paramount+ \n!reset to clear the list\n!any to allow all streaming services")
        streaming_svc = await client.wait_for('message', check=lambda m: m.author == ctx.author)
        streaming_svc = streaming_svc.content
    else: 
        streaming_svc = service

    if any_svc:
        user_streaming_services = []
        any_svc = False

    if streaming_svc == "1" or streaming_svc.lower() == "netflix":
        user_streaming_services.append("netflix")
    elif streaming_svc == "2" or streaming_svc.lower() == "hulu":
        user_streaming_services.append("hulu")
    elif streaming_svc == "3" or streaming_svc.lower() == "hbo max":
        user_streaming_services.append("hbomax")
    elif streaming_svc == "4" or streaming_svc.lower() == "amazon prime video":
        user_streaming_services.append("amazonprime")
    elif streaming_svc == "5" or streaming_svc.lower() == "disney+":
        user_streaming_services.append("disneyplus")
    elif streaming_svc == "6" or streaming_svc.lower() == "apple tv+":
        user_streaming_services.append("appletvplus")
    elif streaming_svc == "7" or streaming_svc.lower() == "peacock":
        user_streaming_services.append("peacocktv")
    elif streaming_svc == "8" or streaming_svc.lower() == "paramount+":
        user_streaming_services.append("paramountplus")
    else:
        return None
    temp = ", ".join(user_streaming_services)
    await ctx.send(f"Streaming list is now [{temp}].")

# Command to recommend content based on user preferences
@client.command(name='wtw')
async def recommend(ctx, mood_arg=None):
    #global user_content_type
    global user_streaming_servFices
    
    # if not user_content_type:
    #     await ctx.send('Please set the content type using the !content command first.')
    #     return

    if not any_svc and len(user_streaming_services) == 0:
        await ctx.send('Please set the streaming services using the !streaming command first or !any for all services.')
        return


    if not mood_arg:
        # Prompt user for mood
        await ctx.send('What do you feel like watching?')
        mood = await client.wait_for('message', check=lambda m: m.author == ctx.author)
        mood = mood.content
    else:
        mood = mood_arg   

    mood = extract_mood(mood)
    
    # Search for content based on mood and streaming service availability
    recommended_content = search_content(user_content_type, mood, user_streaming_services)
    
    # Send top 5 recommended content to user
    if recommended_content:
        for content in recommended_content:
            await ctx.send(f"{content['title']} ({content['year']})\nIMDb rating: {content['rating']}\nIMDb link: https://www.imdb.com/title/tt{content.getID()}/")
    else:
        await ctx.send('Sorry, I could not find any recommendations with the given filter.')


# Command to reset streaming service preferences
@client.command(name='reset')
async def reset(ctx):
    global user_streaming_services
    user_streaming_services = []
    any_svc = False
    made_after = 0
    how_many = 5

    await ctx.send('Streaming services have been reset')

# Filter year made after
@client.command(name='madeafter')
async def madeafter(ctx, val):
    global made_after
    made_after = val
    await ctx.send(f'Showing results produced after {made_after}')

@client.command(name='amount')
async def howmany(ctx, val):
    global how_many
    how_many = val
    await ctx.send(f'Showing {how_many} results at a time')

# Command to reset streaming service preferences
@client.command(name='help')
async def helpme(ctx):
    message = f'''
        WhatToWatch is a Discord Bot created to help you and your friends find great movies to watch on the streaming services you already have!
It uses sentiment analysis and keyword matching to take in an input sentence and find movies with similar vibes to you. Whether that be your current mood, favorite movie genre, or anything you can think of! 

    !wtw - is the main command. Reply with a sentence to descibe your mood or what your interested in watching and WhatToWatch will send you list a top rated movies.

By default, WhatToWatch enables all streaming services and includes all movies in the IMDB top 250. You can use a handful of commands to help narrow down your search.

    !stream - lets you set which streaming services you would like to search through
    !any - enables all streaming services in the case that it has been reset
    !reset - resets your streaming service and movie year preferences 
    !madeafter - lets you set a minimum year for the release date of your movie search
    !amount - lets you set the number of movies you would like WhatToWatch to find in a single search (default is 5)


    '''
    await ctx.send(message)


# Run bot
client.run(AUTH_TOKEN)