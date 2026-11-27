"""One art style and one look per character, shared by every picture.

Every image prompt = STYLE + the looks of the characters in the shot + the shot.
Change a look here only, then rebuild, so every story stays the same.
"""

# Look: hand-drawn 2D cel animation of the 1990s -- flat-colored characters with
# clean dark outlines on top of richly hand-painted gouache backgrounds.
# A way of drawing, not any one film: never copy existing characters.
STYLE = (
    "Hand-drawn 2D cel animation still in a 1990s TV folktale style, "
    "characters in flat solid colors with clean dark brown outlines and almost no shading, "
    "simple rounded chunky bodies, big round heads, small dot eyes or squinting line eyes, "
    "exaggerated, rubbery comical facial expressions that fit the moment, "
    "soft muted pastel clothing colors (sage green, lavender, faded blue, off-white). "
    "Backgrounds richly hand-painted in gouache and oil with visible brush strokes, deep greens, mossy stone walls, "
    "earthy browns, painterly and detailed, clearly different from the flat characters. "
    "Joseon-era Korean countryside setting (thatched houses, hanok, stone walls, pine trees, straw baskets). "
    "Wide 16:9 frame, full scene, warm and funny, safe for young children. "
    "No text, no letters, no captions, no watermark, no speech bubbles."
)

# The style in a few words, put first in SDXL prompts (render_cuts.py).
STYLE_TAGS = (
    "2D hand-drawn cel animation still, flat colored cartoon characters with clean outlines, "
    "richly hand-painted gouache background with brush strokes, Joseon Korean village"
)

STYLE_TAGS_END = (
    "simple rounded cartoon bodies, small dot eyes, exaggerated funny expressions, "
    "muted pastel colors, wide 16:9 scene, for young children"
)

NEGATIVE = (
    "text, letters, watermark, logo, signature, modern anime, big sparkly anime eyes, glossy 3D render, CGI, "
    "photo, realistic, realistic animal, gradient cel shading, line art only, coloring book, "
    "western house, wooden cabin, chimney, European village, Japanese kimono, oni, scary, blood, gore, dark horror lighting, "
    "extra fingers, deformed hands, blurry"
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
    "tiger": "호랑이: big orange Korean tiger with black stripes, round comical face, small round eyes, "
             "funny rather than scary",
    "baby": "아기: chubby baby with rosy cheeks, wrapped in a colorful saekdong striped blanket",
    "mother": "엄마: young mother in a pale pink hanbok, seen from behind or as a soft shadow on the paper door, face not shown",
    "cow_thief": "소도둑: clumsy round-faced man, patched brown clothes, bundle tied on his back, wide surprised dot eyes",
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
}
LOOKS = {
    "base": {},
    "gouache": {"gouache": 0.85},
    "gouache_90s": {"gouache": 0.7, "90s": 1.5},
    "gouache_cel": {"gouache": 0.6, "cel": 0.6},
}
DEFAULT_LOOK = "gouache"

