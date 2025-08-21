# Primary file for Advanced Initiative Tracker.

# Imports.
import uuid

# Global Constants.
UNIQUE_CONDITIONS = ("slain", "dying", "unconscious", "stable", "concentration")
CONDITIONS = (
    "blinded",
    "charmed",
    "concentration",
    "deafened",
    "dying",
    "frightened",
    "grappled",
    "incapacitated",
    "invisible",
    "paralyzed",
    "petrified",
    "poisoned",
    "prone",
    "restrained",
    "slain",
    "stable",
    "stunned",
    "unconscious"
)

# Warrior class defines combatants: name, initiative, side, AC, HP, conditions and associated durations.
class Warrior:
    def __init__(self, name, initiative, side, ac, hp_current, hp_max,hp_current_max=None, conditions=None, tiebreak_priority=0):
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
        self.tiebreak_priority = tiebreak_priority
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
        new_condition.name = new_condition.name
        if new_condition.name in UNIQUE_CONDITIONS and any(c.name == new_condition.name for c in self.conditions):
            if new_condition.name == "concentration":
                self.remove_condition("concentration")
                self.conditions.append(new_condition)
            return
        else:
            self.conditions.append(new_condition)
            if new_condition.name in ("slain", "stable"):
                self.reset_death_saves()
    # Handles removing conditions from a combatant.
    def remove_condition(self, condition_name=None, condition_id=None, silent=False):
        removed = 0
        if isinstance(condition_name, Condition):
            try:
                self.conditions.remove(condition)
                return 1
            except ValueError:
                if not silent:
                    raise ValueError("Error: Condition instance not found on this warrior.")
                return 0
        if isinstance(condition, str) and condition_name is None:
            condition_name = condition
        if condition_name is not None and condition_id is None:
            for i, c in enumerate(self.conditions):
                if c.name == condition_name:
                    del self.conditions[i]
                    return 1
                if not silent:
                    raise ValueError(f"Error: Condition '{condition_name}' not found on this warrior.")
                return 0
        if condition_name is None and condition_id is not None:
            to_remove = [c for c in self.conditions if getattr(c, "condition_id", None) == condition_id]
            removed = len(to_remove)
            for c in to_remove:
                self.conditions.remove(c)
            if removed == 0 and not silent:
                raise ValueError(f"Error: No conditions with id '{condition_id}' found on this warrior.")
            return removed
        if condition_name is not None and condition_id is not None:
            to_remove = [
                c for c in self.conditions
                if c.name == condition_name and getattr(c, "condition_id", None) == condition_id
            ]
            removed = len(to_remove)
            for c in to_remove:
                self.conditions.remove(c)
            if removed == 0 and not silent:
                raise ValueError(f"Error: No conditions named '{condition_name}' with id '{condition_id}' found on this warrior.")
            return removed
        if not silent:
            raise ValueError("Error: Please provide a condition instance, a name, an ID, or name and ID")
        return 0
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
    def __init__(self, name, duration=None, tick_timing=None, source=None, target=None, tick_owner=None, expires_with_source=None, condition_id=None):
        self.name = name.lower()
        self.duration = duration
        self.tick_timing = tick_timing.lower() if tick_timing else None
        self.source = source.lower() if isinstance(source, str) else source
        self.target = target.lower() if isinstance(target, str) else target
        self.tick_owner = tick_owner.lower() if tick_owner else None
        self.expired = False
        self.expires_with_source = expires_with_source.lower() if expires_with_source else None
        self.condition_id = condition_id or str(uuid.uuid4())
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
        # Forces timing match.
        if self.tick_timing != timing:
            return False
        # If no specific owner, always tick when timing matches.
        if not towner_name:
            return True
        # If the tick owner is the target, tick on target's turn.
        if towner_name == "target":
            if target_name is None or current_actor is None:
                return False
            return current_actor == target_name
        # If the tick owner is the source, tick on source's turn.
        if towner_name == "source":
            if source_name is None or current_actor is None:
                return False
            return current_actor == source_name
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
    # Handles moving from turn to turn.
    def next_turn(self):
        # Defines current warrior in initiative.
        current_warrior = self.warriors[self.current_warrior_index]
        # Loops through current combatant's conditions (if any) and ticks any that decrement at end of turn.
        current_warrior.tick_conditions("end", current_warrior)
        # Increments index in list of combatants.
        self.current_warrior_index += 1
        # Resets index to 0 if reaching the end of initiative list.
        if self.current_warrior_index >= len(self.warriors):
            self.current_warrior_index = 0
            self.round_number += 1
        # Defines new current warrior.
        new_warrior = self.warriors[self.current_warrior_index]
        # Loops through current combatant's conditions (if any) and ticks any that decrement at start of turn.
        new_warrior.tick_conditions("start", new_warrior)
        # Returns the new current combatant in the list.
        return new_warrior
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
        self.warriors.sort(key=lambda x: (-x.initiative, x.tiebreak_priority))
    # Handles condition removal cascade.
    def remove_condition(self, warrior, condition_name):
        # Designates conditions that break concentration.
        breaks_concentration = ("slain", "dying", "unconscious", "incapacitated", "paralyzed", "petrified", "stunned")
        # Removes conditions.
        warrior.remove_condition(condition_name, silent=True)
        # Cascades conditions that rely on other conditions.
        for other in self.warriors:
            for cond in list(other.conditions):
                if cond.source == warrior and cond.expires_with_source == condition_name:
                    other.remove_condition(cond)
        # Cascades concentration effects.
        if condition_name == "concentration":
            for other in self.warriors:
                for cond in list(other.conditions):
                    if cond.source == warrior and cond.expires_with_source == "concentration" and cond.target == other:
                        other.remove_condition(cond)
            return
        # Cascades effects that break concentration.
        elif condition_name in breaks_concentration:
            if any(cond.name == "concentration" for cond in warrior.conditions):
                self.remove_condition(warrior, "concentration")
    def get_initiative_ties(self):
        ties = {}
        for warrior in self.warriors:
            ties.setdefault(warrior.initiative, []).append(warrior)
        return {init: group for init, group in ties.items() if len(group) > 1}

# Primary function
def main():
    tracker = Tracker()

if __name__ == "__main__":
    main()