"""One art style and one look per character, shared by every picture.

Every image prompt = STYLE + the looks of the characters in the shot + the shot.
Change a look here only, then rebuild, so every story stays the same.
"""

# Look (chosen 2026-11-27): simple Korean webtoon-style YouTube storytelling cartoon.
# Thick black outlines, flat solid colors with no shading, a few colors only,
# plain backgrounds with only the shapes the scene needs, big heads with dot eyes.
# A way of drawing, not any one channel: never copy existing characters.
# (The earlier 1990s cel + gouache look is kept as LOOKS["gouache_90s"].)
STYLE = (
    "Very simple cute Korean webtoon-style cartoon for a YouTube folktale, few clean lines, simple round shapes, "
    "thick bold black outlines, flat solid colors with no shading and no gradients, "
    "a small limited palette of soft muted colors, "
    "big round heads, small round dot eyes, simple noses and mouths, clear funny expressions, "
    "plain simple backgrounds made of a few flat shapes (a wall, a door, a floor, a hill), not detailed. "
    "Joseon-era Korean setting (thatched houses, hanok, hanbok). "
    "Wide 16:9 frame, safe and friendly for young children. "
    "No text, no letters, no captions, no watermark, no speech bubbles."
)

# The style in a few words, put first in SDXL prompts (render_cuts.py).
STYLE_TAGS = (
    "very simple cute cartoon of a Korean folktale, few clean thick black lines, simple round shapes, "
    "flat solid colors, no shading, no texture, plain simple background, Joseon dynasty Korea"
)

# Sprites (render_layered.py): one character on plain white, to be cut out.
SPRITE_TAGS = (
    "full body character, whole figure visible, isolated on a plain pure white background, no background, "
    "very simple cute cartoon, few clean thick black lines, simple round shapes, flat solid colors, no shading"
)

# How characters are named in SDXL prompts when the key misleads it
# ("cow_thief" drew horns and a cow hat).
PROMPT_NAMES = {"cow_thief": "Joseon thief man", "mother": "Joseon mother", "baby": "Korean baby"}

# Kept out of every human sprite: modern clothes and Japanese/Chinese dress.
HUMAN_NEGATIVE = (
    "hoodie, jacket with zipper, baseball cap, sneakers, jeans, t-shirt, modern clothes, horns, horned hat, helmet, "
    "kimono, yukata, obi belt, kimono collar, Japanese hairstyle, Chinese hanfu, two people"
)

# Backgrounds (render_layered.py): the place only, Korean village things, no people.
KOREAN_PLACE = (
    "Joseon dynasty Korean countryside: round golden straw thatched choga houses, low stone walls, "
    "brown onggi clay jars, persimmon trees, gentle hills"
)

# Korean feel in every SDXL prompt: clothes, houses and things of an old Korean village.
KOREAN = (
    "people wear Korean hanbok: short jeogori jacket tied with a long otgoreum ribbon, "
    "women in a long full chima skirt with hair in a low bun and a binyeo pin, men in baggy baji trousers, "
    "round golden straw thatched choga houses, low stone walls, brown onggi clay jars, persimmon trees, gentle hills"
)

STYLE_TAGS_END = (
    "big round heads, small dot eyes, clear funny expressions, clear pose, "
    "limited soft color palette, minimal details, wide 16:9 scene, for young children"
)

NEGATIVE = (
    "text, letters, watermark, logo, signature, speech bubble, modern anime, big sparkly anime eyes, "
    "glossy 3D render, CGI, photo, realistic, realistic animal, detailed fur, painterly, brush strokes, "
    "detailed, intricate, hatching, crosshatching, many lines, wrinkles, paper texture, realistic proportions, "
    "watercolor texture, gradient shading, soft shading, detailed background, busy background, many colors, "
    "western house, wooden cabin, chimney, European village, glass windows, shingled roof, two-story house, "
    "Japanese kimono, obi belt, geta, Japanese house, tatami, torii, Chinese clothes, qipao, Chinese pagoda, "
    "western clothes, oni, scary, horror, blood, gore, "
    "extra fingers, deformed hands, blurry, duplicate characters, clones, the same animal repeated, "
    "group of tigers, crowd of animals"
)

# English, so the image model reads it the same way every time. Keep left/right exact.
CHARACTERS = {
    # 혹부리 영감
    "hump_man": "혹부리 영감: kind old Korean man, round smiling face, small white topknot, short white beard, "
                "white hanbok with a faded indigo vest, straw sandals; a big round fist-sized lump on his RIGHT cheek",
    "greedy_man": "욕심 영감: thin old Korean man, sharp eyebrows, narrow eyes, grey topknot, thin grey goatee, "
                  "grey hanbok with a brown vest; a lump on his LEFT cheek",
    "goblin_chief": "도깨비 대장: chubby, cheerful Korean dokkaebi goblin, bright red skin, shaggy black hair, one small "
                    "yellow horn, big round eyes, patched blue-and-green hanbok jacket, holding a knobby wooden magic club",
    "goblins": "도깨비들: small round goblins in different colors (green, blue, purple), one tiny horn each, "
               "patched hanbok scraps, cheerful and silly",
    # 토끼의 간
    "rabbit": "토끼: small white rabbit with long pink-lined ears, clever bright eyes, a tiny blue silk vest",
    "turtle": "자라: olive-green soft-shelled turtle with a long neck and kind worried eyes, "
              "wearing a small black Joseon official's hat",
    "dragon_king": "용왕: friendly blue-green Eastern dragon king with long white whiskers, golden royal robe and small crown, "
                   "pale and sick with a wet cloth on his forehead",
    "sea_soldiers": "용궁 군사: crabs and fish soldiers holding little spears, wearing tiny red helmets",
    # 소가 된 게으름뱅이
    "lazy_man": "게으름뱅이: young Korean man, messy black hair, half-closed sleepy eyes, wrinkled beige hanbok, barefoot",
    "lazy_ox": "게으름뱅이 소: yellowish-brown Korean ox with the same half-closed sleepy eyes and a messy black hair tuft "
               "between its horns",
    "mask_old_man": "탈 만드는 노인: mysterious old man, long white beard, dark grey robe, black gat hat, knowing smile",
    "farmer": "농부: sturdy cheerful farmer, white headband, rolled-up sleeves, brown hanbok trousers, straw hat on his back",
    # 바닷물이 짠 까닭
    "young_fisher": "청년: kind young Korean fisherman, black topknot with a white headband, light blue hanbok, gentle smile",
    "snow_old_man": "할아버지: frail old man with a long white beard, snow on his shoulders, plain white robe, "
                    "a faint magical golden glow around him",
    "thief": "도둑: sneaky skinny man, thin curly mustache, black clothes, black cloth tied over his head, shifty eyes",
    "millstone": "맷돌: small grey round stone hand-mill with a wooden handle, a faint golden glow",
    # 호랑이와 곶감
    "tiger": "호랑이 대호: big orange Korean tiger with black stripes, white belly and muzzle, round comical face, small round eyes, "
             "funny rather than scary",
    "baby": "아기 복동: chubby Korean baby boy, shaved head with one small tuft of hair on top, round face, "
            "rosy cheeks, plain white baenaet jeogori",
    "mother": "엄마 춘심: kind Korean village woman, rosy cheeks, black hair in a low bun, ochre yellow jeogori "
              "with a brown otgoreum ribbon, long navy blue chima skirt with a few square patches, straw shoes",
    "cow_thief": "소도둑 칠성: skinny sly Joseon man, black topknot, a tattered white headband, short stubble, "
                 "dark grey patched ragged hanbok jacket and baggy trousers tied with a rope belt, white leg wraps, "
                 "straw sandals, a big brown cloth sack",
}


# Style LoRAs (all SDXL 1.0, from Hugging Face, licenses allow commercial use).
# A "look" is a set of LoRAs: (repo, file, weight, trigger words put first in the prompt).
# render_cuts.py --looks gouache,gouache_90s draws every shot once per look, to compare.
LORAS = {
    # Warm hand-painted gouache storybook, visible brush strokes. openrail++
    "gouache": ("strkyyy/gouache-storybook", "gouache-storybook.safetensors", "g0u4ch3"),
    # Slider toward a 1990s anime look. MIT
    "90s": ("ntc-ai/SDXL-LoRA-slider.90s-anime", "90s anime.safetensors", "90s anime"),
    # Cel-shaded anime with ink lines. openrail++
    "cel": ("strkyyy/anime-cel-shaded", "anime-cel-shaded.safetensors", "4n1mec3l"),
    # Minimal flat illustration, clean outlines, plain backgrounds. creativeml-openrail-m
    "flat": ("ramel2/emotional-flat-illustration-sdxl-lora",
             "minimal_flat_illustration,_emotional_scene.safetensors", "minimal flat illustration"),
}
LOOKS = {
    "base": {},
    "gouache": {"gouache": 0.85},
    "gouache_90s": {"gouache": 0.7, "90s": 1.5},
    "gouache_cel": {"gouache": 0.6, "cel": 0.6},
    "flat": {"flat": 0.9},
    "flat_light": {"flat": 0.6},
}
DEFAULT_LOOK = "flat"  # webtoon-style references, 2026-11-27 (was gouache_90s)

# Groups: these keys mean several figures, so render_cuts.py does not say "only one".
GROUP_CHARACTERS = {"goblins", "sea_soldiers"}

# Time of day found in a shot's picture -> words put first, and what to keep out.
TIME_OF_DAY = {
    "night": ("night, flat dark navy blue sky filling the background, big yellow full moon, yellow glowing paper windows",
              "daylight, bright day, sunny, blue daytime sky"),
    "dusk": ("dusk, orange and purple evening sky, long shadows", "midday, bright noon"),
    "sunset": ("sunset, warm orange evening light", "midday, bright noon"),
    "dawn": ("early dawn, pale pink morning sky, soft first light", "night, midday"),
}

# Words in a shot's picture -> how Korean buildings must look (SDXL drew Western
# cottages with glass windows for "house" and "village").
BUILDINGS = (
    r"house|houses|village|hut|eave|eaves|window|gate|yard|shed|room|roof|wall|market|door",
    "traditional Korean choga cottages with thick rounded golden straw thatched roofs, "
    "low mud and stone walls, wooden posts, hanji paper sliding doors and windows",
)

