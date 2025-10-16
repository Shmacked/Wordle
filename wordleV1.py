import string
from find import *
import pandas as pd


with open(r"./wordle_words.txt", "r") as f:
    GAME_WORDS = [e.strip("\n\t").lower() for e in f.readlines()]
GAME_WORD = "tepid"

# Main class
class Wordle:
    def __init__(self, dictionary=[], bot=True, print_statements=False, play=True):
        self._guess_count = 0
        self._print_statements = print_statements
        self.guess_history = []
        self._game_status = "active"
        self._letters = {e: {"locations": [], "tried_locations": []} for e in string.ascii_lowercase}
        self._word_template = "_____"
        self._dist = pd.read_csv("./letter_distribution.txt", sep="\t")
        self.dictionary = pd.concat([create_dictionary(e) for e in dictionary]).drop_duplicates().reset_index(drop=True)
        if self.dictionary.size == 0:
            self.dictionary = None

        if play:
            # the main loop for the bot
            while self._guess_count <= 6 and self._game_status == "active" and bot:
                self.guess()

    def guess(self):
        if self._game_status == "active":
            if 0 <= self._guess_count < 7:
                if self._guess_count > 0:
                    potential_words = combos(pattern=self._word_template,
                                             chars_available="".join(self._letters.keys()),
                                             dictionary=self.dictionary,
                                             print_statements=self._print_statements)
                else:
                    potential_words = ["adieu"]
                if len(potential_words) > 0:
                    # x is a word - need to make this to reuse letters that where yellow
                    def avg_word(x, dist=self._dist, letters=self._letters, template=self._word_template):
                        if x is not None:
                            exclude = []
                            avg = 0
                            for i, letter in enumerate(x):
                                divide = len(x)
                                if (i not in letters[letter]["tried_locations"]) & (len(letters[letter]["tried_locations"]) > 0):
                                    avg += 1
                                # discourage repeat letters
                                if letter in exclude:
                                    avg -= 1
                                else:
                                    avg += 1
                                # encourage letters that are in the right location
                                if i in letters[letter]["locations"]:
                                    avg += 1
                                # encourage letters that are in the word template in the right location
                                if letter == template[i]:
                                    avg += 1
                                exclude.append(letter)
                                divide = divide if divide > 0 else 1
                                #avg += float(dist.loc[dist["letter"] == letter.upper()]["percent"].values[0][:-1]) / divide
                            #print(x, avg)
                            return avg
                        return 0

                    if self._print_statements:
                        print("Sorting results.")
                    potential_words.sort(reverse=True, key=avg_word)
                    word = potential_words[0]
                    if self._print_statements:
                        print(potential_words[:5])
                    self._update_with_word(word)
                    self.dictionary = self.dictionary[self.dictionary[0].str.contains(self._word_template.replace("_", "."), regex=True)]
                    if self._print_statements:
                        print(f"Guessed {word}, template is now {self._word_template}.")
                    self._guess_count += 1
                    self.guess_history.append(word)
                    # right now the best way to check if the game is won is if the word_template is complete
                    if sum(1 if letter.isalpha() else 0 for letter in self._word_template) == 5:
                        self._update_status("win")
                    else:
                        if self._guess_count == 6:
                            self._update_status("lose")
                else:
                    raise WordGenerationException
            else:
                raise GuessLengthException
        else:
            raise GameOverException

    def _update_with_word(self, word):
        for i, letter in enumerate(word):
            if letter in GAME_WORD:
                if word[i] == GAME_WORD[i]:
                    self._word_template = self._word_template[:i] + letter + self._word_template[i + 1:]
                    self._letters[letter]["locations"].append(i)
                else:
                    if letter not in self._word_template:
                        self._letters[letter]["tried_locations"].append(i)
                    else:
                        self._letters[letter]["tried_locations"] = [e for e in range(len(word))]
            else:
                del self._letters[letter]

    def _update_status(self, status):
        if self._game_status != "active":
            raise GameOverException

        if 0 > self._guess_count or self._guess_count > 7:
            raise GuessLengthException

        self._game_status = status

    def get_status(self):
        return self._game_status

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
    # for e in GAME_WORDS:
    #     print(f"NEW GAME - {e.upper()}")
    #     GAME_WORD = e.lower()
    #     game = Wordle(dictionary=["./dictionaries/dictionary.txt",
    #                           "./dictionaries/all_words_question_mark.txt",
    #                           #"./dictionaries/five-letter-words_sgb-words.txt",
    #                         ])
    #     print(f"GAME OVER - {game.get_status().upper()} with {len(game.guess_history)} guesses.\n")

    print(f"NEW GAME - {GAME_WORD.upper()}")
    game = Wordle(dictionary=["./dictionaries/dictionary.txt",
                              "./dictionaries/all_words_question_mark.txt",
                              # "./dictionaries/five-letter-words_sgb-words.txt",
                              ])
    print(f"GAME OVER - {game.get_status().upper()} with {len(game.guess_history)} guesses.\n")

# the first dictionary (dictionary.txt) has a lot of trash words
# the second dicionary (all_words_question_mark.txt) lacks (at least) inane.
# the third dicionary (five-letter-words_sgb-words.txt) lacks (at least) inane.
