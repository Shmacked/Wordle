import pandas as pd
import random

from functools import reduce # Valid in Python 2.6+, required in Python 3
import operator

from find import create_dictionary

WORD = "duvet"


class Wordle:
    def __init__(self, dictionary=[], print_statements=True, operation=sum):
        self.print_statements = print_statements

        self.guesses = 0
        self.history = []
        self._dist = pd.read_csv("./letter_distribution.txt", sep="\t", index_col="letter")

        if len(dictionary) > 0:
            self.dictionary = pd.concat([create_dictionary(e) for e in dictionary]).drop_duplicates().reset_index(drop=True)
        else:
            self.dictionary = pd.DataFrame()

        if self.dictionary.size == 0:
            self.dictionary = None
        else:
            self.dictionary["weights"] = self.dictionary[0].apply(lambda x: round(operation([float(self._dist.loc[e.upper()]["percent"][:-1]) / x.count(e) if e.upper() in self._dist.index else 1 / x.count(e) for e in set(x)])))

    def random_word(self):
        return "adieu" if self.guesses == 0 else (self.dictionary[0][random.randint(0, len(self.dictionary) - 1)] if len(self.dictionary) > 0 else "")

    def weighted_word(self):
        if self.guesses == 0:
            return "adieu"

        a = self.dictionary[self.dictionary[0].str.len() > 0]
        a = a.sort_values(by=["weights"], ascending=False)

        if len(a) == 0:
            return ""

        a = a[a["weights"] == a["weights"][0]].reset_index(drop=True)

        if self.print_statements:
            print([(a[0][i], a["weights"][i]) for i in range(len(a[:3]))])

        return a[0][random.randint(0, len(a) - 1)]

    def purge(self, word):
        a = self.dictionary[self.dictionary[0].str.len() == len(word)]
        for i in range(len(word)):
            if word[i] == WORD[i]:
                a = a[a[0].str[i] == word[i]]
            elif word[i] in WORD:
                a = a[(a[0].str.contains(word[i])) & (a[0].str[i] != word[i])]
            else:
                a = a[~a[0].str.contains(word[i])]
        return a.reset_index(drop=True)

    def guess(self):
        self.dictionary = self.purge((w := self.weighted_word()))
        self.guesses += 1
        self.history.append(w)
        if self.print_statements:
            print(f"Guess {self.guesses} is {w}.")
        return w


def my_operation(x):
    return reduce(operator.mul, x, 1)


if __name__ == "__main__":
    game = Wordle(dictionary=["./dictionaries/all_words_question_mark.txt",
                              "./dictionaries/five-letter-words_sgb-words.txt",
                              "./dictionaries/english3.txt",
                              "./dictionaries/more_words.txt",
                              #"./dictionaries/Oxford English Dictionary Words.txt",
                              "./dictionaries/usa.txt",
                            ], operation=my_operation)
    while True:
        word = game.guess()

        if not (word != WORD and len(game.dictionary) > 0):
            break

    print(f"Took {game.guesses} guesses to guess {word} && {WORD}.")
    print(game.history)
