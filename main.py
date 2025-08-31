# Primary file for Advanced Initiative Tracker.

# Imports.
import uuid
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, font

# Global Constants.
UNIQUE_CONDITIONS = ("slain", "dying", "unconscious", "stable", "concentration")
CONDITIONS = ("blinded", "charmed", "concentration", "deafened", "dying", "frightened", "grappled", "incapacitated", "invisible", "paralyzed", "petrified", "poisoned", "prone", "restrained", "slain", "stable", "stunned", "unconscious")
# Conditions that render a creature unable to act, more or less permanently with regards to combat. Used for detecting team wipes.
DISABLING_CONDITIONS = ("slain", "dying", "unconscious", "stable")
BREAKS_CONCENTRATION = ("slain", "unconscious", "dying", "stable", "incapacitated", "paralyzed", "stunned", "petrified")

# Warrior class defines combatants: name, initiative, side, AC, HP, conditions, and associated durations.
class Warrior:
    def __init__(self, name, initiative, side, ac, hp_current, hp_max, hp_current_max=None, conditions=None, tiebreak_priority=0):
        self.name = name
        self.initiative = initiative
        self.side = side
        self.ac = ac
        self.hp_max = hp_max
        self.hp_current_max = hp_current_max if hp_current_max is not None else hp_max
        self.hp_current = min(hp_current, self.hp_current_max)
        self.conditions = []
        self._cond_index = {}
        self.death_save_failures = 0
        self.death_save_successes = 0
        self.tiebreak_priority = tiebreak_priority
        if conditions:
            for cond in conditions:
                self.apply_condition(cond)
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
            self.apply_condition(Condition("slain"))
            dying = self._find_condition_by_name("dying")
            unconscious = self._find_condition_by_name("unconscious")
            stable = self._find_condition_by_name("stable")
            if dying is not None:
                self.remove_condition(dying)
            if unconscious is not None:
                self.remove_condition(unconscious)
            if stable is not None:
                self.remove_condition(stable)
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
                self.apply_condition(Condition("dying"))
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
    # Handles applying conditions to a combatant. Returns a token indicating what took place.
    def apply_condition(self, condition):
        name = condition.name
        if name not in CONDITIONS:
            raise ValueError(f"Error: Invalid condition name: {name}")
        is_unique = (name in UNIQUE_CONDITIONS)
        has_same = any(c.name == name for c in self.conditions)
        reset_flag = False
        token = "added"
        if name == "concentration" and has_same:
            return "concentration_replace_requested"
        elif is_unique and has_same:
            return "duplicate_ignored"
        elif name == "slain" or name == "stable":
            reset_flag = True
            token = "added_breaks_concentration"
        elif name in BREAKS_CONCENTRATION:
            token = "added_breaks_concentration"
        else:
            token = "added"
        self.conditions.append(condition)
        self._cond_index[condition.condition_id] = condition
        if reset_flag:
            self.reset_death_saves()
        return token
    # Handles removing conditions from a combatant.
    def remove_condition(self, condition):
        if condition not in self.conditions:
            return 0
        self.conditions.remove(condition)
        self._cond_index.pop(condition.condition_id, None)
        return 1
    # Handles retrieving condition id.
    def get_condition_by_id(self, condition_id):
        return self._cond_index.get(condition_id)
    # Debug helper to ensure list and dict are consistent.
    def assert_index_integrity(self):
        assert len(self._cond_index) == len(set(self._cond_index.keys()))
        assert len(self.conditions) == len(self._cond_index)
        for cond in self.conditions:
            assert cond.condition_id in self._cond_index
            assert self._cond_index[cond.condition_id] is cond
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
        self.source = source
        assert (self.source is None or hasattr(self.source, "name")), (f"Error: Invalid source: {self.source}")
        self.target = target
        assert (self.target is None or hasattr(self.target, "name")), (f"Error: Invalid target: {self.target}")
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
        # Normalizes timing case as safety net.
        timing = timing.lower() if isinstance(timing, str) else timing
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
        # Used for determining when added warriors can act, in case of mid-combat adds (summonings, animation of corpses, etc.)
        self.eligible_from_round = {}
    # Handles moving from turn to turn.
    def next_turn(self):
        # Safely handles cases where next turn is called on an empty list of combatants.
        if len(self.warriors) == 0:
            return None
        # Future proofing.
        self.current_warrior_index %= len(self.warriors)
        # Defines current warrior in initiative.
        current_warrior = self.warriors[self.current_warrior_index]
        # Loops through current combatant's conditions (if any) and ticks any that decrement at end of turn.
        current_warrior.tick_conditions("end", current_warrior)
        # Increments index in list of combatants.
        self.current_warrior_index += 1
        # Resets index to 0 and advances round number if reaching the end of initiative list.
        if self.current_warrior_index >= len(self.warriors):
            self.current_warrior_index = 0
            self.round_number += 1
        # Handles indexing for combatants inserted into an active combat.
        next_index = self.current_warrior_index
        i = 0
        while i < len(self.warriors):
            candidate = self.warriors[next_index]
            eligible_from = self.eligible_from_round.get(id(candidate), 1)
            if eligible_from <= self.round_number:
                break
            else:
                next_index += 1
                if next_index == len(self.warriors):
                    next_index = 0
                    self.round_number += 1
            i += 1
        self.current_warrior_index = next_index
        # Defines new current warrior.
        new_warrior = self.warriors[self.current_warrior_index]
        # Loops through current combatant's conditions (if any) and ticks any that decrement at start of turn.
        new_warrior.tick_conditions("start", new_warrior)
        self.check_team_able()
        # Returns the new current combatant in the list.
        return new_warrior
    # Checks for disabled combatants.
    def _is_disabled(self, warrior):
        return any(c.name in DISABLING_CONDITIONS for c in warrior.conditions)
    # Checks for disabled sides.
    def check_team_able(self):
        allies_disabled = len(self.allies) > 0 and all(self._is_disabled(w) for w in self.allies)
        enemies_disabled = len(self.enemies) > 0 and all(self._is_disabled(w) for w in self.enemies)
        return {"allies_disabled": allies_disabled, "enemies_disabled": enemies_disabled}
    # Adds combatants to lists, determining what round they can first act in if they are added in the midst of combat.
    def add_warrior(self, name, initiative, side, ac, hp_current, hp_max, conditions):
        current_ref = None
        warrior = Warrior(name, initiative, side, ac, hp_current, hp_max, conditions)
        if len(self.warriors) == 0:
            self.warriors.append(warrior)
            self.sort_warriors()
            self.current_warrior_index = 0
            if warrior.side == "enemy":
                self.enemies.append(warrior)
            else:
                self.allies.append(warrior)
            self.eligible_from_round[id(warrior)] = self.round_number
        else:
            current_ref = self.warriors[self.current_warrior_index]
            self.warriors.append(warrior)
            if warrior.side == "enemy":
                self.enemies.append(warrior)
            else:
                self.allies.append(warrior)
            self.sort_warriors()
            self.current_warrior_index = self.warriors.index(current_ref)
            new_index = self.warriors.index(warrior)
            if new_index > self.current_warrior_index:
                self.eligible_from_round[id(warrior)] = self.round_number
            else:
                self.eligible_from_round[id(warrior)] = self.round_number + 1
    # Initiative sorting.
    def sort_warriors(self):
        self.warriors.sort(key=lambda x: (-x.initiative, x.tiebreak_priority))
    # Handles condition removal cascade.
    def remove_condition(self, warrior, condition_id):
        # Establishes specific instance of condition and returns an error if that instance is not found.
        c_instance = warrior.get_condition_by_id(condition_id)
        if c_instance is None:
            return {"removed":0, "primary_id": condition_id, "cascaded":[], "reason":"not_found"}
        # Removes conditions.
        removed = warrior.remove_condition(c_instance)
        if removed == 0:
            return {"removed":0, "primary_id": condition_id, "cascaded":[], "reason":"not_found"}
        anchor = "concentration" if c_instance.name == "concentration" else c_instance.name
        temp_list = []
        for w in self.warriors:
            for cond in list(w.conditions):
                if cond.source is warrior and cond.expires_with_source == anchor:
                    c = (w, cond)
                    temp_list.append(c)
        cascaded_list = []
        for w, cond in temp_list:
            removed = w.remove_condition(cond)
            if removed:
                cascaded_list.append(cond.condition_id)
        self.check_team_able()
        return {"removed": 1, "primary_id": condition_id, "cascaded": cascaded_list}
    # Handles initiative ties, allowing the user to manually sort tied combatants in the gui.
    def get_initiative_ties(self):
        ties = {}
        for warrior in self.warriors:
            ties.setdefault(warrior.initiative, []).append(warrior)
        return {init: group for init, group in ties.items() if len(group) > 1}

# Window class used for creating a functional GUI.
class Window:
    # Defines the window and inputs.
    def __init__(self, tracker, title="Combat Tracker", open_add_modal_on_start=True, cons_catalog=CONDITIONS, breaks_conc=BREAKS_CONCENTRATION, disab_conditions=DISABLING_CONDITIONS, hotkeys=None):
        # parent widget creating an instance of Tk
        if not isinstance(tracker, Tracker):
            raise TypeError("Error: no Tracker instance present.")
        self.tracker = tracker
        self.open_add_modal_on_start = open_add_modal_on_start
        self.cons_catalog = cons_catalog
        self.breaks_conc = breaks_conc
        self.disab_conditions = disab_conditions
        self.hotkeys = hotkeys
        self._suppress_select = False
        self._iid_to_warrior = {}
        self.selected_warrior = None
        self.colors = {
            "panel_bg": "lemonchiffon3",
            "list_bg": "ivory2",
            "highlight": "turquoise3",
            "slain": "gray60",
            "border": "black",
            "button_bg": "NavajoWhite4",
            "label_bg": "NavajoWhite4"
        }
        self.tags = {"current": "current_actor", "slain": "slain"}
        # Builds the tkinter root.
        self.root = tk.Tk()
        # Pulls the title into the gui display.
        self.root.title(title)
        # Calculates user's screen size.
        screenw_full = self.root.winfo_screenwidth()
        screenh_full = self.root.winfo_screenheight()
        # Calculates small offset to prevent overflow in screen.
        screenw = int(screenw_full * .90)
        screenh = int(screenh_full * .90)
        # Screen centering equations.
        x = int((screenw_full - screenw) // 2)
        y = int((screenh_full - screenh) // 2)
        # Generates full screen size, defaulting to 16:9 aspect ratio.
        full_screen = f"{screenw}x{screenh}+{x}+{y}"
        self.root.geometry(full_screen)
        # Establishes minimum screen size for smaller displays.
        self.root.minsize(1120, 630)
        # Note: screen size is, by default, manually adjustable by the user.
        # Configuring columns and rows within screen, defining the grid.
        self.root.grid_columnconfigure(0, weight=2, uniform="cols")
        self.root.grid_columnconfigure(1, weight=3, uniform="cols")
        self.root.grid_columnconfigure(2, weight=2, uniform="cols")
        self.root.grid_rowconfigure(0, weight=3, uniform="rows")
        self.root.grid_rowconfigure(1, weight=1, uniform="rows")
        # Sets up the panel frames in the gui.
        self._setup_left_frame()
        # Configures frames that fit into the grid, providing appearance of a border.
        self.center_frame_border = tk.Frame(self.root, bg=self.colors["border"])
        self.center_frame_border.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)
        self.right_frame_border = tk.Frame(self.root, bg=self.colors["border"])
        self.right_frame_border.grid(row=0, column=2, sticky="nsew", padx=2, pady=2)
        self.log_frame_border = tk.Frame(self.root, bg=self.colors["border"])
        self.log_frame_border.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=2, pady=2)
        self.center_frame_border.grid_columnconfigure(0, weight=1)
        self.center_frame_border.grid_rowconfigure(0, weight=1)
        self.right_frame_border.grid_columnconfigure(0, weight=1)
        self.right_frame_border.grid_rowconfigure(0, weight=1)
        self.log_frame_border.grid_columnconfigure(0, weight=1)
        self.log_frame_border.grid_rowconfigure(0, weight=1)
        # Configures panels that fit into the previously established borders.
        self.center_frame = tk.Frame(self.center_frame_border, bg=self.colors["panel_bg"])
        self.right_frame = tk.Frame(self.right_frame_border, bg=self.colors["panel_bg"])
        self.log_frame = tk.Frame(self.log_frame_border, bg=self.colors["panel_bg"])
        # Snaps the panel section frames into the grid.
        self.center_frame.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.right_frame.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.log_frame.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
    # Defines left panel and contents.
    def _setup_left_frame(self):
        # Establishes 'borders' for frame.
        self.left_frame_border = tk.Frame(self.root, bg=self.colors["border"])
        self.left_frame_border.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self.left_frame_border.grid_columnconfigure(0, weight=1)
        self.left_frame_border.grid_rowconfigure(0, weight=1)
        self.left_frame = tk.Frame(self.left_frame_border, bg=self.colors["panel_bg"])
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        # Left panel frame configuration.
        self.left_frame.grid_columnconfigure(0, weight=1)
        self.left_frame.grid_rowconfigure(0, weight=0)
        self.left_frame.grid_rowconfigure(1, weight=1)
        # Child frame for round counter and next turn buttons.
        self.left_header = tk.Frame(self.left_frame, bg=self.colors["border"])
        self.left_header.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        self.left_header.grid_columnconfigure(0, weight=1)
        self.left_header.grid_columnconfigure(1, weight=0)
        self.left_header.grid_rowconfigure(0, weight=1)
        # Round counter.
        self.round_counter = tk.Frame(self.left_header, bg=self.colors["button_bg"])
        self.round_counter.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        # Current round display.
        self.round_var = tk.StringVar(value=f"Round: {self.tracker.round_number}")
        self.round_label = tk.Label(self.round_counter, textvariable=self.round_var, font=("TkDefaultFont", 14, "bold"), bg=self.colors["label_bg"])
        self.round_label.grid(row=0, column=0, sticky="w")
        # Frame for next turn button.
        self.next_turn = tk.Frame(self.left_header, bg=self.colors["border"])
        self.next_turn.grid(row=0, column=1, sticky="nsew", padx=1, pady=1)
        # Next Turn button configuration.
        self.nxt_turn_btn = ttk.Button(self.next_turn, text="Next Turn", command=self._on_next_turn)
        self.nxt_turn_btn.grid(row=0, column=0, sticky="e", padx=1, pady=1)
        # Child frame for initiative order lists.
        self.left_list_container = tk.Frame(self.left_frame, bg=self.colors["border"])
        self.left_list_container.grid(row=1, column=0, sticky="nsew", padx=1, pady=1)
        self.left_list_container.grid_columnconfigure(0, weight=1) # Initiative list.
        self.left_list_container.grid_columnconfigure(1, weight=0) # Scrollbar.
        self.left_list_container.grid_rowconfigure(0, weight=1)
        # Initiative order list configuration.
        self.init_tree = ttk.Treeview(self.left_list_container, columns=("Name", "Init"), show="headings", selectmode="browse")
        style = ttk.Style(self.root)
        style.configure("Treeview", background=self.colors["list_bg"], fieldbackground=self.colors["list_bg"])
        self.init_tree.tag_configure(self.tags["current"], background=self.colors["highlight"])
        self.init_tree.tag_configure(self.tags["slain"], background=self.colors["slain"])
        self.init_tree.heading("Name", text="Name")
        self.init_tree.heading("Init", text="Init")
        self.init_tree.column("Name", width=200, anchor="w", stretch=True)
        self.init_tree.column("Init", width=60, anchor="e", stretch=False)
        # Creates the initiative scrollbar.
        self.init_scrollbar = ttk.Scrollbar(self.left_list_container, orient="vertical", command=self.init_tree.yview)
        # Hooks the scrollbar to the initiative order list.
        self.init_tree.configure(yscrollcommand=self.init_scrollbar.set)
        # Snaps the initiative list and scrollbar into the correct part of the gui.
        self.init_tree.grid(row=0, column=0, sticky="nsew")
        self.init_scrollbar.grid(row=0, column=1, sticky="ns")
        self.init_tree.bind("<<TreeviewSelect>>", self._on_initiative_select)
    # Used to refresh the initiative display.
    def render_initiative(self):
        if len(self.tracker.warriors) == 0:
            self._clear_initiative_list()
            return
        self._clear_initiative_list()
        for i, w in enumerate(self.tracker.warriors):
            tags = []
            if w.is_dead():
                tags.append(self.tags["slain"])
            if i == self.tracker.current_warrior_index:
                tags.append(self.tags["current"])
            values = (w.name, w.initiative)
            iid = str(id(w))
            self.init_tree.insert("", "end", iid=iid, values=values, tags=tags)
            self._iid_to_warrior[iid] = w
        current = self.tracker.warriors[self.tracker.current_warrior_index]
        current_iid = str(id(current))
        self._suppress_select = True
        self.init_tree.selection_set(current_iid)
        self.init_tree.focus(current_iid)
        self.init_tree.see(current_iid)
        self._suppress_select = False
        if len(self.tracker.warriors) >= 2:
            self.nxt_turn_btn.state(["!disabled"])
        else:
            self.nxt_turn_btn.state(["disabled"])
    # Helper method to clear initiative list between refreshes.
    def _clear_initiative_list(self):
        self.init_tree.delete(*self.init_tree.get_children())
        self._iid_to_warrior = {}
    # Retrieves current warrior identification.
    def _on_initiative_select(self):
        if self._suppress_select:
            return
        iid_tuple = self.init_tree.selection()
        if len(iid_tuple) == 0:
            return
        w_iid = iid_tuple[0]
        w = self._iid_to_warrior.get(w_iid)
        if w is None:
            return
        self.selected_warrior = w
    # Ties tracker.next_turn() and render_initiative() together.
    def _on_next_turn(self):
        # Guards against advancing turn if only one warrior on the list.
        if len(self.tracker.warriors) < 2:
            return
        # Advances the tracker by calling next_turn() and exiting safely if the roster is empty.
        new_actor = self.tracker.next_turn()
        if new_actor is None:
            return
        # Syncs gui by advancing round number if appropriate, updating selected warrior, and updates the highlight.
        self.round_var.set(f"Round: {self.tracker.round_number}")
        self.selected_warrior = new_actor
        self.render_initiative()
        # Checks for team wipe and notifies if true.
        status = self.tracker.check_team_able()
        if status["allies_disabled"]: messagebox.showinfo("Combat", "All allies are defeated. The DM has earned a nap and a cookie!")
        if status["enemies_disabled"]: messagebox.showinfo("Combat", "All enemies are defeated. The party have earned waffles. Waffles, Ho!")
    

# Primary function/entry point.
#def main():
    #tracker = Tracker()

if __name__ == "__main__":
    tracker = Tracker()
    window = Window(tracker)
    window.root.mainloop()
    #main()