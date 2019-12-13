#!/usr/bin/env python3
import os
import sys
import time

from generator.gpt2.gpt2_generator import *
from story import grammars
from story import grammars
from story.story_manager import *
from story.utils import *
from func_timeout import func_timeout, FunctionTimedOut
	

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"


def splash():
    print("0) New Game\n1) Load Game\n2) Change temperature/top_k\n")
    choice = get_num_options(3)

    if choice == 2:
        return "regen"
    elif choice == 1:
        return "load"
    else:
        return "new"


def select_game():
    with open(YAML_FILE, "r") as stream:
        data = yaml.safe_load(stream)

    print("Pick a setting.")
    settings = data["settings"].keys()
    for i, setting in enumerate(settings):
        print_str = str(i) + ") " + setting
        if setting == "fantasy":
            print_str += " (recommended)"

        console_print(print_str)
    console_print(str(len(settings)) + ") custom")
    choice = get_num_options(len(settings) + 1)

    if choice == len(settings):

        context = ""
        console_print(
            "\nEnter a prompt that describes who you are and the first couple sentences of where you start "
            "out ex:\n 'You are a knight in the kingdom of Larion. You are hunting the evil dragon who has been "
            + "terrorizing the kingdom. You enter the forest searching for the dragon and see' "
        )
        prompt = input("Starting Prompt: ")
        return context, prompt, True

    setting_key = list(settings)[choice]

    print("\nPick a character")
    characters = data["settings"][setting_key]["characters"]
    for i, character in enumerate(characters):
        console_print(str(i) + ") " + character)
    character_key = list(characters)[get_num_options(len(characters))]

    name = input("\nWhat is your name? ")
    setting_description = data["settings"][setting_key]["description"]
    character = data["settings"][setting_key]["characters"][character_key]

    name_token = "<NAME>"
    if character_key == "noble" or character_key == "knight":
        context = grammars.generate(setting_key, character_key, "context") + "\n\n"
        context = context.replace(name_token, name)
        prompt = grammars.generate(setting_key, character_key, "prompt")
        prompt = prompt.replace(name_token, name)
    else:
        context = (
            "You are "
            + name
            + ", a "
            + character_key
            + " "
            + setting_description
            + "You have a "
            + character["item1"]
            + " and a "
            + character["item2"]
            + ". "
        )
        prompt_num = np.random.randint(0, len(character["prompts"]))
        prompt = character["prompts"][prompt_num]

    return context, prompt, False


def instructions():
    text = "\nAI Dungeon 2 Instructions:"
    text += '\n Enter actions starting with a verb ex. "go to the tavern" or "attack the orc."'
    text += '\n To speak enter \'say "(thing you want to say)"\' or just "(thing you want to say)" '
    text += "\n\nThe following commands can be entered for any action: "
    text += '\n  "revert"   Reverts the last action allowing you to pick a different action'
    text += '\n  "quit"     Quits the game and saves'
    text += '\n  "restart"  Starts a new game and saves your current one'
    text += '\n  "save"     Makes a new save of your game and gives you the save ID'
    text += '\n  "save abc" Saves the game file as abc'
    text += '\n  "load"     Asks for a save ID and loads the game if the ID is valid'
    text += '\n  "load abc" Loads the save file abc if it exists'
#    text += '\n  "print"    Prints a transcript of your adventure (without extra newline formatting)'
    text += '\n  "help"     Prints these instructions again'
    text += '\n  "censor off/on" to turn censoring off or on.'
    text += '\n  "infto x"  Sets seconds needed to break a loop (for example infto 200)'
    text += '\n  "!"        Text after ! will be injected into the story'
    text += '\n  "retry"    Try a different outcome with same action'
    text += '\n  "setchar"  Switch to a different character, must write in third person'
    text += '\n  "nosave"   turns off autosave'
    
    return text


def play_aidungeon_2():
    generate_num = 60
    temperature = 0.4
    top_k = 40
    top_p = 0.9
    inference_timeout = 200
    upload_story = True

    print("\nInitializing AI Dungeon! (This might take a few minutes)\n")
    generator = GPT2Generator(generate_num, temperature, top_k, top_p)
    story_manager = UnconstrainedStoryManager(generator)
    
    def act(action):
        return func_timeout(inference_timeout, story_manager.act, (action,))
    def notify_hanged():
        console_print("That input caused the model to hang, use infto command to change the timeout, at the moment it is set to " + str(inference_timeout) + " seconds.")
    print("\n")

    with open("opening.txt", "r", encoding="utf-8") as file:
        starter = file.read()
    print(starter)
    
    console_print(instructions())
    console_print("After a crash you can reload the last working position by typing load autosave")

    while True:
        if story_manager.story != None:
            del story_manager.story

        print("\n\n")

        while True:
            if story_manager.story != None:
                del story_manager.story

            characters = []
            current_character = "You"
			
            print("\n\n")

            splash_choice = splash()

            if splash_choice == "new":
                print("\n\n")
                context, prompt, noblock = select_game()
                print("\nGenerating story...")

                story_manager.start_new_story(
                    prompt, context=context, upload_story=upload_story, noblock=noblock
                )
                print("\n")
                console_print(str(story_manager.story))
                break

            elif splash_choice == "load":
                load_ID = input("What is the ID of the saved game? ")
                result = story_manager.load_new_story_from_local(load_ID)
                print("\nLoading Game...\n")
                console_print(result)
                break

            else:
                temperature = float(input("New temperature (default 0.4): "))
                top_k = int(input("New top_k (default 40): "))
                print("\nInitializing AI Dungeon! (This might take a few minutes)\n")
                generator = GPT2Generator(generate_num, temperature, top_k, top_p)
                story_manager = UnconstrainedStoryManager(generator)
                print("\n")

        while True:
            sys.stdin.flush()
            if upload_story:
                try:
                    story_manager.story.save_to_local("autosave")
                except:
                    print("\nautosave failed\n")
            action = input("> ")
            if action.lower() == "restart":
                rating = input("Please rate the story quality from 1-10: ")
                rating_float = float(rating)
                story_manager.story.rating = rating_float
                break

            elif action.lower() == "quit":
                rating = input("Please rate the story quality from 1-10: ")
                rating_float = float(rating)
                story_manager.story.rating = rating_float
                exit()

            elif action.lower() == "nosaving":
                upload_story = False
                story_manager.story.upload_story = False
                console_print("Saving turned off.")

            elif action.lower() == "help":
                console_print(instructions())

            elif action.lower() == "censor off":
                if not generator.censor:
                    console_print("Censor is already disabled.")
                else:
                    generator.censor = False
                    console_print("Censor is now disabled.")

            elif action.lower() == "censor on":
                if generator.censor:
                    console_print("Censor is already enabled.")
                else:
                    generator.censor = True
                    console_print("Censor is now enabled.")

            elif action.lower() == "save":
                id = str(uuid.uuid1())
                story_manager.story.save_to_local(id)
                console_print("Game saved.")
                console_print(
                    "To load the game, type 'load' and enter the following ID: "
                    + id
                )
                
            elif len(action.split(" ")) == 2 and action.lower().split(" ")[0] == "save":
                id = action.lower().split(" ")[1]
                story_manager.story.save_to_local(id)
                console_print("Game saved.")
                console_print(
                    "To load the game, type 'load' and enter the following ID: "
                    + id
                )

            elif action.lower() == "load":
                load_ID = input("What is the ID of the saved game?")
                result = story_manager.story.load_from_local(load_ID)
                #console_print("\nLoading Game...\n")
                console_print(result)

            elif len(action.split(" ")) == 2 and action.split(" ")[0].lower() == "load":
                load_ID = action.split(" ")[1]
                result = story_manager.story.load_from_local(load_ID)
                #console_print("\nLoading Game...\n")
                console_print(result)

            #elif action.lower() == "print":
            #    print("\nPRINTING\n")
            #    print(str(story_manager.story))

            elif action.lower() == "revert":

                if len(story_manager.story.actions) is 0:
                    console_print("You can't go back any farther. ")
                    continue

                story_manager.story.actions = story_manager.story.actions[:-1]
                story_manager.story.results = story_manager.story.results[:-1]
                console_print("Last action reverted. ")
                if len(story_manager.story.results) > 0:
                    console_print(story_manager.story.results[-1])
                else:
                    console_print(story_manager.story.story_start)
                continue
                
            elif action.lower() == 'retry':
                if len(story_manager.story.actions) is 0:
                    console_print("There is nothing to retry.")
                    continue

                last_action = story_manager.story.actions.pop()
                last_result = story_manager.story.results.pop()

                try:
                    # Compatibility with timeout patch
                    act
                except NameError:
                    act = story_manager.act

                try:
                    try:
                        act(last_action)
                        console_print(last_action)
                        console_print(story_manager.story.results[-1])
                    except FunctionTimedOut:
                        story_manager.story.actions.append(last_action)
                        story_manager.story.results.append(last_result)
                        notify_hanged()
                        console_print("Your story progress has not been altered.")
                except NameError:
                    pass

                continue

            elif len(action.split(" ")) == 2 and action.lower().split(" ")[0] == 'infto':

                try:
                    inference_timeout = int(action.split(" ")[1])
                    console_print("Set timeout to " + str(inference_timeout) + " seconds")
                except:
                    console_print("Failed to set timeout. Example usage: infto 180")

                continue
            
            elif len(action.split(" ")) >= 2 and action.lower().split(" ")[0] == "setchar":

                new_char = action[len(action.split(" ")[0]):].strip()
                if new_char == "":
                    console_print("Character name cannot be empty")
                    continue
                is_known_char = False
                for known_char in characters:
                    if known_char.lower() == new_char.lower():
                        is_known_char = True
                        new_char = known_char
                        break
                if not is_known_char:
                    characters.append(new_char)
                
                current_character = new_char
                console_print("Switched to character " + new_char)
                continue

            elif len(action.split(" ")) == 2 and action.lower().split(" ")[0] == 'infto':

                try:
                    inference_timeout = int(action.split(" ")[1])
                    console_print("Set timeout to " + str(inference_timeout))
                except:
                    console_print("Failed to set timeout. Example usage: infto 240")
                continue

            else:
                if action == "":
                    action = ""               	
                    try:
                        result = act(action)
                    except FunctionTimedOut:
                        notify_hanged()
                        continue
                    console_print(result)

                elif action[0] == '"':
                    if current_character == "You":
                        action = "You say " + action
                    else:
                        action = current_character + " says " + action

                elif action[0] == '!':
                    action = "\n" + action[1:].replace("\\n", "\n") + "\n"

                else:
                    action = action.strip()
                    action = action[0].lower() + action[1:]

                    action = current_character + " " + action

                    if action[-1] not in [".", "?", "!"]:
                        action = action + "."

                    action = first_to_second_person(action)

                    action = "\n> " + action + "\n"

                try:
                    result = "\n" + act(action)
                except FunctionTimedOut:
                    notify_hanged()
                    continue
                if len(story_manager.story.results) >= 2:
                    similarity = get_similarity(
                        story_manager.story.results[-1], story_manager.story.results[-2]
                    )
                    if similarity > 0.9:
                        story_manager.story.actions = story_manager.story.actions[:-1]
                        story_manager.story.results = story_manager.story.results[:-1]
                        console_print(
                            "Woops that action caused the model to start looping. Try a different action to prevent that."
                        )
                        continue

                if player_won(result):
                    console_print(result + "\n CONGRATS YOU WIN")
                    break
                elif player_died(result):
                    console_print(result)
                    console_print("YOU DIED. GAME OVER")
                    console_print("\nOptions:")
                    console_print("0) Start a new game")
                    console_print(
                        "1) \"I'm not dead yet!\" (If you didn't actually die) "
                    )
                    console_print("Which do you choose? ")
                    choice = get_num_options(2)
                    if choice == 0:
                        break
                    else:
                        console_print("Sorry about that...where were we?")
                        console_print(result)

                else:
                    console_print(result)


if __name__ == "__main__":
    play_aidungeon_2()
