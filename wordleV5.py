import pandas as pd
import random
import time

from bs4 import BeautifulSoup
import requests

from itertools import permutations
from math import perm

# selenium imports
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By

from datetime import datetime as dt
import asyncio
from pathlib import Path
import string

# "built-in" sum, but for products
from functools import reduce
import operator


class Wordle:
    def __init__(self, dictionary=[], print_statements=True, operation=sum, browser_game=True, word="adieu", starting_guess_word="adieu", save_picture=True, debug=False, dist_file=None, word_delta=5):
        self.print_statements = print_statements
        self.debug = debug
        self.save_picture = save_picture
        self.browser_game = browser_game

        if self.browser_game:
            if self.print_statements:
                print("Loading webdriver.")
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            self.driver = webdriver.Chrome(options=options)
            self.driver.get("https://www.nytimes.com/games/wordle/index.html")
            buttons = self.driver.find_elements(By.CSS_SELECTOR, "button[class*=Welcome-module_button__]")
            for button in buttons:
                if button.text.strip().lower() == "play":
                    play_button = button
                    break
            play_button.click()
            time.sleep(1)
            modal_button = self.driver.find_element(By.CSS_SELECTOR, "button[class*=Modal-module_closeIcon")
            modal_button.click()
            self.gameboard = self.driver.find_element(By.CSS_SELECTOR, "div[class*=Board-module_board]")
            self.body = self.driver.find_element(By.TAG_NAME, "body")
            self.body.send_keys(Keys.RETURN)
            if self.print_statements:
                print("Loaded webdriver.")
        else:
            self.WORD = word

        self.starting_guess_word = starting_guess_word
        self.word_delta = word_delta
        self.guesses = 0
        self.history = []

        if self.print_statements:
            print("Loading dictionaries.")

        if len(dictionary) > 0:
            self.dictionary = pd.concat([Wordle.create_dictionary(e) for e in dictionary]).drop_duplicates().reset_index(drop=True)
        else:
            self.dictionary = pd.DataFrame()

        self.dictionary_length = len(self.dictionary)

        if self.print_statements:
            print("Loading distributions for dictionaries.")

        if dist_file is not None:
            if Path(dist_file).exists():
                self._dist = pd.read_csv(dist_file, sep="\t", index_col="letter")
            else:
                dist = {e: round(sum(self.dictionary[0].str.count(e)), 4) for e in string.ascii_lowercase}
                dist_sum = sum([e for e in dist.values()])
                self._dist = pd.DataFrame({"percent": {k: f"{round(round(v / dist_sum * 100, 2), 1)}%" for k, v in dist.items()}})
        else:
            dist = {e: round(sum(self.dictionary[0].str.count(e.lower())), 4) for e in string.ascii_uppercase}
            dist_sum = sum([e for e in dist.values()])
            self._dist = pd.DataFrame({"percent": {k: f"{(round(v / dist_sum, 4) * 100)}%" for k, v in dist.items()}})

        if self.print_statements:
            print("Loaded distributions.")

        if self.dictionary.size == 0:
            self.dictionary = None
            if self.print_statements:
                print("Dictionary could not be created.")
        else:
            self.dictionary["weights"] = self.dictionary[0].apply(lambda x: round(operation([float(self._dist.loc[e.upper()]["percent"][:-1]) / (x.count(e) ** 2) if e.upper() in self._dist.index else 1 / (x.count(e) ** 2) for e in set(x)])))

        if self.print_statements:
            if self.dictionary is not None:
                print("Loaded dictionaries.")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.browser_game:
            self.driver.close()

    @staticmethod
    def build_dictionary_from_wordle_website(out_filename, print_statements=True, num_of_letters=5):
        if not Path(out_filename).parent.exists():
            print("Parent directory does not exist.")
            return None

        l = asyncio.new_event_loop()
        words = pd.DataFrame({"words": []})

        # wordle is currently played with 5 letter words...
        letter_combos = permutations(string.ascii_lowercase, num_of_letters)
        pc = perm(len(string.ascii_lowercase), num_of_letters)
        if print_statements:
            print(f"Building {pc} permutations...")

        async def check_word(w, d):
            if isinstance(d, pd.core.frame.DataFrame):
                if sum([1 for e in results if e == "empty"]) > 0:
                    # if self.print_statements:
                    #     # the word could not be long enough, maybe because the animation wasn't done loading for the tiles.
                    #     # tbd
                    #     #print("Word not long enough. Returning previously guessed word.")
                    return self.history[-1]

                while sum([1 for e in results if e == "tbd"]) > 0:
                    # remove the entry from the dictionary
                    self.dictionary = self.browser_purge(w, results)
                    # backspace the characters
                    d = [self.body.send_keys(Keys.BACKSPACE) for e in results]

                    w = self.avg_weighted_word()
                    self.body.send_keys(w)
                    self.body.send_keys(Keys.RETURN)

                    response = self.gameboard.find_element(By.XPATH, f".//div[@aria-label='Row {len(self.history) + 1}']")
                    results = asyncio.run(self.check(response, max_wait=3))

        async def check_words(loop, combos, d=None, update_percent=8):
            counter = 0
            for i, e in enumerate(combos):
                if i / len(combos) >= counter / update_percent:
                    counter += 1
                    print(f"Update: {counter / update_percent * 100}% with {len(d)} words.")
                loop.create_task(check_word(e, d))

        l.run_until_complete(check_words(l, letter_combos, d=words))
        l.close()
        if print_statements:
            print("Finished generating dictionary from wordle website.")
        return words

    @staticmethod
    def create_dictionary(dictionary):
        df = pd.read_csv(dictionary, header=None)
        df = df.loc[df[0].str.len() == 5]
        df[0] = df[0].str.lower()
        return df

    def random_word(self):
        return "adieu" if self.guesses == 0 else (self.dictionary[0][random.randint(0, len(self.dictionary) - 1)] if len(self.dictionary) > 0 else "")

    def avg_weighted_word(self):
        if self.guesses == 0 and self.starting_guess_word is not None:
            return self.starting_guess_word

        a = self.dictionary.copy()
        if len(a) == 0:
            if self.print_statements:
                print("self.avg_weighted_word(): Dictionary has a length of 0.")
                return self.starting_guess_word
        mean = round(a["weights"].mean())
        target_weight = (a["weights"] - mean).apply(abs).sort_values().iloc[0]
        a = a[(a["weights"] - mean).abs() == target_weight]

        return a[0].iloc[random.randint(0, len(a) - 1)]

    def weighted_word(self):
        if self.guesses == 0 and self.starting_guess_word is not None:
            return self.starting_guess_word

        a = self.dictionary.copy()
        a = a.sort_values(by=["weights"], ascending=False).reset_index(drop=True)

        if self.guesses == 0:
            max_val = a["weights"].iloc[0]
            a = a[a["weights"] >= max_val - self.word_delta]
            return a[0].iloc[random.randint(0, len(a) - 1)]

        if len(a) == 0:
            return ""

        #a = a[a["weights"] == a["weights"][0]].reset_index(drop=True)
        a = a[a["weights"] == a["weights"][0]]

        if self.debug:
            print([(a[0][i], a["weights"][i]) for i in range(len(a[:3]))])

        return a[0].iloc[random.randint(0, len(a) - 1)]

    def purge(self, word):
        a = self.dictionary[self.dictionary[0].str.len() == len(word)]
        for i in range(len(word)):
            if word[i] == self.WORD[i]:
                a = a[a[0].str[i] == word[i]]
            elif word[i] in self.WORD:
                a = a[(a[0].str.contains(word[i])) & (a[0].str[i] != word[i])]
            else:
                a = a[~a[0].str.contains(word[i])]
        weight = self.dictionary[self.dictionary[0] == word]["weights"]
        weight = weight.iloc[0] if len(weight) > 0 else 0
        return a.reset_index(drop=True), weight

    def guess(self):
        self.dictionary, weight = self.purge((w := self.avg_weighted_word()))
        self.guesses += 1
        self.history.append(w)
        if self.print_statements:
            print(f"Guess {self.guesses} is {w} ({weight}) with {len(self.dictionary)} options remaining out of {self.dictionary_length}.")
        return w

    def browser_purge(self, word, results):
        a = self.dictionary[self.dictionary[0].str.len() == len(word)]
        absent_locations = set()
        absent_letters = set()
        present_letters = set()

        if sum([1 for e in results if e == "empty"]) > 0:
            if self.debug:
                print(f"Empty on {word}")
            return a

        if sum([1 for e in results if e == "tbd"]) > 0:
            if self.debug:
                print(f"TBD on {word}")
            return a[a[0] != word].reset_index(drop=True)

        for i in range(len(word)):
            if results[i] == "correct":
                a = a[a[0].str[i] == word[i]]
            elif results[i] == "present":
                # wrong location; the location should also be appended to absent_locations set for clean up
                a = a[(a[0].str.contains(word[i])) & (a[0].str[i] != word[i])]
                absent_locations.add(i)
                present_letters.add(word[i])
            elif results[i] == "absent":
                # wrong letter and location
                absent_locations.add(i)
                absent_letters.add(word[i])

        # had to add this because "spool" caused a problem -> template:
        # "PAPAP"; present, absent, present, absent, present
        # O was present, then it was absent.
        for letter in present_letters.intersection(absent_letters):
            absent_letters.remove(letter)

        # clean up for absent locations should happen after we check for correct and present tiles
        for i in absent_locations:
            for letter in absent_letters:
                a = a[a[0].str[i] != letter]

        return a.reset_index(drop=True)

    def browser_user_guess(self, word):
        if len(self.dictionary[self.dictionary[0] == word]) == 0:
            if self.print_statements:
                print(f"Word {word} does not exist in dictionary.")
            return None

        if self.debug:
            #print(f"{word}'s weight is {self.dictionary[self.dictionary[0] == word].reset_index(drop=True)['weights'][0]}.")
            print(f"{word}'s weight is {self.dictionary[self.dictionary[0] == word]['weights'].iloc[0]}.")
        return self.browser_guess(word=word)

    def browser_guess(self, word=None):
        if word is None:
            if self.guesses == 0:
                w = self.weighted_word()
            else:
                w = self.avg_weighted_word()
        else:
            w = word

        if not self.browser_game:
            return w

        if len(self.history) >= 6:
            return w

        self.body.send_keys(w)
        self.body.send_keys(Keys.RETURN)

        # async function here to wait for the attributes to load
        response = self.gameboard.find_element(By.XPATH, f".//div[@aria-label='Row {len(self.history) + 1}']")
        results = asyncio.run(self.check(response, max_wait=5))

        if sum([1 for e in results if e == "empty"]) > 0:
            # if self.print_statements:
            #     # the word could not be long enough, maybe because the animation wasn't done loading for the tiles.
            #     # tbd
            #     #print("Word not long enough. Returning previously guessed word.")
            return self.history[-1]

        while sum([1 for e in results if e == "tbd"]) > 0:
            # remove the entry from the dictionary
            self.dictionary = self.browser_purge(w, results)
            # backspace the characters
            d = [self.body.send_keys(Keys.BACKSPACE) for e in results]

            w = self.avg_weighted_word()
            self.body.send_keys(w)
            self.body.send_keys(Keys.RETURN)

            response = self.gameboard.find_element(By.XPATH, f".//div[@aria-label='Row {len(self.history) + 1}']")
            results = asyncio.run(self.check(response, max_wait=3))

        if w == "":
            if self.print_statements:
                print("Could not generate a word; Returning previously guessed word.")
            return self.history[-1]

        weight = self.dictionary[self.dictionary[0] == w]["weights"]
        weight = weight.iloc[0] if len(weight) > 0 else 0
        self.dictionary = self.browser_purge(w, results)
        self.guesses += 1
        self.history.append(w)
        if self.print_statements:
            print(f"Guess {self.guesses} is {w} ({weight}) with {len(self.dictionary)} options remaining out of {self.dictionary_length}.")

        return w

    def browser_game_over(self) -> bool:
        if len(self.history) >= 6:
            return True

        if len(self.history) == 0:
            return False

        # In the other "response" variable used in browser_guess(), we add 1 to len(self.history), but we don't here,
        # because the rows on the game site are 1 indexed, and this method will only check the rows when self.history
        # is between 0 and 6 exclusive.
        response = self.gameboard.find_element(By.XPATH, f".//div[@aria-label='Row {len(self.history)}']")
        results = asyncio.run(self.check(response, max_wait=2))
        results = [1 for e in results if e == "correct"]

        if sum(results) == 5:
            return True

        return False

    def browser_game_score(self):
        if len(self.history) == 0:
            return "tbd"
        if self.browser_game_over():
            response = self.gameboard.find_element(By.XPATH, f".//div[@aria-label='Row {len(self.history)}']")
            results = sum([1 for e in asyncio.run(self.check(response, max_wait=5)) if e.lower() == "correct"])
            return "win" if self.guesses <= 6 and results == 5 else "lose"
        return "tbd"

    async def check(self, elem, max_wait=10):
        s = dt.now()
        while True:
            if sum([1 for e in elem.find_elements(By.CSS_SELECTOR, "div[class*=Tile-module_tile]") if (ds := e.get_attribute("data-state")) == "tbd" or ds == "empty"]) == 0:
                break
            if (dt.now() - s).seconds >= max_wait:
                break
        l = [e.get_attribute("data-state") for e in elem.find_elements(By.CSS_SELECTOR, "div[class*=Tile-module_tile]")]
        return l if sum([1 for e in l if e == 'tbd']) == 0 else ["tbd"] * 5

    def play(self):
        if self.browser_game:
            if self.print_statements:
                print("Starting game.")
            while not self.browser_game_over():
                word = self.browser_guess()
            if self.print_statements:
                print(f"Game over - {self.browser_game_score()}.")
            if self.save_picture:
                print("Taking a screen shot.")
                now = dt.now()
                if not Path("./images/").exists():
                    Path("./images/").mkdir()
                
                wait = WebDriverWait(self.driver, 10) # waits up to 10 seconds
                
                close_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[class*=Modal-module_close]")))
                actions = ActionChains(self.driver)
                actions.move_to_element(close_button).click().perform()
                close_button.click()

                scroll_fn = f"""
                    let container = document.querySelector('div[class*=App-module_gameContainer__]');
                    container.scrollTop = container.scrollIntoView(true);
                """

                self.driver.execute_script(scroll_fn)

                delete_toast_fn = """
                    // Use the ^= (starts with) operator to select any element whose ID begins with the stable part.
                    var element = document.querySelector('[id^="ToastContainer-module_gameToaster__"]');

                    // Check if the element was found before attempting to remove it.
                    if (element) {
                        element.remove();
                    }
                """

                self.driver.execute_script(delete_toast_fn)

                time.sleep(1)
                self.gameboard.find_element(By.XPATH, "../..").screenshot(f"./images/{now.year}_{now.month}_{now.day}_{self.browser_game_score()}.png")

            if self.print_statements:
                print("Closing web driver.")
            self.driver.close()
        else:
            WORD = self.WORD
            while True:
                word = self.guess()

                if not (word != WORD and len(self.dictionary) > 0):
                    break

            print(f"Took {self.guesses} guesses to guess {word} && {WORD}.")
            print(game.history)


def my_operation(x):
    return reduce(operator.mul, x, 1)


if __name__ == "__main__":
    game = Wordle(dictionary=["./dictionaries/all_words_question_mark.txt",
                              "./dictionaries/five-letter-words_sgb-words.txt",
                              "./dictionaries/english3.txt",
                              "./dictionaries/more_words.txt",
                              #"./dictionaries/Oxford English Dictionary Words.txt",
                              "./dictionaries/usa.txt",
                            ], operation=sum, browser_game=True, print_statements=True, starting_guess_word=None)
    game.play()
