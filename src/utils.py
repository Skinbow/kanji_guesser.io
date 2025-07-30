from pathlib import Path

import random
import threading
import time
import csv
import logging

from random import randint

# from libraries.KanjiRecognition import *

#--------------------------Example---------------------------
# print("Loading the models...")
# kanji_df = get_kanji_dataframe("resources/csv/marugoto_a1_kanji_furigana.csv")
# device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
# model = load_model("resources/models/Model_250.pth", device)

# # Transform for drawing on the website
# transform = transforms.Compose([
#     transforms.Resize((64, 64)),
#     transforms.Grayscale(num_output_channels=1),
#     transforms.ToTensor(),
#     transforms.Lambda(lambda x: 1.0 - x),
#     transforms.Lambda(lambda x: (x > 0.2).float()),
#     transforms.Normalize(mean=[0.5], std=[0.5])
# ])

# # Transform for reference images
# transform_rf = transforms.Compose([
#         transforms.Resize((64, 64)),
#         transforms.Grayscale(num_output_channels=1),
#         transforms.ToTensor(),
#         transforms.ConvertImageDtype(torch.float32),
#         transforms.Lambda(lambda x: (x > 0.2).float()),
#         transforms.Normalize(mean=[0.5], std=[0.5])
#     ])

# labels, reference_vectors = get_reference_vectors(model, device, "resources/models/references/", transform_rf)
# print("Done.")
#------------------------------------------------------------


SAVE_DIR = Path("drawings")
SAVE_DIR.mkdir(exist_ok=True)

# TODO: add the complete list
characterList = ['金', '木', '水', '火', '土']
character_to_image_name = {
    '金': 'gold.png',
    '木': 'wood.png',
    '水': 'water.png',
    '火': 'fire.png',
    '土': 'earth.png'
}

def get_random_kanji():
    with open('static/kanjis.csv', newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        kanjis = list(reader)
    return random.choice(kanjis)