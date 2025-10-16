import string
from find import *
import pandas as pd
import random


with open(r"./wordle_words.txt", "r") as f:
    GAME_WORDS = [e.strip("\n\t").lower() for e in f.readlines()]
GAME_WORD = "tepid"


# Main class
class Wordle:
    def __init__(self, dictionary=[], bot=True, print_statements=False, play=True):
        # _guess_count may be unnecessary because we can perform len() on history
        self._guess_count = 0
        self.history = []
        self._game_status = "active" if play else "new"

        self._all_letters = list(string.ascii_lowercase)
        self._yellow_letters = {}
        self._red_letters = []
        self._word_template = "_____"

        self._dist = pd.read_csv("./letter_distribution.txt", sep="\t")

        self.dictionary = pd.concat([create_dictionary(e) for e in dictionary]).drop_duplicates().reset_index(drop=True)
        if self.dictionary.size == 0:
            self.dictionary = None

        if len(dictionary) > 0:
            # the main loop for the ai
            while self._guess_count <= 6 and self._game_status == "active" and bot:
                self.guess()

    # algorithm to determine best guess - returns a str
    def _calc_guess(self) -> str:
        if self._guess_count == 0:
            return "adieu"

        list_combos = combos(self._word_template, self._all_letters, dictionary=self.dictionary)

        def _calc_guess_sort_function(word):
            # dist_table = self._dist[self._dist["letter"].str.contains("|".join(set(word.upper())))]
            # dist = sum([round(word.count(e.lower()) * float(a["percent"][a.index[0]][:-1]), 2) for e in dist_table["letter"] if (a:=dist_table[dist_table["letter"] == e]) is a])
            # return dist
            green = sum([1 for a, b in zip(word, self._word_template) if a == b])
            yellow = sum([sum([1 / (len(word) - len(v) if len(word) - len(v) > 0 else 1) * (1 / word.count(k) if word.count(k) > 0 else 1) for e in v if word[e] != k]) for k, v in self._yellow_letters.items()])
            red = sum([0 if e in self._all_letters else 1 for e in self._word_template if e.isalpha()])
            return 0 if red > 0 else (green + yellow)

        word = sorted(list_combos, key=_calc_guess_sort_function, reverse=True)
        print(word[:10], self.dictionary[:10])
        return word[0]

    # algorithm to make the guess - returns None
    def guess(self) -> None:
        if self._guess_count >= 6 or self._game_status != "active":
            self._game_status = "game over"
            return None

        word = self._calc_guess()
        self._guess_count += 1
        self.history.append(word)
        self._game_status = "game over" if GAME_WORD.lower() == self._word_template else self._game_status
        # update the template to be the letters in the correct known spots
        self._word_template = "".join([a if a == b else "_" for a, b in zip(GAME_WORD.lower(), word)])
        # remove any letters used that are not in the GAME_WORD from self._all_letters
        # and add letters to _yellow_letters if they aren't in the right position
        for i in range(len(word)):
            a = word[i]
            if a != GAME_WORD.lower()[i]:
                if a not in GAME_WORD.lower():
                    self._all_letters.remove(a)
                    self._red_letters.append(a)
                else:
                    if a in self._yellow_letters:
                        self._yellow_letters[a].append(i)
                    else:
                        self._yellow_letters[a] = [i]
        # update the dictionary to only contain words with the remaining letters and letters already in the right spot
        self.dictionary = self.dictionary[self.dictionary[0].str.contains("|".join(self._all_letters))]
        self.dictionary = self.dictionary[~self.dictionary[0].str.contains("|".join(self._red_letters))]
        for i in range(len(self._word_template)):
            letter = self._word_template[i]
            if letter.isalpha():
                self.dictionary = self.dictionary[self.dictionary[0].str[i] == letter]
        # update the dictionary to only contain words where the yellow letters haven't been used
        for letter in self._yellow_letters:
            for i in self._yellow_letters[letter]:
                self.dictionary = self.dictionary[self.dictionary[0].str[i] != letter]
        self.dictionary = self.dictionary.reset_index(drop=True)

        return None





# Exceptions


class WordleException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class WordGenerationException(WordleException):
    def __init__(self):
        super().__init__("Could not generate any words.")


class WordLengthException(WordleException):
    def __init__(self):
        super().__init__("Word length is not the right size.")


class GameOverException(WordleException):
    def __init__(self):
        super().__init__("Game is over. Can not continue with operation.")


class GuessLengthException(WordleException):
    def __init__(self):
        super().__init__("Guess counter does not fall within intended range.")


if __name__ == "__main__":
    for e in GAME_WORDS:
        print(f"NEW GAME - {e.upper()}")
        GAME_WORD = e.lower()
        game = Wordle(dictionary=["./dictionaries/dictionary.txt",
                              "./dictionaries/all_words_question_mark.txt",
                              #"./dictionaries/five-letter-words_sgb-words.txt",
                            ])
        print(f"GAME OVER - {game._game_status.upper()} with {len(game.history)} guesses.\n")

    # print(f"NEW GAME - {GAME_WORD.upper()}")
    # game = Wordle(dictionary=["./dictionaries/dictionary.txt",
    #                           "./dictionaries/all_words_question_mark.txt",
    #                           # "./dictionaries/five-letter-words_sgb-words.txt",
    #                           ])
    # print(f"GAME OVER - {game._game_status.upper()} with {len(game.history)} guesses.\n")

# the first dictionary (dictionary.txt) has a lot of trash words
# the second dicionary (all_words_question_mark.txt) lacks (at least) inane.
# the third dicionary (five-letter-words_sgb-words.txt) lacks (at least) inane.
