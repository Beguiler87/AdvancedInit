# Primary file for Advanced Initiative Tracker.

# Global Constants.
UNIQUE_CONDITIONS = ["slain", "dying", "unconscious", "stable"]

# Registry of conditions.
class ConditionRegistry:
    CONDITIONS = [
        "blinded",
        "charmed",
        "concentration",
        "deafened",
        "frightened",
        "grappled",
        "incapacitated",
        "invisible",
        "paralyzed",
        "petrified",
        "poisoned",
        "prone",
        "restrained",
        "stunned",
        "unconscious"
    ]

# Warrior class defines combatants: name, initiative, side, AC, HP, conditions and associated durations.
class Warrior:
    def __init__(self, name, initiative, side, ac, hp_current, hp_max,hp_current_max=None, conditions=None):
        self.name = name
        self.initiative = initiative
        self.side = side
        self.ac = ac
        self.hp_current = hp_current
        self.hp_max = hp_max
        self.hp_current_max = hp_current_max if hp_current_max is not None else hp_max
        self.hp_current = min(hp_current, self.hp_current_max)
        self.conditions = conditions if conditions is not None else []
        self.death_save_failures = 0
        self.death_save_successes = 0
    # Handles a combatant taking damage.
    def take_damage(self, amount, is_critical=False):
        # Checks if the target is dead already
        if self.is_dead():
            return "slain"
        # Defines whether a target is already at 0
        was_at_zero = (self.hp_current == 0)
        # If not, adjusts current hp
        self.hp_current -= amount
        # If the target is an enemy and reduced to 0 hp or less, marks them as dead
        if self.hp_current <= 0 and self.side == "enemy":
            self.hp_current = 0
            self.apply_condition("slain")
            return "slain"
        # Provides conditions for when the target is an ally and reduced to 0 hp or less
        if self.hp_current <= 0 and self.side == "ally":
            # If the target is an ally, checks for massive damage
            if self.hp_current <= -self.hp_current_max:
                self.hp_current = 0
                self.apply_condition("slain")
                self.remove_condition("dying")
                return "slain"
            # Provides cases for when the target is an ally and not killed outright
            else:
                # If the ally is dropped to 0 hp, they are marked as dying
                self.apply_condition("dying")
                # If the ally was already at 0, begins accruing death save failures
                if was_at_zero:
                    failures = 2 if is_critical else 1
                    self.death_save_failures += failures
                    if self.death_save_failures >= 3:
                        self.apply_condition("slain")
                        self.remove_condition("dying")
                        return "slain"
                    return "dying"
                self.hp_current = 0
                return "dying"
        return
    # Handles a combatant receiving healing.
    def heal(self, amount, resurrection_effect=False):
        if self.is_dead():
            if resurrection_effect:
                self.reset_death_saves()
                self.remove_condition("slain")
            else:
                return
        self.reset_death_saves()
        self.remove_condition("unconscious", silent=True)
        self.remove_condition("dying", silent=True)
        self.remove_condition("stable", silent=True)
        self.hp_current += amount
        if self.hp_current > self.hp_current_max:
            self.hp_current = self.hp_current_max
        return
    # Helper function for checking death status.
    def is_dead(self):
        return any(c.name.lower() == "slain" for c in self.conditions)
    # Helper function for checking unconscious status.
    def is_unconscious(self):
        return any(c.name.lower() == "unconscious" for c in self.conditions)
    # Handles applying conditions to a combatant.
    def apply_condition(self, condition):
        # Checks if the condition is a Condition instance or not
        if isinstance(condition, Condition):
            new_condition = condition
        # If condition is not a Condition instance, converts
        else:
            new_condition = Condition(condition)
        new_condition.name = new_condition.name.lower()
        if new_condition.name in UNIQUE_CONDITIONS and any(c.name == new_condition.name for c in self.conditions):
            return
        else:
            self.conditions.append(new_condition)
            if new_condition.name in ("slain", "stable"):
                self.reset_death_saves()
    # Handles removing conditions from a combatant.
    def remove_condition(self, condition, silent=False):
        condition_name = condition.lower() if isinstance(condition, str) else condition.name.lower()
        for c in self.conditions:
            if c.name.lower() == condition_name:
                self.conditions.remove(c)
                return
        if not silent:
            raise ValueError(f"Error: Condition '{condition_name}' not found in log.")
    # Handles the mechanics of failed death saving throws.
    def fail_death_saves(self, is_critical=False):
        if self.hp_current > 0:
            return
        if self.is_dead():
            return "slain"
        self.death_save_failures += 2 if is_critical else 1
        if self.death_save_failures >= 3:
            self.remove_condition("dying")
            self.apply_condition("slain")
            return "slain"
    # Handles the mechanics of successful death saving throws.
    def succeed_death_saves(self, is_critical=False):
        if self.hp_current > 0:
            return
        if self.is_dead():
            return "slain"
        self.death_save_successes += 1
        if is_critical:
            self.remove_condition("slain", silent=True)
            self.remove_condition("unconscious", silent=True)
            self.remove_condition("dying", silent=True)
            self.hp_current = 1
            self.reset_death_saves()
            return
        if self.death_save_successes == 3:
            self.remove_condition("dying")
            self.apply_condition("stable")
            self.reset_death_saves()
    # Resets counts associated with death saving throws when necessary.
    def reset_death_saves(self):
        self.death_save_successes = 0
        self.death_save_failures = 0
    # Handles condition timers.
    def tick_conditions(self, timing, current_actor=None):
        # Loops through a copy of the conditions affecting each combatant.
        for condition in list(self.conditions):
            # Checks to see if each condition has a timer and when that timer should tick down. Decrements timer when appropriate.
            if condition.should_tick(timing, current_actor) and condition.tick():
                    # When the timer reaches 0 (ie. when condition.tick() returns "True"), the condition is removed.
                    self.remove_condition(condition)

# Conditions class defines various combat conditions.
class Condition:
    def __init__(self, name, duration=None, tick_timing=None, source=None, target=None, tick_owner=None, expires_with_source=None):
        self.name = name
        self.duration = duration
        self.tick_timing = tick_timing
        self.source = source
        self.target = target
        self.tick_owner = tick_owner
        self.expired = False
        self.expires_with_source = expires_with_source
    # Checks condition duration and decrements it, but never below 0. 0 is the expiration condition and will return True.
    def tick(self):
        if self.duration is None:
            return False
        if self.duration > 0:
            self.duration -= 1
        if self.duration == 0 and not self.expired:
            self.expired = True
            return True
        return False
    # Indicates when a condition duration should tick. Returns True to indicate ticking should occur.
    def should_tick(self, timing, current_actor):
        # Helper function to normalize names.
        def normalize(value):
            if isinstance(value, Warrior):
                return value.name.lower()
            elif isinstance(value, str):
                return value.lower()
            else:
                return None
        # Normalizes variable names to lower case for comparison.
        current_actor = normalize(current_actor)
        target_name = normalize(self.target)
        source_name = normalize(self.source)
        towner_name = normalize(self.tick_owner)
        # Fail early if unexpected types are encountered
        if current_actor is None or target_name is None or source_name is None:
            return False
        # Forces timing match.
        if self.tick_timing != timing:
            return False
        # If no specific owner, always tick when timing matches.
        if not towner_name:
            return True
        # If the tick owner is the target, tick on target's turn.
        if towner_name == "target" and current_actor == target_name:
            return True
        # If the tick owner is the source, tick on source's turn.
        if towner_name == "source" and current_actor == source_name:
            return True
        # Returns False by default.
        return False


# Tracker class creates empty list of combatants, allies/enemies, sets current combatant to 0.
class Tracker:
    def __init__(self):
        self.warriors = []
        self.allies = []
        self.enemies = []
        self.current_warrior_index = 0
        self.round_number = 1
    # Adds combatants to lists, then sorts by initiative in descending order.
    def add_warrior(self, name, initiative, side, ac, hp_current, hp_max, conditions):
        warrior = Warrior(name, initiative, side, ac, hp_current, hp_max, conditions)
        self.warriors.append(warrior)
        if warrior.side == "enemy":
            self.enemies.append(warrior.name)
        else:
            self.allies.append(warrior.name)
        self.sort_warriors()
    # Initiative sorting.
    def sort_warriors(self):
        self.warriors.sort(key=lambda x: x.initiative, reverse=True)
    

# Primary function
def main():
    tracker = Tracker()

if __name__ == "__main__":
    main()