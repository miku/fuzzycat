import regex
import unicodedata

# from http://zderadicka.eu/removing-diacritics-marks-from-strings/
SANDCRAWLER_CHAR_MAP = {
    '\N{Latin capital letter AE}': 'AE',
    '\N{Latin small letter ae}': 'ae',
    '\N{Latin capital letter Eth}': 'D',
    '\N{Latin small letter eth}': 'd',
    '\N{Latin capital letter O with stroke}': 'O',
    '\N{Latin small letter o with stroke}': 'o',
    '\N{Latin capital letter Thorn}': 'Th',
    '\N{Latin small letter thorn}': 'th',
    '\N{Latin small letter sharp s}': 's',
    '\N{Latin capital letter D with stroke}': 'D',
    '\N{Latin small letter d with stroke}': 'd',
    '\N{Latin capital letter H with stroke}': 'H',
    '\N{Latin small letter h with stroke}': 'h',
    '\N{Latin small letter dotless i}': 'i',
    '\N{Latin small letter kra}': 'k',
    '\N{Latin capital letter L with stroke}': 'L',
    '\N{Latin small letter l with stroke}': 'l',
    '\N{Latin capital letter Eng}': 'N',
    '\N{Latin small letter eng}': 'n',
    '\N{Latin capital ligature OE}': 'Oe',
    '\N{Latin small ligature oe}': 'oe',
    '\N{Latin capital letter T with stroke}': 'T',
    '\N{Latin small letter t with stroke}': 't',

    # bnewbold additions; mostly Latin-ish OCR ambiguous
    '\N{MICRO SIGN}': 'u',
    '\N{LATIN SMALL LETTER C}': 'c',
    '\N{LATIN SMALL LETTER F WITH HOOK}': 'f',
    '\N{Greek Small Letter Alpha}': 'a',
    '\N{Greek Small Letter Beta}': 'b',
    '\N{Greek Small Letter Iota}': 'i',
    '\N{Greek Small Letter Kappa}': 'k',
    '\N{Greek Small Letter Chi}': 'x',
    '\N{Greek Small Letter Upsilon}': 'u',
    '\N{Greek Small Letter Nu}': 'v',
    '\N{Greek Small Letter Gamma}': 'y',
    '\N{Greek Small Letter Tau}': 't',
    '\N{Greek Small Letter Omicron}': 'o',
    # bnewbold map-to-null (for non-printing stuff not in the regex)
    '\N{PARTIAL DIFFERENTIAL}': '',
    '\N{LATIN LETTER INVERTED GLOTTAL STOP}': '',
    '\N{N-ARY SUMMATION}': '',
    '\N{N-ARY PRODUCT}': '',
    '\N{MODIFIER LETTER CIRCUMFLEX ACCENT}': '',
    '\N{SNOWMAN}': '',
    '\N{CARON}': '',
}

SANDCRAWLER_PREFIX_REMOVE = [
    "original article: ",
    "original article ",
    "article: ",
    "title: ",
]

# regex that matches all characters which should be removed
SANDCRAWLER_REMOVE_CHAR_REGEX = regex.compile(
    r"[\s\p{Punctuation}\p{M}\p{InCombiningDiacriticalMarks}\u2000-\u206F\u2E00-\u2E7F’·“”‘’“”«»「」¿–±§_`°ʖ©®¤=<>|+$^~≈√∫≤≥÷ƒ∆¬£¢∞¥◊€]"
)

def sandcrawler_slugify(raw: str) -> str:
    """
    Python re-implementation of sandcrawler Scala code for string comparison
    ("scorable" strings)
    """
    slug = raw.strip().lower()

    # transforms before running regex
    for prefix in SANDCRAWLER_PREFIX_REMOVE:
        if slug.startswith(prefix):
            slug = slug[:len(prefix)]

    slug = slug.replace("&apos;", "'")

    # iterate over all chars and replace from map, if in map; then lower-case again
    slug = ''.join([SANDCRAWLER_CHAR_MAP.get(c, c) for c in slug]).lower()

    # early bailout before executing regex
    if not slug:
        return ""

    slug = unicodedata.normalize('NFKD', slug)
    slug = SANDCRAWLER_REMOVE_CHAR_REGEX.sub('', slug)

    return slug.lower()


def test_sandcrawler_slugify() -> None:
    test_cases = [
        ("", ""),
        ("asdf", "asdf"),
        ("'Hello World!'", "helloworld"),
        ("ASDF", "asdf"),
        ("as\n  df", "asdf"),
        ("as\u0142  bb \u00f8", "aslbbo"),
        ("`hello¿", "hello"),
        ("علمية", "علمية"),
        ("期刊的数字", "期刊的数字"),
        ("les pré-impressions explorées à partir", "lespreimpressionsexploreesapartir"),
        ("γ-Globulin", "yglobulin"),

        # "MICRO SIGN"
        ("\xb5meter", "umeter"),
        # "GREEK SMALL LETTER MU"
        ("\u03bcmeter", "\u03bcmeter"),

        # TODO: ("salt &and; pepper", "saltpepper"),
        # TODO: ("new <b>and</b> improved", "newandimproved"),

        # some via https://github.com/minimaxir/big-list-of-naughty-strings/blob/master/blns.txt
        ("-9223372036854775808/-1", "92233720368547758081"),
        (r",./;'[]\-= <>?:\"{}|_+ !@#$%^&*()`~", ""),
        (" \n\r \x85 \u1680\u2002\u2003\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u200b\u202f\u205f\u3000",
         ""),
        (r"Ω≈ç√∫˜≤≥÷", "ωc"),
        (r"åß∂ƒ©˙∆˚¬…æ", "asfae"),
        (r"œ∑´®†¥¨ˆøπ“‘", "oeoπ"),
        (r"¡™£¢∞§¶•ªº–≠ ", "tmao"),
        (r"¸˛Ç◊ı˜Â¯˘¿", "cia"),
        (r"ÅÍÎÏ˝ÓÔÒÚÆ☃", "aiiiooouae"),
        (r"Œ„´‰ˇÁ¨ˆØ∏”’", "oeao"),
        (r"`⁄€‹›ﬁﬂ‡°·‚—±", "fifl"),
        (r"ЁЂЃЄЅІЇЈЉЊЋЌЍЎЏАБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдежзийклмнопрстуфхцчшщъыьэюя",
         "еђгєѕііјљњћкиуџабвгдежзииклмнопрстуфхцчшщъыьэюяабвгдежзииклмнопрстуфхцчшщъыьэюя"),
        (r"⁰⁴⁵₀₁₂", "045012"),
        (r"社會科學院語學研究所", "社會科學院語學研究所"),
        # TODO: ("パーティーへ行かないか", "パーティーへ行かないか"),
        # TODO: ("表ポあA鷗ŒéＢ逍Üßªąñ丂㐀𠀀", "表ポあa鷗oeebＢ逍usaan丂㐀𠀀"),
        (r"( ͡° ͜ʖ ͡°)", ""),
        # emoji ok? I guess
        (r"👾 🙇 💁 🙅 🙆 🙋 🙎 🙍", "👾🙇💁🙅🙆🙋🙎🙍"),
        (r"2️⃣ 3️⃣ 4️⃣ 5️⃣", "2345"),
        (r"﷽ ", "﷽"),
        (r"\"̗̺͖̹̯͓Ṯ̤͍̥͇͈h̲́e͏͓̼̗̙̼̣͔ ͇̜̱̠͓͍ͅN͕͠e̗̱z̘̝̜̺͙p̤̺̹͍̯͚e̠̻̠͜r̨̤͍̺̖͔̖̖d̠̟̭̬̝͟i̦͖̩͓͔̤a̠̗̬͉̙n͚͜ ̻̞̰͚ͅh̵͉i̳̞v̢͇ḙ͎͟-҉̭̩̼͔m̤̭̫i͕͇̝̦n̗͙ḍ̟ ̯̲͕͞ǫ̟̯̰̲͙̻̝f ̪̰̰̗̖̭̘͘c̦͍̲̞͍̩̙ḥ͚a̮͎̟̙͜ơ̩̹͎s̤.̝̝ ҉Z̡̖̜͖̰̣͉̜a͖̰͙̬͡l̲̫̳͍̩g̡̟̼̱͚̞̬ͅo̗͜.̟",
         "thenezperdianhivemindofchaoszalgo"),
        (r"Ｔｈｅ ｑｕｉｃｋ ｂｒｏｗｎ ｆｏｘ ｊｕｍｐｓ ｏｖｅｒ ｔｈｅ ｌａｚｙ ｄｏｇ", "thequickbrownfoxjumpsoverthelazydog"),
        (r"Ｔｈｅ ｑｕｉｃｋ ｂｒｏｗｎ ｆｏｘ ｊｕｍｐｓ ｏｖｅｒ ｔｈｅ ｌａｚｙ ｄｏｇ", "thequickbrownfoxjumpsoverthelazydog"),
        (r"𝕋𝕙𝕖 𝕢𝕦𝕚𝕔𝕜 𝕓𝕣𝕠𝕨𝕟 𝕗𝕠𝕩 𝕛𝕦𝕞𝕡𝕤 𝕠𝕧𝕖𝕣 𝕥𝕙𝕖 𝕝𝕒𝕫𝕪 𝕕𝕠𝕘 ", "thequickbrownfoxjumpsoverthelazydog"),
    ]

    for in_str, out_str in test_cases:
        if sandcrawler_slugify(in_str) != out_str:
            for c in list(sandcrawler_slugify(in_str)):
                try:
                    print(unicodedata.name(c))
                except ValueError:
                    print(ord(c))
            print("----")
            for c in list(out_str):
                print(unicodedata.name(c))
            print(in_str)
        assert sandcrawler_slugify(in_str) == out_str

