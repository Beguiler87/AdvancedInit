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
    def __init__(self, name, initiative, side, ac, hp_current, hp_max, hp_current_max=None, conditions=None, tiebreak_priority=0):
        self.name = name
        self.initiative = initiative
        self.side = side
        self.ac = ac
        self.hp_max = hp_max
        self.hp_current_max = hp_current_max if hp_current_max is not None else hp_max
        self.hp_current = min(hp_current, self.hp_current_max)
        self.conditions = conditions if conditions is not None else []
        self.death_save_failures = 0
        self.death_save_successes = 0
        self.tiebreak_priority = tiebreak_priority
    # Handles a combatant's maximum hp receiving a temporary buff and any associated healing effect.
    def buff_max_hp(self, x, healing=False):
        if x <= 0:
            raise ValueError(f"Error: {x} must be greater than 0.")
        if self.is_dead():
            return
        self.hp_current_max += x
        if healing:
            self.heal(x)
        self.hp_current = min(self.hp_current, self.hp_current_max)
    # Handles a combatant's maximum hp receiving a debuff and potential side effects.
    def debuff_max_hp(self, x):
        if x <= 0:
            raise ValueError(f"Error: {x} must be greater than 0.")
        if self.is_dead():
            return
        self.hp_current_max = max(self.hp_current_max - x, 0)
        if self.hp_current_max <= 0:
            self.hp_current = 0
            self.hp_current_max = 0
            self.apply_condition(Condition("slain"))
            return
        self.take_damage(x)
        self.hp_current = min(self.hp_current, self.hp_current_max)
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
            self.apply_condition(Condition("slain"))
            return "slain"
        # Provides conditions for when the target is an ally and reduced to 0 hp or less
        if self.hp_current <= 0 and self.side == "ally":
            # If the target is an ally, checks for massive damage
            if self.hp_current <= -self.hp_current_max:
                self.hp_current = 0
                self.apply_condition(Condition("slain"))
                dying = self._find_condition_by_name("dying")
                if dying is not None:
                    self.remove_condition(dying)
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
                        self.apply_condition(Condition("slain"))
                        dying = self._find_condition_by_name("dying")
                        if dying is not None:
                            self.remove_condition(dying)
                        return "slain"
                    return "dying"
                self.hp_current = 0
                return "dying"
        return
    # Helper method for finding conditions by name from string type.
    def _find_condition_by_name(self, name: str):
        return next((c for c in self.conditions if getattr(c, "name", "").lower() == name.lower()), None)
    # Handles a combatant receiving healing.
    def heal(self, amount, resurrection_effect=False):
        if self.is_dead():
            if resurrection_effect:
                slain = self._find_condition_by_name("slain")
                if slain is not None:
                    self.remove_condition(slain)
            else:
                return
        self.reset_death_saves()
        unconscious = self._find_condition_by_name("unconscious")
        dying = self._find_condition_by_name("dying")
        stable = self._find_condition_by_name("stable")
        if unconscious is not None:
            self.remove_condition(unconscious)
        if dying is not None:
            self.remove_condition(dying)
        if stable is not None:
            self.remove_condition(stable)
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
        is_unique = new_condition.name in UNIQUE_CONDITIONS
        has_same = any(c.name == new_condition.name for c in self.conditions)
        if is_unique and new_condition.name == "concentration":
            if has_same:
                return "concentration_exists"
            else:
                self.conditions.append(new_condition)
                return "added"
        if is_unique and has_same:
            return "duplicate_ignored"
        else:
            self.conditions.append(new_condition)
            if new_condition.name in ("slain", "stable"):
                self.reset_death_saves()
            return "added"
    # Handles removing conditions from a combatant.
    def remove_condition(self, condition):
        removed = 0
        if not isinstance(condition, Condition):
            raise TypeError(f"Error: {condition} is not a Condition instance.")
        elif condition not in self.conditions:
            raise ValueError(f"Error: {condition} not found on target combatant.")
        else:
            self.conditions.remove(condition)
            removed = 1
        return removed
    # Handles the mechanics of failed death saving throws.
    def fail_death_saves(self, is_critical=False):
        if self.hp_current > 0:
            return
        if self.is_dead():
            return "slain"
        self.death_save_failures += 2 if is_critical else 1
        if self.death_save_failures >= 3:
            dying = self._find_condition_by_name("dying")
            if dying:
                self.remove_condition(dying)
            self.apply_condition(Condition("slain"))
            return "slain"
    # Handles the mechanics of successful death saving throws.
    def succeed_death_saves(self, is_critical=False):
        if self.hp_current > 0:
            return
        if self.is_dead():
            return "slain"
        slain = self._find_condition_by_name("slain")
        unconscious = self._find_condition_by_name("unconscious")
        dying = self._find_condition_by_name("dying")
        self.death_save_successes += 1
        if is_critical:
            if slain is not None:
                self.remove_condition(slain)
            if unconscious is not None:
                self.remove_condition(unconscious)
            if dying is not None:
                self.remove_condition(dying)
            self.hp_current = 1
            self.reset_death_saves()
            return
        if self.death_save_successes == 3:
            if dying is not None:
                self.remove_condition(dying)
            self.apply_condition(Condition("stable"))
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
        if duration is None:
            self.duration = duration
        elif isinstance(duration, bool):
            raise TypeError("Error: Duration must be None or a whole number greater than 0.")
        elif isinstance(duration, int) and duration >= 0:
            self.duration = duration
        else:
            raise TypeError("Error: Duration must be None or a whole number greater than 0.")
        self.tick_timing = tick_timing.lower() if tick_timing else None
        assert self.tick_timing in (None, "start", "end"), (f"Error: Invalid tick_timing: {self.tick_timing}")
        self.source = source.lower() if isinstance(source, str) else source
        self.target = target.lower() if isinstance(target, str) else target
        self.tick_owner = tick_owner.lower() if tick_owner else None
        assert self.tick_owner in (None, "source", "target"), (f"Error: Invalid tick_owner: {self.tick_owner}")
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