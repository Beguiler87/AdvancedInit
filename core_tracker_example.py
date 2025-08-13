# Primary file for Basic Initiative Tracker.
import colorama
from colorama import Fore, Back, init
colorama.init(autoreset=True)
# Warrior class defines combatants: name, initiative, which side of combat they belong to.
class Warrior:
    def __init__(self, name, initiative, side):
        self.name = name
        self.initiative = initiative
        self.side = side
# Tracker class creates empty list of combatants, allies/enemies, sets current combatant to 0.
class Tracker:
    def __init__(self):
        self.warriors = []
        self.allies = []
        self.enemies = []
        self.current_warrior_index = 0
    # Adds combatants to lists, then sorts by initiative in descending order.
    def add_warrior(self, name, initiative, side):
        warrior = Warrior(name, initiative, side)
        self.warriors.append(warrior)
        if warrior.side == "enemy":
            self.enemies.append(warrior.name)
        else:
            self.allies.append(warrior.name)
        self.sort_warriors()
    # Initiative sorting
    def sort_warriors(self):
        self.warriors.sort(key=lambda x: x.initiative, reverse=True)
    # Displays combatants
    def order_list(self):
        for i, warrior in enumerate(self.warriors):
            if warrior.side == "ally":
                print(f"{colorama.Fore.CYAN}{warrior.name} is an {warrior.side} with an initiative of {warrior.initiative}")
            else:
                print(f"{colorama.Fore.YELLOW}{warrior.name} is an {warrior.side} with an initiative of {warrior.initiative}")
    # Displays current combatant's turnq
    def get_current_warrior(self):
        if self.warriors:
            current = self.warriors[self.current_warrior_index]
            if current.side == "ally":
                print(f"It is {colorama.Fore.CYAN}{current.name}{colorama.Fore.WHITE}'s turn.")
            else:
                print(f"It is {colorama.Fore.YELLOW}{current.name}{colorama.Fore.WHITE}'s turn.")
        return None
    # Advances to next turn.
    def next_turn(self):
        # Checks to see if one side has been defeated or not.
        if len(self.allies) == 0:
            print(colorama.Fore.YELLOW + "All allies have been slain! The GM has earned a nap and a cookie.")
            return False
        elif len(self.enemies) == 0:
            print(colorama.Fore.CYAN + "All enemies have been slain! The players have earned waffles. WAFFLES, HO!")
            return False
        self.current_warrior_index = (self.current_warrior_index + 1) % len(self.warriors)
        self.get_current_warrior()
        return True
# Primary function
def main():
    tracker = Tracker()
    # Adds combatants to the roster
    tracker.add_warrior("Goblin King", 16, "enemy")
    tracker.add_warrior("Goblin 1", 3, "enemy")
    tracker.add_warrior("Goblin 2", 7, "enemy")
    tracker.add_warrior("Goblin 3", 9, "enemy")
    tracker.add_warrior("Goblin 4", 1, "enemy")
    tracker.add_warrior("Goblin 5", 6, "enemy")
    tracker.add_warrior("Ogre", 2, "enemy")
    tracker.add_warrior("Conan, the Librarian!", 23, "ally")
    tracker.add_warrior("Gabriella of Edgemoore", 17, "ally")
    tracker.add_warrior("Griswold the Evoker", 12, "ally")
    tracker.add_warrior("Bob the cleric", 4, "ally")
    tracker.add_warrior("Possum the Trollslayer, a Kobold of Means", 18, "ally")
    # Prints the initiative order and the first combatant in the initiative.
    print("Welcome to combat. Initiative has been rolled.")
    # Prints a count of total combatants, as well as how many are allies and enemies.
    print(f"There are {len(tracker.warriors)} combatants: {len(tracker.allies)} allies and {len(tracker.enemies)} enemies.")
    tracker.order_list()
    print("To view a list of options, type 'commands.' Or press ENTER to advance the turn.")
    tracker.get_current_warrior()
    # Handles initiative actions and conditions.
    while True:
        user_input = input("Awaiting input...")
        if not tracker.warriors:
            print(colorama.Fore.BLUE + "There are no combatants. Combat has ceased.")
            break
        if user_input == "slain":
            slain = tracker.warriors[tracker.current_warrior_index]
            print(f"{slain.name} has been slain!")
            if slain.side == "ally":
                tracker.allies.remove(slain.name)
            else:
                tracker.enemies.remove(slain.name)
            del tracker.warriors[tracker.current_warrior_index]
            if tracker.warriors:
                tracker.current_warrior_index %= len(tracker.warriors)
                if len(tracker.allies) == 0:
                    print(colorama.Fore.YELLOW + colorama.Style.BRIGHT + "All allies have been slain! The GM has earned a nap and a cookie.")
                    break
                elif len(tracker.enemies) == 0:
                    print(colorama.Fore.CYAN + colorama.Style.BRIGHT + "All enemies have been slain! The players have earned waffles. WAFFLES, HO!")
                    break
                tracker.get_current_warrior()
        elif user_input == "remains":
            print(f"There are {len(tracker.warriors)} combatants: {len(tracker.allies)} allies and {len(tracker.enemies)} enemies.")
        elif user_input == "current":
            tracker.get_current_warrior()
        elif user_input == "commands":
            print("commands: displays a list of available commands.")
            print("slain: removes current combatant from initiative and advances the turn")
            print("remains: displays a count of active combatants, as well as how many are allies and how many are enemies")
            print("current: displays the current combatant")
            print("quit: ends combat")
        elif user_input == "quit":
            print(colorama.Fore.BLUE + "Combat has ended.")
            break
        else:
            tracker.next_turn()

if __name__ == "__main__":
    main()