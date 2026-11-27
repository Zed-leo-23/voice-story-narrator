"""Layered shot plans: draw backgrounds (no characters) and character sprites
(white background, cut out) separately, then place sprites on backgrounds.

Why: one SDXL prompt with scene + style + Korean props + several characters
kept dropping the tiger or mixing it with other animals, and the tiger looked
different in every shot. A background alone and one character alone are easy
for SDXL, and one sprite reused in many shots looks the same every time.

STORIES[id]:
  backgrounds: name -> (time of day or None, what the place looks like, no characters)
  sprites:     name -> (characters drawn together, pose / action)
               The first sprite of each character is its reference: later sprites
               of that character copy its look through IP-Adapter.
  shots:       shot number (as in stories/<id>.json) -> (background, [placements])
               placement: (sprite, x, bottom, height, flip)
                 x       centre of the sprite, 0 = left edge, 1 = right edge
                 bottom  where its lowest pixel sits, 0 = top, 1 = bottom edge
                 height  sprite height as a share of the frame height
                 flip    True to mirror it (face the other way)
"""

STORIES = {
    "tiger-persimmon": {
        "backgrounds": {
            "forest_persimmon": ("night", "snowy pine forest at night, falling snow, in the near left corner the edge of a "
                                          "thatched house eave with a string of orange dried persimmons hanging from it"),
            "village_below": ("night", "snowy mountain slope at night looking down at a small Korean village of round "
                                       "thatched choga houses with glowing yellow paper windows far below"),
            "house_wall": ("night", "outside wall of a thatched choga house at night in snow, low stone wall, one glowing "
                                    "yellow hanji paper window with the dark silhouette of a crying baby on it"),
            "window_mother": ("night", "outside wall of a thatched choga house at night in snow, one big glowing yellow "
                                       "hanji paper window with the dark silhouette of a woman rocking a child on it"),
            "window_crying": ("night", "outside wall of a thatched choga house at night in snow, one big glowing yellow "
                                       "hanji paper window with the dark silhouette of a small child crying loudly on it"),
            "room": ("night", "inside a warm small Korean ondol room at night, hanji paper sliding doors, a small oil lamp, "
                              "folded colorful quilts, a wooden chest, yellow floor paper"),
            "monster_wall": ("night", "outside a thatched choga house at night in snow, a huge dark scary imaginary monster "
                                      "shadow with big claws cast on the mud wall and the snow"),
            "cow_shed": ("night", "inside a dark Korean straw cow shed at night, straw on the ground, wooden posts and "
                                  "fence, a feeding trough, moonlight through gaps in the wall"),
            "mountain_path": ("night", "snowy mountain path at night between pine trees, snow flying, a full moon"),
            "tree_dawn": ("dawn", "a big old bare tree with one long low branch on a snowy hill at dawn, pink and pale "
                                  "yellow sky, distant mountains"),
            "cave": ("dawn", "a rocky mountain cave entrance with a dark opening, snow on the rocks, soft dawn light"),
            "persimmon_eave": (None, "under the eave of a thatched choga house in late autumn, many strings of peeled "
                                     "orange persimmons hanging and drying in the wind, a straw mat, onggi jars"),
            "cave_persimmon": (None, "a rocky mountain cave entrance with a dark opening, a string of orange dried "
                                     "persimmons hanging on the rock beside it, a sunny winter day"),
        },
        "sprites": {
            "tiger_ref": (["tiger"], "standing on all fours facing right, calm friendly smile, full body side view"),
            "tiger_run_scared": (["tiger"], "running away fast to the right in a panic, legs stretched, eyes wide, "
                                            "mouth open screaming, sweat drops"),
            "tiger_sneak": (["tiger"], "walking slowly to the right, belly hanging, licking its lips, hungry sly smile"),
            "tiger_listen": (["tiger"], "crouching low facing left, one ear forward listening, sly smug smile"),
            "tiger_scratch": (["tiger"], "sitting facing left, scratching its head with one front paw, confused face, "
                                         "question mark feeling"),
            "tiger_scared": (["tiger"], "sitting facing left, shaking and trembling, very wide scared eyes, tail tucked, "
                                        "teeth chattering"),
            "tiger_ridden": (["tiger", "cow_thief"], "the tiger leaping and running fast to the right with the man "
                                                     "sitting on its back hugging its neck tightly, both screaming"),
            "tiger_peek": (["tiger"], "lying down facing left, peeking, sighing with relief, a little shiver"),
            "tiger_wave": (["tiger"], "sitting facing the viewer, waving one front paw, sheepish embarrassed smile"),
            "thief_climb": (["cow_thief"], "reaching forward with both hands and lifting one leg to climb onto something "
                                           "in the dark, sly whisper face"),
            "thief_hang": (["cow_thief"], "hanging from above with both arms stretched up, legs dangling, "
                                          "relieved and scared"),
            "mother_offer": (["mother"], "kneeling and holding out a dried persimmon with one hand, gentle smile, "
                                         "side view facing left"),
            "baby_chew": (["baby"], "sitting and happily chewing a dried persimmon with both hands, eyes closed in joy"),
        },
        "shots": {
            1: ("forest_persimmon", [("tiger_run_scared", 0.55, 0.95, 0.50, False)]),
            2: ("village_below", [("tiger_sneak", 0.35, 0.96, 0.45, False)]),
            3: ("house_wall", [("tiger_listen", 0.72, 0.96, 0.42, False)]),
            4: ("window_mother", [("tiger_listen", 0.75, 0.96, 0.42, False)]),
            5: ("window_crying", [("tiger_scratch", 0.74, 0.96, 0.50, False)]),
            6: ("room", [("mother_offer", 0.62, 0.95, 0.70, False), ("baby_chew", 0.32, 0.95, 0.40, False)]),
            7: ("monster_wall", [("tiger_scared", 0.66, 0.96, 0.48, False)]),
            8: ("cow_shed", [("tiger_listen", 0.40, 0.95, 0.40, True), ("thief_climb", 0.72, 0.95, 0.55, False)]),
            9: ("mountain_path", [("tiger_ridden", 0.50, 0.95, 0.62, False)]),
            10: ("forest_persimmon", [("tiger_ridden", 0.55, 0.96, 0.66, False)]),
            11: ("tree_dawn", [("thief_hang", 0.32, 0.62, 0.42, False), ("tiger_run_scared", 0.72, 0.96, 0.32, False)]),
            12: ("cave", [("tiger_peek", 0.50, 0.90, 0.34, False)]),
            13: ("persimmon_eave", []),
            14: ("cave_persimmon", [("tiger_wave", 0.50, 0.95, 0.55, False)]),
        },
    },
}
