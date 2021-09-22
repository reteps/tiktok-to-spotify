import cv2
import glob
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import json
import urllib.parse
import hashlib

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id="beab155c09e64034b4793a9d3c7ada23",
                                                           client_secret="24e6b75c47ec46e1bafdd375f2bb321c",
                                                            redirect_uri="https://google.com",
                                                           scope="playlist-modify-public"))

def create_from_raw_list(data):
    processed_ids = []
    for row in data:
        song = row['song']
        artist = row['artist']
        cleaned_song = song.split('(')[0].strip()
        cleaned_artist = artist.split(',')[0].split('&')[0].strip()
        queries = [
            f"{cleaned_song} {cleaned_artist}",
            f"{song}",
        ]
        
        parts = cleaned_song.split(' ')
        if len(parts[-1]) == 1:
            queries.insert(1, ' '.join(parts[:-1]) + ' ' + cleaned_artist)
            queries.insert(2, ' '.join(parts[:-1]))
        if cleaned_song != song:
            queries.append(cleaned_song)
        for query in queries:
            # print(query)
            result = sp.search(query, limit=1, type='track')['tracks']['items']
            if len(result) == 0:
                continue
            result = result[0]
            # print(result['name'], ','.join(n['name'] for n in result['artists']), result['id'])
            processed_ids.append(result['id'])
            break
    hash = hashlib.md5(''.join(processed_ids).encode('utf-8')).hexdigest()
    user_id = sp.me()['id']
    playlists = sp.user_playlists(user_id)['items']
    exists = None
    for i,p in enumerate(playlists):
        if p['name'] == hash:
            exists = p['href']

    if exists is None:
        res = sp.user_playlist_create(user_id, hash)
        exists = res['href']
        sp.playlist_add_items(res['id'], processed_ids)
   
    return exists