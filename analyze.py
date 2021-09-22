import cv2
import os
from skimage.metrics import structural_similarity  as ssim
import numpy as np
from PIL import Image
import pytesseract
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json
from TikTokApi import TikTokApi
import requests
from pprint import pprint
import re
import logging
import random
import string
import hashlib, io
import timeit
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id="beab155c09e64034b4793a9d3c7ada23",
                                                           client_secret="24e6b75c47ec46e1bafdd375f2bb321c",
                                                            redirect_uri="https://google.com",
                                                           scope="playlist-modify-public"))
api = TikTokApi.get_instance()

MATCHES = [
    {
        'img': cv2.imread('spotify_play.jpg', cv2.IMREAD_GRAYSCALE),
        'name': 'spotify',
        'bounds': [.8, .94]
    },
    {
        'img': cv2.imread('apple_play_2.jpg', cv2.IMREAD_GRAYSCALE),
        'name': 'apple',
        'bounds': [.7, .82]
    }
]

def time_method(func):
    def wrapper(*args):
        start = timeit.default_timer()
        val = func(*args)
        elapsed = timeit.default_timer() - start
        print(f'Elapsed time of {func.__name__}:', elapsed)
        return val
    return wrapper
@time_method
def get_ids_from_raw(data):
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
    return processed_ids
@time_method
def create_playlist_from_ids(ids):
    hash = hashlib.md5(''.join(ids).encode('utf-8')).hexdigest()
    user_id = sp.me()['id']
    playlists = sp.user_playlists(user_id)['items']
    exists = None
    for i,p in enumerate(playlists):
        if p['name'] == hash:
            exists = p['href']

    if exists is None:
        res = sp.user_playlist_create(user_id, hash)
        exists = res['href']
        sp.playlist_add_items(res['id'], ids)
   
    return exists

@time_method
def get_music_frames(file, matches, min_sim=0.5):
    video = cv2.VideoCapture(file)
    phase2 = []
    types = []
    y = None
    while True:
        ret,frame = video.read()
        if ret:
            gray_img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            _, threshed = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
            cv2.imwrite('out.jpg', threshed)
            for i, match in enumerate(matches):
                matched_result = cv2.matchTemplate(match['img'], threshed , cv2.TM_SQDIFF_NORMED)
                c,_,loc,_ = cv2.minMaxLoc(matched_result)
                if c < min_sim:
                    if y is None:
                        y = loc[1]
                    phase2.append(frame[:y, :])
                    types.append(i)
                    break
        else:
            break
    video.release()
    if len(phase2) == 0:
        return {}, []
    n = round(sum(types) / len(types))
    best_match = matches[n]
    m = best_match['bounds']
    final = []
    for my_frame in phase2:
        height, _,_ = my_frame.shape
        final.append(my_frame[int(height*m[0]):int(height*m[1]), :])
    return final, best_match 
@time_method
def remove_duplicate_frames(frames, max_sim=0.97):
    pframe = frames[0]
    non_duplicate_frames = []
    for frame in frames[1:]:
        sim = ssim(frame, pframe, multichannel=True)
        if sim < max_sim:
            gray_frame = cv2.cvtColor(pframe, cv2.COLOR_BGR2GRAY)
            _, bw_frame = cv2.threshold(gray_frame, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
            non_duplicate_frames.append(255 - bw_frame)
        pframe = frame
    return non_duplicate_frames
@time_method
def get_binary_from(video_id):
    c_did = ''.join(random.choice(string.digits) for num in range(19))
    id = re.match(r'https:\/\/m.tiktok.com\/v\/(.*)\.html', requests.get('https://vm.tiktok.com/' + video_id, allow_redirects=False).headers['Location']).group(1)
    t_data = api.getTikTokById(id, custom_did=c_did)
    addr = t_data['itemInfo']['itemStruct']['video']['downloadAddr']
    return api.get_Video_By_DownloadURL(addr, custom_did=c_did)
@time_method
def recognize_text_in_frames(frames):
    songs = []
    for frame in frames:
        output = str(pytesseract.image_to_string(frame, lang='eng', config='')) # --psm 6
        cleaned_output = list(filter(lambda s: len(s) > 2, output.split('\n')))
        if len(cleaned_output) > 1:
            song = cleaned_output[0]
            artist = cleaned_output[1]
            songs.append({'song': song, 'artist': artist})
    return songs
videos = [
    'ZMJwqpTPq',
    'ZMJwY87XF',
    'ZMJwYkMF3',
    # 'ZMJwq4uQy',
    'ZMJwm6Kva',
    'ZMJwY53gV',
]

for n in range(len(videos)):
    video_id = videos[n]
    binary = get_binary_from(video_id)
    if len(binary) < 500:
        raise ValueError('Exception')
    with open('out.mp4', 'wb') as f:
        f.write(binary)
    frames, best_type = get_music_frames('out.mp4', MATCHES)
    if len(frames) == 0:
        continue
    frames = remove_duplicate_frames(frames)
    raw_text = recognize_text_in_frames(frames)
    song_ids = get_ids_from_raw(raw_text)
    playlist = create_playlist_from_ids(song_ids)
    print('Playlist:', playlist)