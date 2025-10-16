from bs4 import BeautifulSoup
import requests
from itertools import permutations
from math import perm
import sys
import asyncio
import pandas as pd


def create_dictionary(dictionary):
    df = pd.read_csv(dictionary, header=None)
    df = df.loc[df[0].str.len() == 5]
    df[0] = df[0].str.lower()
    return df


def combos(pattern, chars_available, print_statements=False, dictionary=None):
    loop = asyncio.new_event_loop()
    #loop = asyncio.get_running_loop()
    words = []
    p = len([c for c in pattern if c == "_"])
    template = pattern.replace("_", "%c")
    letter_combos = permutations(chars_available, p)
    if print_statements:
        print(f"Working on computing {(pc:=perm(len(chars_available), p))} permutation{'s' if pc > 1 else ''}...")

    async def check_word(w, ps, d=None):
        if d is None:
            c = requests.get(f"https://www.merriam-webster.com/dictionary/{w}")
            if c is not None:
                bs = BeautifulSoup(c.content, "html.parser")
                if len(bs.find_all("h1", class_="hword")) > 0:
                    if ps:
                        print(f"{w} is a word!")
                    return w
        elif isinstance(d, pd.core.frame.DataFrame):
            if not d.loc[d[0] == w].empty:
                return w
        return None

    if dictionary is None:
        for i, combo in enumerate(letter_combos):
            if i % 1000 == 0 and i > 0 and print_statements:
                print(f"Searched {i} combinations.")
            word = template % combo
            if word is not None:
                response = asyncio.run(check_word(word, print_statements))
                if response is not None:
                    words.append(response)
    elif isinstance(dictionary, pd.core.frame.DataFrame):
        perms = [template % e for e in letter_combos]
        words = dictionary.loc[dictionary[0].isin(perms)][0].tolist()

    loop.close()
    if print_statements:
        print("Finished.")
    return words


if __name__ == "__main__":
    # help menu
    if len([e for e in sys.argv if "help" in e.lower()]) > 0:
        print("Usage: python find.py pattern available_characters")
        print("Example: python find.py __e__ abdknpo")
        print("Disclaimer: this uses http to check for words, so naturally it is slow.")
    else:
        if len(sys.argv) == 3:
            combos(sys.argv[1], sys.argv[2])
        if len(sys.argv) == 4:
            combos(sys.argv[1], sys.argv[2])
