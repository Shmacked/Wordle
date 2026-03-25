from wordle import *


if __name__ == "__main__":
    game = Wordle(dictionary=["./dictionaries/all_words_question_mark.txt",
                              "./dictionaries/five-letter-words_sgb-words.txt",
                              "./dictionaries/english3.txt",
                              "./dictionaries/more_words.txt",
                              #"./dictionaries/Oxford English Dictionary Words.txt",
                              "./dictionaries/usa.txt",
                            ], operation=sum, browser_game=True, print_statements=True, starting_guess_word=None)
    game.play()
