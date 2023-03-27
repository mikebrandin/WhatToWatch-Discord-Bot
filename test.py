import os
import discord
from discord.ext import commands
import spacy
from imdb import Cinemagoer
import justwatch
from dotenv import load_dotenv
from functools import cache 
from concurrent.futures import ThreadPoolExecutor
from collections import deque
from typing import List
import asyncio

# Initialize spaCy for NLP
nlp = spacy.load("en_core_web_sm")
# Initialize IMDbPY client
ia = Cinemagoer()

# Initialize JustWatch client
justwatch_api = justwatch.JustWatch(country='US')
print(justwatch_api.get_genres())

# Define function to extract mood from user message
@cache
def extract_mood(message):
    doc = nlp(message)
    keywords = []
    for token in doc:
        if token.pos_ in ["NOUN", "ADJ", "VERB"] and not token.is_stop:
            keywords.append(token.lemma_)
    return list(keywords)

# Define function to search for movies  based on mood and streaming service availability
def search_content(content_type, mood, streaming_services):
    # Retrieve top 250 movies or TV series from IMDbPY
    global made_after
    top_content = []

    if content_type == 'movie':
        top_content = ia.get_top250_movies()
    elif content_type == 'tv':
        top_content = ia.get_top250_tv()
    else:
        return 
    print(top_content)

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
    for x in streaming_services:
        short_stream_names.append(streaming_services_dict[x])

    # Filter content based on mood
    filtered_content = []
    found = False
    for content in top_content:
        if 'keywords' not in content:
            ia.update(content, 'keywords')
        found = False
        for keyword in content["keywords"]:
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

            if content_type == "either" and result['title'].lower() == content['title'].lower() and result['offers'] and result['original_release_year'] >= made_after:
                if any_svc:
                    available_content.append(content)
                    break

                for offer in result['offers']:
                    if offer['package_short_name'] in short_stream_names:
                        available_content.append(content)
                        break
                break
            elif result['object_type'] == content_dict[content_type] and result['title'].lower() == content['title'].lower() and result['offers'] and result['original_release_year'] >= made_after:
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
    return sorted_content[:15]

# Global variables to store user preferences
user_content_type = 'movie'
user_streaming_services = ["netflix", "hbomax"]
any_svc = False
made_after = 0

# Command to recommend content based on user preferences
def recommend(mood_arg="I'm feeling happy"):
    global user_content_type
    global user_streaming_services

    mood = extract_mood(mood_arg)
    print(mood)
    # Search for content based on mood and streaming service availability

    recommended_content = search_content(user_content_type, mood, user_streaming_services)
    # Send top 5 recommended content to user
    if recommended_content:
        for content in recommended_content:
            print(f"{content['title']} ({content['year']})\nIMDb rating: {content['rating']}\nIMDb link: https://www.imdb.com/title/tt{content.getID()}/")
    else:
        print('Sorry, I could not find any recommendations with the given filter.')

recommend()