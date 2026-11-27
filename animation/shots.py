"""Hand-written shot plan for each story: which lines a picture covers, what it shows.

Each shot: (scene, first line, last line, picture, motion). Optional "times" maps a
scene number to a time of day (night, dusk, sunset, dawn). Scene and line numbers
follow the story's timeline.json (lines counted from 0 inside each scene).
build_shotlist.py adds the times, the spoken lines and the full prompt.
"""

STORIES = {
    "hump-old-man": {
        "title": "혹부리 영감과 노래 주머니",
        "cast": ["hump_man", "greedy_man", "goblin_chief", "goblins"],
        "shots": [
            (1, 0, 0, "hump_man smiling and humming on a mountain path in autumn, a big round lump on his RIGHT cheek, thatched village far below", "slow zoom in"),
            (2, 0, 0, "hump_man carrying an A-frame of firewood on his back, the sun setting behind dark mountains, an old empty wooden house with a sagging roof among the trees", "slow pan right"),
            (2, 1, 1, "hump_man sitting on the wooden floor of the dark empty house, one small oil lamp, singing with his eyes closed, mouth open", "gentle zoom in, lamp flicker"),
            (3, 0, 1, "the paper door bursting open, goblin_chief and the goblins crowding in with wide happy eyes, pointing at hump_man", "quick push in"),
            (3, 2, 3, "hump_man, nervous but clever, tapping the lump on his RIGHT cheek with one finger while goblin_chief leans in, amazed", "slow zoom on the lump"),
            (3, 4, 4, "goblin_chief holding out an open treasure chest full of gold bars and silk, begging, the goblins cheering behind", "slight bounce"),
            (4, 0, 0, "goblin_chief swinging his magic club, the lump popping off hump_man's cheek with sparkles, then hump_man walking home at dawn rubbing his smooth cheek with a big bundle of gold and silk", "pan left to right"),
            (5, 0, 1, "greedy_man with a lump on his LEFT cheek, rubbing his hands greedily as villagers whisper the rumour in the background", "slow zoom in"),
            (5, 2, 3, "greedy_man singing terribly in the empty house, musical notes drawn crooked, goblins covering their ears and grimacing", "shake slightly"),
            (5, 4, 5, "greedy_man grinning and pointing at the lump on his LEFT cheek, goblin_chief frowning with arms crossed, holding the old lump in one hand", "slow push in"),
            (5, 6, 6, "the old lump flying through the air and sticking to greedy_man's RIGHT cheek, greedy_man now has lumps on both cheeks, crying and running down the mountain", "pan down"),
            (6, 0, 0, "a cute cutaway picture of a child singing, showing the throat with two small vocal folds vibrating, gentle sound waves around, simple and friendly, no labels", "slow zoom in"),
            (7, 0, 0, "hump_man and the goblins waving goodbye together in front of the old house under a starry sky", "slow zoom out"),
        ],
    },
    "rabbit-liver": {
        "title": "간을 두고 온 토끼",
        "cast": ["rabbit", "turtle", "dragon_king", "sea_soldiers"],
        "shots": [
            (1, 0, 0, "rabbit riding on turtle's back through blue water with bubbles, an underwater palace glowing far below", "slow zoom in"),
            (2, 0, 0, "the grand underwater dragon palace with coral pillars, dragon_king lying sick in bed with a cold cloth on his forehead, fish doctors and an old sea tortoise doctor gathered around", "slow pan right"),
            (2, 1, 1, "dragon_king sitting up weakly on his throne, asking his court, sea creatures looking at each other", "slow push in"),
            (2, 2, 2, "turtle stepping forward and bowing deeply before dragon_king, proud and brave", "slight zoom in"),
            (3, 0, 0, "turtle crawling up onto a sandy beach and into a green forest, finding rabbit happily munching grass", "pan left to right"),
            (3, 1, 1, "turtle talking sweetly to rabbit, a dreamy thought bubble picture of a palace feast and an official's hat above them", "gentle zoom in"),
            (3, 2, 3, "rabbit hopping excitedly onto turtle's back, then the two diving deep into the blue sea", "move downward"),
            (4, 0, 1, "sea_soldiers tying rabbit up with seaweed rope in the palace hall, dragon_king coughing on his throne", "slow push in"),
            (4, 2, 3, "rabbit, ears standing straight up in surprise but forcing a big friendly smile, explaining with paws raised; a small picture inset of a liver drying on a sunny rock by a stream", "gentle zoom in"),
            (4, 4, 4, "dragon_king pointing toward the surface, shouting an order, turtle hurrying", "quick push in"),
            (5, 0, 1, "rabbit leaping off turtle's back onto the beach and running into the forest, laughing and waving", "pan right fast"),
            (5, 2, 2, "turtle sitting alone on the sand, sighing with a big puff, the sunset sea behind", "slow zoom out"),
            (6, 0, 0, "a friendly cutaway picture of a child's tummy showing the liver as a big soft reddish-brown shape on the upper right, a small piece glowing and growing back, no labels", "slow zoom in"),
            (7, 0, 0, "rabbit waving from the forest edge, turtle waving from the waves", "slow zoom out"),
        ],
    },
    "lazy-ox": {
        "title": "소가 된 게으름뱅이",
        "cast": ["lazy_man", "lazy_ox", "mask_old_man", "farmer"],
        "shots": [
            (1, 0, 0, "lazy_man yawning hugely while lying on a straw mat, next to him a brown ox chewing grass, both with the same sleepy face", "slow zoom in"),
            (2, 0, 1, "lazy_man rolling around under a quilt in a thatched house at noon, family members with brooms and water jars frowning at him; he daydreams of a relaxed ox", "slow pan right"),
            (2, 2, 2, "lazy_man sneaking out of the gate with a tiny bundle, looking back nervously", "pan left to right"),
            (3, 0, 0, "a small hut by a mountain pass, mask_old_man carving a big wooden ox-head mask, lazy_man peeking curiously", "slow push in"),
            (3, 1, 3, "mask_old_man holding up the ox-head mask with a mysterious smile, lazy_man's eyes sparkling with excitement", "gentle zoom in"),
            (3, 4, 4, "lazy_man wearing the ox mask, an oxhide draped over his back, magical swirls as he turns into lazy_ox, mouth open in a surprised moo", "zoom in with sparkle"),
            (4, 0, 1, "a busy market, mask_old_man leading lazy_ox by a rope and talking to farmer, pointing a warning finger", "slow pan right"),
            (4, 2, 2, "farmer laughing and slapping his chest, holding the rope, ready to go", "slight bounce"),
            (4, 3, 3, "lazy_ox pulling a heavy plough through a field from morning to sunset, tears in his eyes, farmer behind with a whip of reeds", "slow pan left to right"),
            (5, 0, 0, "lazy_ox sneaking into a radish field at dusk and biting a big white radish, then the mask falling off with sparkles as he turns back into a man", "zoom in"),
            (5, 1, 1, "lazy_man back as a human, jumping with joy with arms raised, the ox mask and hide lying on the ground", "slight bounce"),
            (5, 2, 2, "lazy_man sweeping the yard at sunrise, carrying water, working hard and smiling, surprised villagers watching over the fence", "slow pan right"),
            (6, 0, 0, "a friendly cutaway picture of a cow showing a stomach with four round rooms, grass going up and down, the cow chewing happily, no labels", "slow zoom in"),
            (7, 0, 0, "lazy_man and a real ox resting together under a tree after work, waving", "slow zoom out"),
        ],
    },
    "salt-millstone": {
        "title": "바닷물이 짠 까닭",
        "cast": ["young_fisher", "snow_old_man", "thief", "millstone"],
        "shots": [
            (1, 0, 0, "a small stone millstone glowing softly on the deep sea floor, white salt swirling out of it into the blue water", "slow zoom in"),
            (2, 0, 0, "young_fisher carrying snow_old_man on his back through a snowy seaside village, then feeding him warm porridge by a fire", "slow pan right"),
            (2, 1, 2, "snow_old_man handing millstone to young_fisher with both hands, a gentle golden glow, young_fisher bowing gratefully", "gentle zoom in"),
            (3, 0, 2, "young_fisher turning millstone in his small room, white rice pouring out into a straw sack, his face amazed", "slow push in"),
            (3, 3, 4, "young_fisher sharing rice and cloth with smiling neighbours in the village yard, children laughing", "slow pan right"),
            (4, 0, 1, "thief sneaking out of the house at night with millstone under his arm, grinning, moonlight", "pan left to right"),
            (4, 2, 3, "thief rowing a stolen boat to the middle of the sea, millstone in the boat, dreaming of piles of money", "slow zoom out"),
            (5, 0, 0, "white salt pouring out of millstone, piling up in the boat, thief dancing happily", "slight bounce"),
            (5, 1, 1, "thief panicking, waving his arms at millstone, salt up to the edge of the boat", "shake slightly"),
            (5, 2, 2, "the boat sinking into the waves, thief clinging to a piece of wood, then millstone sinking down into the deep sea still spinning out salt", "move downward"),
            (6, 0, 0, "a friendly picture of the water cycle: rain on mountains, a river carrying tiny salt sparkles to the sea, sun lifting water up as clouds, salt staying in the sea, no labels", "slow pan right"),
            (7, 0, 0, "young_fisher on the beach at sunset waving, the calm sea sparkling", "slow zoom out"),
        ],
    },
    "tiger-persimmon": {
        "title": "호랑이보다 무서운 곶감",
        "cast": ["tiger", "baby", "mother", "cow_thief"],
        # Time of day per scene (scene number -> key of style.TIME_OF_DAY), for shots whose
        # picture text doesn't say it. The whole night in the village is scenes 1-4.
        "times": {1: "night", 2: "night", 3: "night", 4: "night", 5: "dawn"},
        "shots": [
            (1, 0, 0, "tiger running away in a panic through a snowy forest at night, a string of dried persimmons hanging from a house eave in the foreground", "slow zoom in"),
            (2, 0, 1, "tiger walking down a snowy mountain toward a village at night, belly rumbling, licking its lips", "pan left to right"),
            (2, 2, 3, "tiger crouching flat under the wall of a thatched house with a warm lit paper window, ears up; a crying baby silhouette in the window", "slow push in"),
            (3, 0, 1, "tiger crouching outside a thatched choga house at night, one ear pressed to the glowing hanji paper window, smiling smugly, the shadow of a woman rocking a little child on the paper window", "slow pan right"),
            (3, 2, 4, "tiger outside the glowing paper window at night scratching its head with one paw, confused, a big shadow of a crying little child on the window", "shake slightly"),
            (3, 5, 5, "mother holding out a dried persimmon, baby instantly quiet and happily chewing", "gentle zoom in"),
            (3, 6, 6, "tiger outside the thatched house at night trembling with wide scared eyes, a huge dark imaginary monster shadow looming above it", "slow push in"),
            (4, 0, 0, "inside a dark straw cow shed at night, a tiger crouching in the straw, cow_thief climbing onto the tiger's back thinking it is a cow", "slow zoom in"),
            (4, 1, 2, "tiger leaping and running wildly toward the mountain with cow_thief on its back, snow flying", "fast pan right"),
            (4, 3, 4, "cow_thief riding on the tiger's back hugging its neck tightly, both screaming, running past snowy trees at night", "shake, fast pan"),
            (5, 0, 0, "dawn, cow_thief hanging from a tree branch with both hands, the tiger running away below", "slow pan left to right"),
            (5, 1, 2, "tiger hiding in a cave, peeking out, sighing with relief and shivering", "slow zoom out"),
            (6, 0, 0, "peeled persimmons hanging under a house eave drying in the wind, turning into sweet dried persimmons with a light white powder, a child happily tasting one, no labels", "slow pan down"),
            (7, 0, 0, "tiger peeking out from the cave, sheepishly waving goodbye, persimmons on a string in front", "slow zoom out"),
        ],
    },
}
