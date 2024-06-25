from os import listdir, chdir, getcwd
import json

CWD = getcwd()
CONFIG_PATH = './config.json'
PATHS = ["/videos/dog_videos/", "/videos/background_videos/"]

CONFIG = json.load(open(CONFIG_PATH))
CONFIG["video_settings"] = {"background_video_paths": [], "dog_video_paths": []}

chdir(CWD + PATHS[0])
CONFIG["video_settings"]["dog_video_paths"] = [f".{PATHS[0]}{el}" for el in listdir()]

chdir(CWD + PATHS[1])
CONFIG["video_settings"]["background_video_paths"] = [f".{PATHS[1]}{el}" for el in listdir()]

chdir(CWD)
