# AdvancedInit
A more robust initiative tracker compatible with the 5th Edition Dungeons and Dragons combat system based on an earlier project of mine. No trademark or copyright infringement is intended.
If you would like to use this project at your home table for a private game, please feel free. You may not use this program or its code or contents in any non-personal or commercial manner without written permission from the author.

Motivation: I have been playing various TTRPGs for most of my life, mostly Dungeons and Dragons. Given my knowledge of the game rules, I wanted to build a combat tracker to facilitate the running of the game. Since there are so many moving parts to any given combat, it felt like a good way to stretch my creative muscles and see just how far I could take the concept.

##Contributing: Constructive feedback is always welcome. If you have suggestions or feedback, please message me on the Boot.dev Discord. Thank you!

-Hours Logged: 82

Installation:
You'll need to clone the repository from GitHub (https://github.com/Beguiler87/AdvancedInit.git). If you are unsure of how to do so, this link should be helpful: https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository.
Please note, you will need Python 3 or later to run this program. If you do not know how to install that, please review the following links (YouTube may also be helpful):
For Windows:
https://www.python.org/downloads/
https://learn.microsoft.com/en-us/windows/python/beginners
For Mac OS:
https://www.python.org/downloads/macos/
https://docs.python.org/3/using/mac.html
For Linux:
Let's be honest, you probably already know enough to do this without me telling you how...

Quick Start:
Once installed, navigate to the directory within your program of choice (I used VS Code for this project) and start it with "python3 main.py". This opens the combat tracker on your screen, and you are off to the races! Click the Add Combatant button and enter the requested information. Repeat this process for all participants, and click the Start Combat button to begin.

Usage:

Adding Combatants
To add combatants to the initiative, click the Add Combatant button. A modal will pop up, requesting information. Please make sure each field is filled appropriately. You can leave the Tiebreak field blank by default. Once the fields are filled out, click the Add Combatant button, and the information will appear in the initiative panel on the left and the roster panel in the center of the screen. Once you have entered all of your combatants, click the Start Combat button. This will activate the system fully and you will be able to advance from turn to turn.
Once the Start Combat button has been clicked, the system will bring up a modal if any initiative ties were detected. This modal allows you to sort the entries to your satisfaction.
When entering combatants into the initiative tracker, make sure each name is distinct. If you have multiple entries that are otherwise identical, try to separate them with numbers (ie Goblin 1, Goblin 2, Goblin 3, etc.). More unique names (Goblin with sword, Goblin with bow, Goblin with spear, Bob the Goblin, etc.) are also sufficient.
If you're a DM who runs their monsters in groups (I certainly am), there are two options to consider in the program's current incarnation (9/17/2025). The first is to keep all of your monsters in one group under a single entry with one initiative. This is certainly the easiest way to go, since you only need to type in "orc" once and enter initiative, etc. for it a single time. However, you will run into issues with the various conditions if you do so. For example, if one orc is stunned, but another is concentrating on a spell, the concentration marker would be removed by the system automatically. To avoid this, I recommend entering each of your monsters individually. Give them the same initiative and stats, but change the name for each (ie orc 1, orc 2, orc 3, etc.). This does mean set up is a little more time-consuming, but it will certainly make combat a little smoother.

Conditions
When applying a condition to one or more targets you'll want to select a condition source (if none exists, choose None) then one or more targets. Enter the number of rounds the condition lasts, whether the rounds count down (tick timing) at the start or end of the source or target's turn (tick owner), and check the box if the condition is reliant on the source's concentration (concentration-reliant conditions will cascade off if concentration is removed). Once you've done this, check the box for the appropriate condition and click the Add Condition button.
Once a condition is applied, the program automatically counts down its duration as the Next Turn button is pressed.
A limited number of conditions will be visible in the central roster panel. If more than 3-4 conditions are applied to the same target, they are likely to expand beyond the visible area. Conditions beyond this will still be applied, but this will obviously make them harder to track. Please bear this in mind for the current version (9/17/2025).
To manually remove a condition, make sure you have the target(s) selected and the correct condition(s) checked off, then click the Clear Condition button.