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
        return warrior
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
        self.root = tk.Tk()
        self.open_add_modal_on_start = open_add_modal_on_start
        self.cons_catalog = cons_catalog
        self.breaks_conc = breaks_conc
        self.disab_conditions = disab_conditions
        self.hotkeys = hotkeys
        self._suppress_select = False
        self._iid_to_warrior = {}
        self.selected_warrior = None
        self._combat_started = False
        self.var_target = tk.StringVar()
        self._target_values = []
        self.var_amount = tk.StringVar()
        self._target_index_to_warrior = []
        self.var_resurrection = tk.BooleanVar(value=False)
        self.status_text = tk.StringVar(value="")
        self._cond_vars = {}
        self._cond_checks = {}
        self.var_cond_duration = tk.StringVar(value="")
        self.var_cond_tick_timing = tk.StringVar(value="start")
        self.var_cond_tick_owner = tk.StringVar(value="target")
        self.var_cond_concentration_tie = tk.BooleanVar(value=False)
        self.var_cond_source = tk.StringVar(value="None")
        self._cond_targets_index_to_warrior = []
        self._conc_tie_counts = {}
        self._cond_cached_selection = {"source": "None", "targets": set(), "scroll": 0}
        self._cond_checks = {}
        self.colors = {
            "panel_bg": "lemonchiffon3",
            "list_bg": "ivory",
            "highlight": "turquoise3",
            "slain": "gray60",
            "border": "black",
            "button_bg": "NavajoWhite4",
            "label_bg": "NavajoWhite4"
        }
        self.tags = {"current": "current_actor", "slain": "slain"}
        self._roster_iid_to_warrior = {}
        # Builds the tkinter root.
        self.root.withdraw() # Hides the first iteration of the gui window for better sizing operation.
        # Pulls the title into the gui display.
        self.root.title(title)
        # Calculates user's screen size.
        screenw_full = self.root.winfo_screenwidth()
        screenh_full = self.root.winfo_screenheight()
        # Calculates small offset to prevent overflow in screen.
        tw = int(screenw_full * .90)
        th = int(screenh_full * .90)
        # Clamps aspect ratio.
        if tw / th > 16/9:
            tw = int(th * 16/9)
        else:
            th = int(tw * 9/16)
        screenw = tw
        screenh = th
        # Screen centering equations.
        x = int((screenw_full - screenw) // 2)
        y = int((screenh_full - screenh) // 2)
        # Generates full screen size, defaulting to 16:9 aspect ratio.
        full_screen = f"{screenw}x{screenh}+{x}+{y}"
        self.root.geometry(full_screen)
        self.root.update_idletasks()
        self.root.deiconify()
        self.root.after_idle(self.root.geometry, full_screen)
        # Establishes minimum screen size for smaller displays.
        self.root.minsize(1120, 630)
        # Note: screen size is, by default, manually adjustable by the user.
        # Configuring columns and rows within screen, defining the grid.
        self.root.grid_columnconfigure(0, weight=2, uniform="cols")
        self.root.grid_columnconfigure(1, weight=4, uniform="cols")
        self.root.grid_columnconfigure(2, weight=2, uniform="cols")
        self.root.grid_rowconfigure(0, weight=3, uniform="rows")
        self.root.grid_rowconfigure(1, weight=1, uniform="rows")
        # Sets up the panel frames in the gui.
        self._setup_left_frame()
        self._setup_central_frame()
        self._setup_right_frame()
        self._update_concentration_toggle_state()
        self._setup_log_frame()
    # Defines panels and contents.
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
        self.nxt_turn_btn.state(["disabled"])
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
    def _setup_central_frame(self):
        # Central panel frame configuration.
        self.center_frame_border = tk.Frame(self.root, bg=self.colors["border"])
        self.center_frame_border.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)
        self.center_frame_border.grid_columnconfigure(0, weight=1)
        self.center_frame_border.grid_rowconfigure(0, weight=1)
        self.center_frame = tk.Frame(self.center_frame_border, bg=self.colors["panel_bg"])
        self.center_frame.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.center_frame.grid_columnconfigure(0, weight=1)
        self.center_frame.grid_rowconfigure(0, weight=1)
        # Child frame for central panel.
        self.central_header = tk.Frame(self.center_frame, bg=self.colors["border"])
        self.central_header.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self.central_header.grid_columnconfigure(0, weight=1)
        self.central_header.grid_columnconfigure(1, weight=0)
        self.central_header.grid_rowconfigure(0, weight=1)
        # Child frame for central list.
        self.central_list = tk.Frame(self.central_header, bg=self.colors["list_bg"])
        self.central_list.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.central_list.grid_columnconfigure(0, weight=1)
        self.central_list.grid_columnconfigure(1, weight=0)
        self.central_list.grid_rowconfigure(0, weight=1)
        self.central_list.grid_rowconfigure(1, weight=0)
        # Creates roster treeview.
        self.roster = ttk.Treeview(self.central_list, columns=("Name", "AC", "HP", "Max HP", "Conditions", "Fail", "Pass"), show="headings", selectmode="browse")
        self.roster.heading("Name", text="Name")
        self.roster.heading("AC", text="AC")
        self.roster.heading("HP", text="HP")
        self.roster.heading("Max HP", text="Max HP")
        self.roster.heading("Conditions", text="Conditions")
        self.roster.heading("Fail", text="Fail")
        self.roster.heading("Pass", text="Pass")
        style = ttk.Style(self.root)
        style.configure("Treeview", background=self.colors["list_bg"], fieldbackground=self.colors["list_bg"])
        self.roster.column("Name", width=200, anchor="w", stretch=True)
        self.roster.column("AC", width=45, anchor="w", stretch=False)
        self.roster.column("HP", width=70, anchor="w", stretch=False)
        self.roster.column("Max HP", width=70, anchor="w", stretch=False)
        self.roster.column("Conditions", width=20, anchor="w", stretch=True)
        self.roster.column("Fail", width=40, anchor="w", stretch=False)
        self.roster.column("Pass", width=40, anchor="w", stretch=False)
        # Creates the roster scrollbars.
        self.roster_vert = ttk.Scrollbar(self.central_list, orient="vertical", command=self.roster.yview)
        self.roster_horiz = ttk.Scrollbar(self.central_list, orient="horizontal", command=self.roster.xview)
        # Hooks the scrollbars to the roster list.
        self.roster.configure(yscrollcommand=self.roster_vert.set)
        self.roster.configure(xscrollcommand=self.roster_horiz.set)
        # Snaps the roster list and scrollbars into the correct part of the gui.
        self.roster.grid(row=0, column=0, sticky="nsew")
        self.roster_vert.grid(row=0, column=1, sticky="ns")
        self.roster_horiz.grid(row=1, column=0, sticky="ew")
        self.roster.bind("<<TreeviewSelect>>", self._on_roster_select)
    def _setup_right_frame(self):
        # Right panel frame configuration.
        self.right_frame_border = tk.Frame(self.root, bg=self.colors["border"])
        self.right_frame_border.grid(row=0, column=2, sticky="nsew", padx=2, pady=2)
        self.right_frame_border.grid_columnconfigure(0, weight=1)
        self.right_frame_border.grid_rowconfigure(0, weight=1)
        self.right_frame = tk.Frame(self.right_frame_border, bg=self.colors["panel_bg"])
        self.right_frame.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(0, weight=0)
        self.right_frame.grid_rowconfigure(1, weight=0)
        self.right_frame.grid_rowconfigure(2, weight=0)
        self.right_frame.grid_rowconfigure(4, weight=0)
        self.right_frame.grid_rowconfigure(3, weight=0)
        # Sets up 'Add Combatant' button.
        self.add_combatant = tk.Frame(self.right_frame, bg=self.colors["border"])
        self.add_combatant.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        self.add_combatant.grid_columnconfigure(0, weight=1)
        self.add_combatant.grid_rowconfigure(0, weight=1)
        self.add_combatant_frame = tk.Frame(self.add_combatant, bg=self.colors["button_bg"])
        self.add_combatant_frame.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        self.add_combatant_frame.grid_columnconfigure(0, weight=1)
        self.add_combatant_frame.grid_rowconfigure(0, weight=1)
        # 'Add Combatant' button configuration.
        self.add_combat_btn = ttk.Button(self.add_combatant_frame, text="Add Combatant", command=self._open_add_warrior_modal)
        self.add_combat_btn.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        # Sets up 'Start Combat' button.
        self.strt_frame = tk.Frame(self.right_frame, bg=self.colors["border"])
        self.strt_frame.grid(row=1, column=0, sticky="ew", padx=1, pady=1)
        self.strt_frame.grid_columnconfigure(0, weight=1)
        self.strt_frame.grid_rowconfigure(0, weight=1)
        self.strt_btn_frame = tk.Frame(self.strt_frame, bg=self.colors["button_bg"])
        self.strt_btn_frame.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        self.strt_btn_frame.grid_columnconfigure(0, weight=1)
        self.strt_btn_frame.grid_rowconfigure(0, weight=1)
        # 'Start Combat' button configuration
        self.start_combat_btn = ttk.Button(self.strt_btn_frame, text="Start Combat", command=self._on_start_combat)
        self.start_combat_btn.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        # Sets up HP management frame above the 'Damage' and 'Heal' buttons.
        self.hp_mng_border = tk.Frame(self.right_frame, bg=self.colors["border"])
        self.hp_mng_border.grid(row=2, column=0, sticky="ew", padx=1, pady=1)
        self.hp_mng_border.grid_columnconfigure(0, weight=1)
        self.hp_mng_border.grid_rowconfigure(0, weight=1)
        self.hp_mng = tk.Frame(self.hp_mng_border, bg=self.colors["panel_bg"])
        self.hp_mng.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.hp_mng.grid_columnconfigure(0, weight=3, uniform="r2")
        self.hp_mng.grid_columnconfigure(1, weight=1, uniform="r2", minsize = 50)
        self.hp_mng.grid_columnconfigure(2, weight=1, uniform="r2")
        self.hp_mng.grid_columnconfigure(3, weight=0, uniform="r2")
        self.hp_mng.grid_rowconfigure(0, weight=1)
        self.hp_mng.grid_rowconfigure(1, weight=0)
        self.hp_mng.grid_rowconfigure(2, weight=0)
        self.hp_mng.grid_rowconfigure(3, weight=0)
        self.ds_frame = tk.Frame(self.hp_mng, bg=self.colors["border"])
        self.ds_frame.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=1, pady=1)
        self.ds_frame.grid_columnconfigure(0, weight=1)
        self.ds_frame.grid_columnconfigure(1, weight=1)
        self.ds_frame.grid_columnconfigure(2, weight=1)
        self.ds_frame.grid_columnconfigure(3, weight=1)
        self.ds_frame.grid_rowconfigure(0, weight=1)
        # HP management widget framing.
        self.targeter_border = tk.Frame(self.hp_mng, bg=self.colors["border"])
        self.targeter_border.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.targeter_border.grid_columnconfigure(0, weight=1)
        self.targeter_border.grid_rowconfigure(0, weight=1)
        self.targeter = tk.Frame(self.targeter_border, bg=self.colors["button_bg"])
        self.targeter.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.amnt_border = tk.Frame(self.hp_mng, bg=self.colors["border"])
        self.amnt_border.grid(row=0, column=1, sticky="nsew", padx=1, pady=1)
        self.amnt_border.grid_columnconfigure(0, weight=1)
        self.amnt_border.grid_rowconfigure(0, weight=1)
        self.amnt_entry = tk.Frame(self.amnt_border, bg=self.colors["button_bg"])
        self.amnt_entry.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.res_border = tk.Frame(self.hp_mng, bg=self.colors["border"])
        self.res_border.grid(row=0, column=2, columnspan=2, sticky="nsew", padx=1, pady=1)
        self.res_border.grid_columnconfigure(0, weight=1)
        self.res_border.grid_rowconfigure(0, weight=1)
        self.res_toggle = tk.Frame(self.res_border, bg=self.colors["button_bg"])
        self.res_toggle.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        # Sets up 'Status' strip.
        self.status_border = tk.Frame(self.hp_mng, bg=self.colors["border"])
        self.status_border.grid(row=3, column=0, columnspan=4, sticky="ew", padx=1, pady=1)
        self.status_border.grid_columnconfigure(0, weight=1)
        self.status_border.grid_rowconfigure(0, weight=1)
        self.status_panel = tk.Frame(self.status_border, bg=self.colors["button_bg"])
        self.status_panel.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        self.status_panel.grid_columnconfigure(0, weight=1)
        self.status_panel.grid_rowconfigure(0, weight=1)
        # Sets up 'Damage' and 'Heal' buttons.
        self.dmg_hl_border = tk.Frame(self.right_frame, bg=self.colors["border"])
        self.dmg_hl_border.grid(row=3, column=0, sticky="ew", padx=1, pady=1)
        self.dmg_hl_border.grid_columnconfigure(0, weight=1)
        self.dmg_hl_border.grid_rowconfigure(0, weight=1)
        self.dmg_hl_btn_frame = tk.Frame(self.dmg_hl_border, bg=self.colors["button_bg"])
        self.dmg_hl_btn_frame.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        self.dmg_hl_btn_frame.grid_columnconfigure(0, weight=1)
        self.dmg_hl_btn_frame.grid_columnconfigure(1, weight=1)
        self.dmg_hl_btn_frame.grid_rowconfigure(0, weight=1)
        # 'Damage' and 'Heal' button configurations
        self.dmg_btn = ttk.Button(self.dmg_hl_btn_frame, text="Damage", command=self._on_damage_apply)
        self.dmg_btn.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        self.hl_btn = ttk.Button(self.dmg_hl_btn_frame, text="Heal", command=self._on_heal_apply)
        self.hl_btn.grid(row=0, column=1, sticky="ew", padx=1, pady=1)
        # HP management widgets.
        self.targeting = ttk.Combobox(self.targeter, state="readonly", textvariable=self.var_target)
        self.targeting.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.targeting.bind("<<ComboboxSelected>>", lambda e: self._validate_hp_controls())
        self.amount_entry_point = tk.Entry(self.amnt_entry, textvariable=self.var_amount, justify="left", bg=self.colors["list_bg"])
        self.amount_entry_point.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.res_checkbox = tk.Checkbutton(self.res_toggle, text="Resurrection", variable=self.var_resurrection)
        self.res_checkbox.grid(row=0, column=0, sticky="w", padx=1, pady=1)
        self.status_lbl = tk.Label(self.status_panel, textvariable=self.status_text, bg=self.colors["button_bg"], justify="left")
        self.status_lbl.grid(row=0, column=0, sticky="ew")
        # Death saving throw buttons
        self.fail_btn = ttk.Button(self.ds_frame, text="DS Failure", command=self._on_ds_fail)
        self.fail_btn.grid(row=1, column=0, sticky="nsew", padx=1, pady=1)
        self.crit_fail_btn = ttk.Button(self.ds_frame, text="Critical Failure", command=self._on_ds_crit_fail)
        self.crit_fail_btn.grid(row=1, column=1, sticky="nsew", padx=1, pady=1)
        self.pass_btn = ttk.Button(self.ds_frame, text="DS Success", command=self._on_ds_success)
        self.pass_btn.grid(row=1, column=2, sticky="nsew", padx=1, pady=1)
        self.crit_pass_btn = ttk.Button(self.ds_frame, text="Critical Success", command=self._on_ds_crit_success)
        self.crit_pass_btn.grid(row=1, column=3, sticky="nsew", padx=1, pady=1)
        # Conditions panel frames.
        self.conditions_border = tk.Frame(self.right_frame, bg=self.colors["border"])
        self.conditions_border.grid(row=4, column=0, sticky="nsew", padx=1, pady=1)
        self.conditions_border.grid_columnconfigure(0, weight=1)
        self.conditions_border.grid_rowconfigure(0, weight=1)
        self.conditions_panel = tk.Frame(self.conditions_border, bg=self.colors["panel_bg"])
        self.conditions_panel.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.conditions_panel.grid_columnconfigure(0, weight=1)
        self.conditions_panel.grid_rowconfigure(0, weight=0)
        self.conditions_panel.grid_rowconfigure(1, weight=1)
        self.conditions_panel.grid_rowconfigure(2, weight=1)
        self.conditions_panel.grid_rowconfigure(3, weight=1)
        # Conditions header.
        self.conditions_header_border = tk.Frame(self.conditions_panel, bg=self.colors["border"])
        self.conditions_header_border.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        self.conditions_header_border.grid_columnconfigure(0, weight=1)
        self.conditions_header_border.grid_rowconfigure(0, weight=1)
        self.conditions_header = tk.Frame(self.conditions_header_border, bg=self.colors["button_bg"])
        self.conditions_header.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        self.conditions_header.grid_columnconfigure(0, weight=1)
        self.conditions_header.grid_rowconfigure(0, weight=1)
        self.conditions_header_lbl = tk.Label(self.conditions_header, text="Conditions", bg=self.colors["button_bg"])
        self.conditions_header_lbl.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        # Conditions list and checkbox gridding (3 columns, 6 rows).
        self.condlist_border = tk.Frame(self.conditions_panel, bg=self.colors["border"])
        self.condlist_border.grid(row=1, column=0, sticky="nsew", padx=1, pady=1)
        self.condlist_border.grid_columnconfigure(0, weight=1)
        self.condlist_border.grid_rowconfigure(0, weight=1)
        self.condlist = tk.Frame(self.condlist_border, bg=self.colors["list_bg"])
        self.condlist.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.condlist.grid_columnconfigure(0, weight=1)
        self.condlist.grid_columnconfigure(1, weight=1)
        self.condlist.grid_columnconfigure(2, weight=1)
        self.condlist.grid_rowconfigure(0, weight=1)
        self.condlist.grid_rowconfigure(1, weight=1)
        self.condlist.grid_rowconfigure(2, weight=1)
        self.condlist.grid_rowconfigure(3, weight=1)
        self.condlist.grid_rowconfigure(4, weight=1)
        self.condlist.grid_rowconfigure(5, weight=1)
        # Condition checkboxes builder.
        for idx, name in enumerate(CONDITIONS):
            row = idx % 6
            col = idx // 6
            var = tk.BooleanVar(value=False)
            self._cond_vars[name] = var
            cb = tk.Checkbutton(self.condlist, text=name, variable=var, anchor="w", bg=self.colors["list_bg"])
            cb.grid(row=row, column=col, sticky="ew", padx=1, pady=1)
            self._cond_checks[name] = cb
            if name in ("slain", "dying"):
                self._cond_checks[name].configure(state="disabled")
        # Source and Targets for conditions.
        self.sandt_border = tk.Frame(self.conditions_panel, bg=self.colors["border"])
        self.sandt_border.grid(row=2, column=0, sticky="nsew", padx=1, pady=1)
        self.sandt_border.grid_columnconfigure(0, weight=1)
        self.sandt_border.grid_rowconfigure(0, weight=1)
        self.sandt_panel = tk.Frame(self.sandt_border, bg=self.colors["button_bg"])
        self.sandt_panel.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.sandt_panel.grid_columnconfigure(0, weight=0)
        self.sandt_panel.grid_columnconfigure(1, weight=1)
        self.sandt_panel.grid_rowconfigure(0, weight=1)
        self.sandt_panel.grid_rowconfigure(1, weight=1)
        # Source label.
        self.cond_source_lbl = tk.Label(self.sandt_panel, text="Condition Source", bg=self.colors["button_bg"], justify="left")
        self.cond_source_lbl.grid(row=0, column=0, sticky="ew")
        # Source list.
        self.cond_sources = ttk.Combobox(self.sandt_panel, state="readonly", values=["None"] + [w.name for w in self.tracker.warriors], textvariable=self.var_cond_source)
        self.cond_sources.grid(row=0, column=1, sticky="ew", padx=1, pady=1)
        self._cond_source_items = [None]
        for w in self.tracker.warriors:
            self._cond_source_items.append(w)
        # Targets label.
        self.targs_lbl = tk.Label(self.sandt_panel, text="Targets", bg=self.colors["button_bg"], justify="left")
        self.targs_lbl.grid(row=1, column=0, sticky="ew", padx=1, pady=1)
        # Targets listbox.
        self.targets_list_frame = tk.Frame(self.sandt_panel, bg=self.colors["button_bg"])
        self.targets_list_frame.grid(row=1, column=1, sticky="nsew", padx=1, pady=1)
        self.targets_list_frame.grid_columnconfigure(0, weight=1)
        self.targets_list_frame.grid_columnconfigure(1, weight=0)
        self.targets_list_frame.grid_rowconfigure(0, weight=1)
        self.targs = tk.Listbox(self.targets_list_frame, selectmode="extended", bg=self.colors["list_bg"])
        self.targs.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        # Targets scrollbar.
        self.targs_scroll = tk.Scrollbar(self.targets_list_frame, command=self.targs.yview)
        self.targs_scroll.grid(row=0, column=1, sticky="ns")
        # Condition details frames.
        self.cond_details_border = tk.Frame(self.conditions_panel, bg=self.colors["border"])
        self.cond_details_border.grid(row=3, column=0, sticky="nsew", padx=1, pady=1)
        self.cond_details_border.grid_columnconfigure(0, weight=1)
        self.cond_details_border.grid_rowconfigure(0, weight=1)
        self.cond_details = tk.Frame(self.cond_details_border, bg=self.colors["button_bg"])
        self.cond_details.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.cond_details.grid_columnconfigure(0, weight=1)
        self.cond_details.grid_columnconfigure(1, weight=1)
        self.cond_details.grid_columnconfigure(2, weight=1)
        self.cond_details.grid_columnconfigure(3, weight=1)
        self.cond_details.grid_rowconfigure(0, weight=0)
        self.cond_details.grid_rowconfigure(1, weight=1)
        self.cond_details.grid_rowconfigure(2, weight=1)
        # Condition duration.
        self.duration_lbl = tk.Label(self.cond_details, text="Rounds:", bg=self.colors["button_bg"], justify="center", width=12)
        self.duration_lbl.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        self.duration_entry = tk.Entry(self.cond_details, textvariable=self.var_cond_duration, width=8)
        self.duration_entry.grid(row=1, column=0, sticky="ew", padx=1, pady=1)
        self.var_cond_duration.trace_add("write", self._on_duration_change)
        # Condition tick timing.
        self.tick_time_lbl = tk.Label(self.cond_details, text="Tick timing:", bg=self.colors["button_bg"], font=("TkDefaultFont", 10), justify="center", width=6)
        self.tick_time_lbl.grid(row=0, column=1, sticky="ew", padx=1, pady=1)
        self.tick_time = ttk.Combobox(self.cond_details, state="readonly", values=["start", "end"], textvariable=self.var_cond_tick_timing)
        self.tick_time.grid(row=1, column=1, sticky="ew", padx=1, pady=1)
        self.tick_time.bind("<<ComboboxSelected>>", lambda e: self._validate_conditions_block())
        # Condition tick owner.
        self.tick_owner_lbl = tk.Label(self.cond_details, text="Tick owner:", bg=self.colors["button_bg"], font=("TkDefaultFont", 10), justify="center", width=6)
        self.tick_owner_lbl.grid(row=0, column=2, sticky="ew", padx=1, pady=1)
        self.tick_owner = ttk.Combobox(self.cond_details, state="readonly", values=["none", "target", "source"], textvariable=self.var_cond_tick_owner)
        self.tick_owner.grid(row=1, column=2, sticky="ew", padx=1, pady=1)
        self.tick_owner.bind("<<ComboboxSelected>>", lambda e: self._validate_conditions_block())
        # Concentration.
        self.tie_lbl = tk.Label(self.cond_details, text="Conc.?", bg=self.colors["button_bg"], justify="center", width=12)
        self.tie_lbl.grid(row=0, column=3, sticky="nsew", padx=1, pady=1)
        self.tie_checkbox = tk.Checkbutton(self.cond_details, variable=self.var_cond_concentration_tie, justify="center", width=12)
        self.tie_checkbox.grid(row=1, column=3, sticky="nsew", padx=1, pady=1)
        if self.var_cond_source.get() == "None":
            self.tie_checkbox.configure(state="disabled")
            self.var_cond_concentration_tie.set(False)
        # 'Add' and 'Clear' condition buttons.
        self.add_cond_btn = ttk.Button(self.cond_details, text="Add Condition", command=self._on_conditions_apply, state="disabled")
        self.add_cond_btn.grid(row=2, column=0, columnspan=2, sticky="ew", padx=1, pady=1)
        self.clear_cond_btn = ttk.Button(self.cond_details, text="Clear Condition", command=self._on_conditions_clear, state="disabled")
        self.clear_cond_btn.grid(row=2, column=2, columnspan=2, sticky="ew", padx=1, pady=1)
        # Renders the right panel and its contents.
        self.render_right_panel()
        self._rebuild_target_options()
        self._validate_hp_controls()
    def _setup_log_frame(self):
        # Log panel frame configuration.
        self.log_frame_border = tk.Frame(self.root, bg=self.colors["border"])
        self.log_frame_border.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=2, pady=2)
        self.log_frame_border.grid_columnconfigure(0, weight=1)
        self.log_frame_border.grid_rowconfigure(0, weight=1)
        self.log_frame = tk.Frame(self.log_frame_border, bg=self.colors["panel_bg"])
        self.log_frame.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(0, weight=1)
    # Apply condition button wiring.
    def _on_conditions_apply(self):
        indices = self.targs.curselection()
        targets = [ self._cond_targets_index_to_warrior[i] for i in indices]
        idx = self.cond_sources.current()
        source = self._cond_source_items[idx]
        if idx == 0:
            source = None
        raw = self.var_cond_duration.get().strip()
        timing = self.var_cond_tick_timing.get()
        owner = self.var_cond_tick_owner.get()
        if owner == "none":
            owner = None
        tie = self.var_cond_concentration_tie.get()
        names = [name for name, v in self._cond_vars.items() if v.get() and name not in {"slain", "dying", "unconscious", "stable", "concentration"}]
        duration = None if raw == "" else int(raw)
        added_ties = 0
        if not targets or not names:
            return
        for target in targets:
            for cond_name in names:
                cond = Condition(name=cond_name, duration=duration, tick_timing=timing, tick_owner=owner, source=source, target=target, expires_with_source=("concentration" if tie else None))
                token = target.apply_condition(cond)
                if token == "duplicate_ignored":
                    self._log(f"{cond_name} already on {target.name}, skipped.")
                elif token == "concentration_replace_requested":
                    self._log(f"{source.name} already has Concentration; replacement needed for {cond_name}.")
                elif token == "added_breaks_concentration":
                    self._log(f"{target.name} is now {cond_name} (breaks concentration).")
                elif token == "added":
                    dur_text = "indefinite" if duration is None else f"{duration} rounds"
                    owner_text = owner or "none"
                    self._log(f"Applied {cond_name} ({dur_text}, {timing}/{owner_text}) from {source.name if source else 'None'} to {target.name}.")
                if tie and source is not None and token in ("added", "added_breaks_concentration"):
                    added_ties += 1
        for n in names:
            self._cond_vars[n].set(False)
        if tie and source is not None and source._find_condition_by_name("concentration") is None:
            source.apply_condition(Condition("concentration", source=source, target=source))
        if tie and source is not None and added_ties:
            self._conc_tie_counts[source] = self._conc_tie_counts.get(source, 0) + added_ties
        self._rebuild_cond_sources_and_targets()
        self._validate_conditions_block()
    # Clear condition button wiring.
    def _on_conditions_clear(self):
        man_cons = {"slain","dying","unconscious","stable","concentration"}
        names = [name for name, v in self._cond_vars.items() if v.get() and name not in man_cons]
        indices = self.targs.curselection()
        targets = [ self._cond_targets_index_to_warrior[i] for i in indices]
        sources_to_check = set()
        dec_by = {}
        if not names or not targets:
            return
        for target in targets:
            for cond in list(target.conditions):
                if cond.name in names:
                    target.remove_condition(cond)
                    if cond.expires_with_source == "concentration" and cond.source is not None:
                        sources_to_check.add(cond.source)
                        dec_by[src] = dec_by.get(src, 0) + 1
                    self._log(f"Cleared {cond.name} from {target.name}.")
        for src in sources_to_check:
            still_tied = any(c.expires_with_source == "concentration" and c.source is src, for w in self.tracker.warriors, for c in w.conditions)
            if not still_tied:
                conc = src._find_condition_by_name("concentration")
                if conc is not None:
                    src.remove_condition(conc)
                    self._log(f"{src.name} stops concentrating (no tied effects remain)")
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
        self.init_tree.focus(current_iid)
        self.init_tree.see(current_iid)
        self._suppress_select = False
        if self._combat_started and len(self.tracker.warriors) >= 2:
            self.nxt_turn_btn.state(["!disabled"])
        else:
            self.nxt_turn_btn.state(["disabled"])
        self.render_roster()
    # Helper method to clear initiative list between refreshes.
    def _clear_initiative_list(self):
        self.init_tree.delete(*self.init_tree.get_children())
        self._iid_to_warrior = {}
    # Retrieves current warrior identification.
    def _on_initiative_select(self, event=None):
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
        self.init_tree.selection_remove(self.init_tree.selection())
        self.render_roster()
    # Handler for scrollbar binding in central panel.
    def _on_roster_select(self, event=None):
        if self._suppress_select:
            return
        selection = self.roster.selection()
        if not selection:
            return
        iid = selection[0]
        w = self._roster_iid_to_warrior.get(iid)
        if w is not None:
            self.selected_warrior = w
            self.roster.selection_remove(self.roster.selection())
            self.render_right_panel()
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
        self.render_roster()
        # Checks for team wipe and notifies if true.
        status = self.tracker.check_team_able()
        if status["allies_disabled"]: messagebox.showinfo("Combat", "All allies are defeated. The DM has earned a nap and a cookie!")
        if status["enemies_disabled"]: messagebox.showinfo("Combat", "All enemies are defeated. The party have earned waffles. Waffles, Ho!")
    # Renders roster.
    def render_roster(self):
        self.roster.delete(*self.roster.get_children())
        self._roster_iid_to_warrior = {}
        for w in self.tracker.warriors:
            iid = str(id(w))
            self._roster_iid_to_warrior[iid] = w
            values = (w.name, w.ac, w.hp_current, w.hp_current_max, ", ".join(c.name for c in w.conditions), w.death_save_failures, w.death_save_successes)
            tags = []
            if w.is_dead():
                tags.append(self.tags["slain"])
            if w is self.tracker.warriors[self.tracker.current_warrior_index]:
                tags.append(self.tags["current"])
            self.roster.insert("", "end", iid=iid, values=values, tags=tags)
        if self.selected_warrior is not None:
            sel_iid = str(id(self.selected_warrior))
            if sel_iid in self._roster_iid_to_warrior:
                self._suppress_select = True
                self.roster.focus(sel_iid)
                self.roster.see(sel_iid)
                self._suppress_select = False
    # Opens the 'Add Warrior' modal on call.
    def _open_add_warrior_modal(self):
        # Defines the modal window.
        self._aw_win = tk.Toplevel(self.root)
        self._aw_win.grid_columnconfigure(0, weight=1)
        self._aw_win.grid_rowconfigure(0, weight=1)
        self._aw_container = tk.Frame(self._aw_win, bg=self.colors["border"])
        self._aw_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self._aw_contain_field = tk.Frame(self._aw_container, bg=self.colors["panel_bg"])
        self._aw_contain_field.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self._aw_contain_field.grid_columnconfigure(0, weight=0)
        self._aw_contain_field.grid_columnconfigure(1, weight=1)
        # Defines the rows in the modal window for data input.
        self.name_lbl = tk.Label(self._aw_contain_field, text="Name:", bg=self.colors["label_bg"])
        self.name_lbl.grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        self._aw_name = ttk.Entry(self._aw_contain_field)
        self._aw_name.grid(row=0, column=1, sticky="ew", padx=2, pady=2)
        self._aw_name.focus_set()
        self.side_lbl = tk.Label(self._aw_contain_field, text="Side:", bg=self.colors["label_bg"])
        self.side_lbl.grid(row=1, column=0, sticky="ew", padx=2, pady=2)
        self.side_combo = ttk.Combobox(self._aw_contain_field, state="readonly", values=["Ally", "Enemy"])
        self.side_combo.grid(row=1, column=1, sticky="ew", padx=2, pady=2)
        self.ac_lbl = tk.Label(self._aw_contain_field, text="AC:", bg=self.colors["label_bg"])
        self.ac_lbl.grid(row=2, column=0, sticky="ew", padx=2, pady=2)
        self._aw_ac = ttk.Entry(self._aw_contain_field, justify="center")
        self._aw_ac.grid(row=2, column=1, sticky="ew", padx=2, pady=2)
        self.chp_lbl = tk.Label(self._aw_contain_field, text="Current HP:", bg=self.colors["label_bg"])
        self.chp_lbl.grid(row=3, column=0, sticky="ew", padx=2, pady=2)
        self._aw_chp = ttk.Entry(self._aw_contain_field, justify="center")
        self._aw_chp.grid(row=3, column=1, sticky="ew", padx=2, pady=2)
        self.mhp_lbl = tk.Label(self._aw_contain_field, text="Max HP:", bg=self.colors["label_bg"])
        self.mhp_lbl.grid(row=4, column=0, sticky="ew", padx=2, pady=2)
        self._aw_mhp = ttk.Entry(self._aw_contain_field, justify="center")
        self._aw_mhp.grid(row=4, column=1, sticky="ew", padx=2, pady=2)
        self.init_lbl = tk.Label(self._aw_contain_field, text="Initiative:", bg=self.colors["label_bg"])
        self.init_lbl.grid(row=5, column=0, sticky="ew", padx=2, pady=2)
        self._aw_init = ttk.Entry(self._aw_contain_field, justify="center")
        self._aw_init.grid(row=5, column=1, sticky="ew", padx=2, pady=2)
        self.tbrk_lbl = tk.Label(self._aw_contain_field, text="Tiebreak:", bg=self.colors["label_bg"])
        self.tbrk_lbl.grid(row=6, column=0, sticky="ew", padx=2, pady=2)
        self._aw_tbrk = ttk.Entry(self._aw_contain_field, justify="center")
        self._aw_tbrk.grid(row=6, column=1, sticky="ew", padx=2, pady=2)
        self._aw_tbrk.insert(0, "0")
        # Creates frame for add/cancel buttons.
        self.add_frame = tk.Frame(self._aw_contain_field, bg=self.colors["border"])
        self.add_frame.grid(row=7, column=0, columnspan=2, sticky="nsew", padx=1, pady=1)
        self.add_frame.grid_columnconfigure(0, weight=1)
        self.add_frame.grid_rowconfigure(0, weight=1)
        self.cadd_frame = tk.Frame(self.add_frame, bg=self.colors["button_bg"])
        self.cadd_frame.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.cadd_frame.grid_columnconfigure(0, weight=1)
        self.cadd_frame.grid_columnconfigure(1, weight=1)
        # Configures add/cancel buttons.
        self.add_btn = ttk.Button(self.cadd_frame, text="Add Combatant", command=self._confirm_add_warrior)
        self.add_btn.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        self.canc_btn = ttk.Button(self.cadd_frame, text="Cancel", command=self.close_modal)
        self.canc_btn.grid(row=0, column=1, sticky="ew", padx=1, pady=1)
    # Method to close modal.
    def close_modal(self):
        self._aw_win.destroy()
    # Confirms a warrior being added.
    def _confirm_add_warrior(self):
        name = self._aw_name.get().strip()
        if not name:
            messagebox.showerror("Add Combatant", "Name is required.")
            self._aw_name.focus_set()
            return
        if any(w.name == name for w in self.tracker.warriors):
            if not messagebox.askyesno("Duplicate name", "Name already used. Continue?"):
                self._aw_name.focus_set()
                return
        side = self.side_combo.get()
        if side not in ("Ally", "Enemy"):
            messagebox.showerror("Add Combatant", "Side is required.")
            self.side_combo.focus_set()
            return
        try:
            ac = int(self._aw_ac.get().strip())
        except ValueError:
                messagebox.showerror("Add Combatant", "AC is not valid.")
                self._aw_ac.focus_set()
                return
        if ac < 0:
            messagebox.showerror("Add Combatant", "AC is not valid.")
            self._aw_ac.focus_set()
            return
        try:
            hp_max = int(self._aw_mhp.get().strip())
        except ValueError:
            messagebox.showerror("Add Combatant", "Max HP must be at least 0.")
            self._aw_mhp.focus_set()
            return
        if hp_max <0:
            messagebox.showerror("Add Combatant", "Max HP must be at least 0.")
            self._aw_mhp.focus_set()
            return
        try:
            hp_cur = int(self._aw_chp.get().strip())
        except ValueError:
            messagebox.showerror("Add Combatant", "Current HP must be at least 0.")
            self._aw_chp.focus_set()
            return
        hp_cur = max(0, min(hp_cur, hp_max))
        try:
            initiative = int(self._aw_init.get().strip())
        except ValueError:
            messagebox.showerror("Add Combatant", "Initiative must be entered.")
            self._aw_init.focus_set()
            return
        t_text = self._aw_tbrk.get().strip()
        if t_text == "":
            tiebreak = 0
        else:
            try:
                tiebreak = int(t_text)
            except ValueError:
                messagebox.showerror("Add Combatant", "Tiebreak must be a whole number, but may default to 0.")
                self._aw_tbrk.focus_set()
                return
        payload = {
            "name": name,
            "side": side.lower(),
            "ac": ac,
            "hp_cur": hp_cur,
            "hp_max": hp_max,
            "initiative": initiative,
            "tiebreak": tiebreak,
        }
        self._finalize_add_warrior(payload)
    # Finalizes the warrior being added.
    def _finalize_add_warrior(self, payload):
        # Create the new Warrior
        w = self.tracker.add_warrior(
            payload["name"],
            payload["initiative"],
            payload["side"],
            payload["ac"],
            payload["hp_cur"],
            payload["hp_max"],
            conditions=None
        )
        # Remember last side for convenience in the modal
        self._last_side = payload["side"]
        # Close modal
        self._aw_win.destroy()
        # Handles adding if combat has started.
        if self._combat_started:
            ties = self.tracker.get_initiative_ties()
            if w.initiative in ties and len(ties[w.initiative]) >= 2:
                self._open_tie_breaker_modal({w.initiative: ties[w.initiative]})
                self._tb_win.transient(self.root)
                self._tb_win.grab_set()
                self._tb_win.wait_window()
                self.tracker.sort_warriors()
        # Refresh displays
        self.render_initiative()
        self.render_roster()
        self._rebuild_target_options()
        self._validate_hp_controls()
        self.render_right_panel()
        # Select and reveal the new combatant
        iid = str(id(w))
        self._suppress_select = True
        if iid in self._iid_to_warrior:  # initiative list
            self.init_tree.selection_set(iid)
            self.init_tree.focus(iid)
            self.init_tree.see(iid)
        if iid in self._roster_iid_to_warrior:  # roster list
            self.roster.selection_set(iid)
            self.roster.focus(iid)
            self.roster.see(iid)
        self._suppress_select = False
    # Renders the right panel.
    def render_right_panel(self):
        # Placeholder until right-panel controls are finished.
        if not self._combat_started and len(self.tracker.warriors) >= 2:
            self.start_combat_btn.state(["!disabled"])
        else:
            self.start_combat_btn.state(["disabled"])
        pass
    # Handler for starting combat.
    def _on_start_combat(self):
        if len(self.tracker.warriors) < 2:
            messagebox.showinfo("Combat", "Add at least two combatants to start.")
            return
        self.tracker.sort_warriors()
        ties = self.tracker.get_initiative_ties()
        if ties:
            self._open_tie_breaker_modal(ties)
            self._tb_win.transient(self.root)
            self._tb_win.grab_set()
            self._tb_win.wait_window()
            if getattr(self, "_tb_cancelled", False):
                return
            self.tracker.sort_warriors()
        self.tracker.current_warrior_index = 0
        self.tracker.round_number = 1
        for w in self.tracker.warriors:
            self.tracker.eligible_from_round[id(w)] = 1
        self.selected_warrior = self.tracker.warriors[0]
        self._combat_started = True
        self.render_initiative()
        self.render_roster()
        self._rebuild_target_options()
        self._validate_hp_controls()
        self.render_right_panel()
    # Modal for handling tied initiative.
    def _open_tie_breaker_modal(self, ties):
        self._tb_cancelled = False
        self._tb_groups = {}
        # Establishes modal.
        self._tb_win = tk.Toplevel(self.root)
        self._tb_win.title("Resolve Initiative Ties")
        self._tb_win.resizable(False, False)
        self._tb_win.grid_columnconfigure(0, weight=1)
        self._tb_win.grid_rowconfigure(0, weight=1)
        # Creates border and panel frames.
        self._tb_border = tk.Frame(self._tb_win, bg=self.colors["border"])
        self._tb_border.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self._tb_border.grid_columnconfigure(0, weight=1)
        self._tb_border.grid_rowconfigure(0, weight=1)
        self._tb_panel = tk.Frame(self._tb_border, bg=self.colors["panel_bg"])
        self._tb_panel.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self._tb_panel.grid_columnconfigure(0, weight=1)
        self._tb_panel.grid_rowconfigure(0, weight=0)
        self._tb_panel.grid_rowconfigure(1, weight=1)
        self._tb_panel.grid_rowconfigure(2, weight=0)
        # Header row.
        self._header_border = tk.Frame(self._tb_panel, bg=self.colors["border"])
        self._header_border.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        self._header_border.grid_columnconfigure(0, weight=1)
        self._header = tk.Frame(self._header_border, bg=self.colors["label_bg"])
        self._header.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        self._header.grid_columnconfigure(0, weight=1)
        self._header_lbl = tk.Label(self._header, text="Initiative ties detected. Adjust order within each group.", bg=self.colors["label_bg"], anchor="w")
        self._header_lbl.grid(row=0, column=0, sticky="w")
        self._header_lbl.grid_columnconfigure(0, weight=1)
        # Groups row.
        self._tb_body = tk.Frame(self._tb_panel, bg=self.colors["panel_bg"])
        self._tb_body.grid(row=1, column=0, sticky="nsew", padx=1, pady=1)
        self._tb_body.grid_columnconfigure(0, weight=1)
        orig_index = {w: idx for idx, w in enumerate(self.tracker.warriors)}
        for i, (init_val, group) in enumerate(sorted(ties.items(), key=lambda kv: -kv[0])):
            ordered = sorted(group, key=lambda w: (w.tiebreak_priority, orig_index[w]))
            # i = row index for this group
            # Outer border + inner panel
            group_border = tk.Frame(self._tb_body, bg=self.colors["border"])
            group_border.grid(row=i, column=0, sticky="nsew", padx=2, pady=2)
            group_border.grid_columnconfigure(0, weight=1)
            group_panel = tk.Frame(group_border, bg=self.colors["panel_bg"])
            group_panel.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
            group_panel.grid_columnconfigure(0, weight=1)  # listbox column
            group_panel.grid_columnconfigure(1, weight=0)  # buttons column
            group_panel.grid_rowconfigure(1, weight=1)     # listbox row grows
            # Title row
            title_border = tk.Frame(group_panel, bg=self.colors["border"])
            title_border.grid(row=0, column=0, columnspan=2, sticky="ew", padx=1, pady=1)
            title_border.grid_columnconfigure(0, weight=1)
            title_inner = tk.Frame(title_border, bg=self.colors["label_bg"])
            title_inner.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
            tk.Label(title_inner, text=f"Initiative {init_val}", bg=self.colors["label_bg"]).grid(row=0, column=0, sticky="w")
            # Listbox (for tied warriors)
            listbox = tk.Listbox(group_panel, exportselection=False, height=min(len(group), 6))
            listbox.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
            # Populate names
            for w in ordered:
                listbox.insert("end", w.name)
            # Buttons (Up/Down)
            btn_frame = tk.Frame(group_panel, bg=self.colors["button_bg"])
            btn_frame.grid(row=1, column=1, sticky="ns", padx=2, pady=2)
            ttk.Button(btn_frame, text="↑", command=lambda v=init_val: self._tb_move_up(v)).grid(row=0, column=0, sticky="ew", padx=1, pady=1)
            ttk.Button(btn_frame, text="↓", command=lambda v=init_val: self._tb_move_down(v)).grid(row=1, column=0, sticky="ew", padx=1, pady=1)
            # Track this group for later
            self._tb_groups[init_val] = {"list": listbox, "ids": [id(w) for w in ordered]}
        # Buttons row.
        self._tb_footer_border = tk.Frame(self._tb_panel, bg=self.colors["border"])
        self._tb_footer_border.grid(row=2, column=0, sticky="ew", padx=1, pady=1)
        self._tb_footer_border.grid_columnconfigure(0, weight=1)
        self._tb_footer = tk.Frame(self._tb_footer_border, bg=self.colors["button_bg"])
        self._tb_footer.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        self._tb_footer.grid_columnconfigure(0, weight=1)
        self._tb_footer.grid_columnconfigure(1, weight=1)
        ttk.Button(self._tb_footer, text="Apply Order", command=self._tb_apply).grid(row=0, column=0, padx=1, pady=1)
        ttk.Button(self._tb_footer, text="Cancel", command=self._tb_cancel).grid(row=0, column=1, padx=1, pady=1)
    # Moves selection up in tiebreaker mode.
    def _tb_move_up(self, init_val):
        lb = self._tb_groups[init_val]["list"]
        ids = self._tb_groups[init_val]["ids"]
        sel = lb.curselection()
        if not sel: return
        i = sel[0]
        if i == 0: return
        # swap ids
        ids[i-1], ids[i] = ids[i], ids[i-1]
        # swap listbox rows
        txt = lb.get(i)
        above = lb.get(i-1)
        lb.delete(i-1, i)
        lb.insert(i-1, txt)
        lb.insert(i, above)
        lb.selection_clear(0, "end")
        lb.selection_set(i-1)
        lb.see(i-1)
    # Moves selection down in tiebreaker mode.
    def _tb_move_down(self, init_val):
        lb = self._tb_groups[init_val]["list"]
        ids = self._tb_groups[init_val]["ids"]
        sel = lb.curselection()
        if not sel: return
        i = sel[0]
        if i >= lb.size() - 1: return
        # swap ids
        ids[i+1], ids[i] = ids[i], ids[i+1]
        # swap listbox rows
        txt = lb.get(i)
        below = lb.get(i+1)
        lb.delete(i, i+1)
        lb.insert(i, below)
        lb.insert(i+1, txt)
        lb.selection_clear(0, "end")
        lb.selection_set(i+1)
        lb.see(i+1)
    # Apply button wiring.
    def _tb_apply(self):
        # map: python id -> Warrior (fast lookup)
        id_to_w = {id(w): w for w in self.tracker.warriors}
        for init_val, grp in self._tb_groups.items():
            for rank, wid in enumerate(grp["ids"]):
                w = id_to_w.get(wid)
                if w is None: continue
                # Only set within its tied init (defensive)
                if w.initiative == init_val:
                    w.tiebreak_priority = rank
        self._tb_cancelled = False
        self._tb_win.destroy()
    # Cancel button wiring.
    def _tb_cancel(self):
        self._tb_cancelled = True
        self._tb_win.destroy()
    # Handles damage application.
    def _on_damage_apply(self):
        cause = None
        conc_dict = {}
        w = self._get_selected_warrior()
        (ok_amt, n) = self._parse_amount()
        if w is None:
            self.status_text.set("Select a target.")
            return
        if not ok_amt:
            self.status_text.set("Enter a non-negative integer amount.")
            return
        hp_before = w.hp_current
        result = w.take_damage(n, is_critical=False)
        breaks = {x.lower() for x in BREAKS_CONCENTRATION}
        if result == "slain":
            cause = "slain"
        elif result == "dying":
            cause = "dying"
        else:
            for c in w.conditions:
                if c.name.lower() in breaks:
                    cause = c.name
                    break
        conc = w._find_condition_by_name("concentration")
        if cause and conc in w.conditions:
            conc_dict = self.tracker.remove_condition(w, conc.condition_id)
        hp_after = w.hp_current
        self.render_initiative()
        self.render_roster()
        self._rebuild_target_options()
        self._validate_hp_controls()
        self.status_text.set("")
        # Logging info.
        log_line = f"DMG: {w.name} takes {n} damage. Hit points reduce from {hp_before} to {hp_after}"
        if result == "slain":
            log_line += " [slain]"
        elif result == "dying":
            log_line += " [dying]"
        self._log(log_line)
        if cause and conc_dict.get("removed", 0) == 1:
            self._log(f"CONC: {w.name} lost concentration due to {cause}")
            for cid in conc_dict.get("cascade", []):
                for ww in self.tracker.warriors:
                    cond = ww.get_condition_by_id(cid)
                    if cond:
                        self._log(f"CASCADED: Removed {cond.name} from {ww.name} (source {w.name})")
    # Handles healing application.
    def _on_heal_apply(self):
        w = self._get_selected_warrior()
        (ok_amt, n) = self._parse_amount()
        res = self.var_resurrection.get()
        if w is None:
            self.status_text.set("Select a target.")
            return
        if not ok_amt:
            self.status_text.set("enter a non-negative integer amount.")
            return
        hp_before = w.hp_current
        if w.is_dead() and res == False:
            self.status_text.set("Slain: source must be a resurrection effect to revive.")
            self._log(f"HEAL: {w.name} no effect (slain; resurrection required).")
            return
        w.heal(n, resurrection_effect=res)
        hp_after = w.hp_current
        self.render_initiative()
        self.render_roster()
        self._rebuild_target_options()
        self._validate_hp_controls()
        self.status_text.set("")
        # Logging info.
        log_line = f"HEAL: {w.name} is healed for {n}. Hit points increase from {hp_before} to {hp_after}"
        if res:
            log_line += " [resurrection]"
        self._log(log_line)
    # Handlers for death saving throw buttons.
    def _on_ds_fail(self):
        w = self._get_selected_warrior()
        if w is None:
            self.status_text.set("Select a target.")
            return
        if w.hp_current != 0 or w.is_dead():
            self.status_text.set("Death saves only allowed at 0 hp (not slain or stable)")
            return
        if w._find_condition_by_name("stable"):
            self.status_text.set("Death saves only allowed at 0 hp (not slain or stable)")
            return
        result = w.fail_death_saves(is_critical=False)
        self.render_initiative()
        self.render_roster()
        self._rebuild_target_options()
        self._validate_hp_controls()
        self.status_text.set("")
        log_line = f"DS: {w.name} +1 failure."
        if result == "slain":
            log_line += " [slain]"
        self._log(log_line)
    def _on_ds_crit_fail(self):
        w = self._get_selected_warrior()
        if w is None:
            self.status_text.set("Select a target.")
            return
        if w.hp_current != 0 or w.is_dead():
            self.status_text.set("Death saves only allowed at 0 hp (not slain or stable)")
            return
        if w._find_condition_by_name("stable"):
            self.status_text.set("Death saves only allowed at 0 hp (not slain or stable)")
            return
        result = w.fail_death_saves(is_critical=True)
        self.render_initiative()
        self.render_roster()
        self._rebuild_target_options()
        self._validate_hp_controls()
        self.status_text.set("")
        log_line = f"DS: {w.name} +2 failures."
        if result == "slain":
            log_line += " [slain]"
        self._log(log_line)
    def _on_ds_success(self):
        w = self._get_selected_warrior()
        if w is None:
            self.status_text.set("Select a target.")
            return
        if w.hp_current != 0 or w.is_dead():
            self.status_text.set("Death saves only allowed at 0 hp (not slain or stable)")
            return
        if w._find_condition_by_name("stable"):
            self.status_text.set("Death saves only allowed at 0 hp (not slain or stable)")
            return
        result = w.succeed_death_saves(is_critical=False)
        self.render_initiative()
        self.render_roster()
        self._rebuild_target_options()
        self._validate_hp_controls()
        self.status_text.set("")
        log_line = f"DS: {w.name} +1 success"
        if result == "stable":
            log_line += " [stable]"
        self._log(log_line)
    def _on_ds_crit_success(self):
        w = self._get_selected_warrior()
        if w is None:
            self.status_text.set("Select a target.")
            return
        if w.hp_current != 0 or w.is_dead():
            self.status_text.set("Death saves only allowed at 0 hp (not slain or stable)")
            return
        if w._find_condition_by_name("stable"):
            self.status_text.set("Death saves only allowed at 0 hp (not slain or stable)")
            return
        w.succeed_death_saves(is_critical=True)
        self.render_initiative()
        self.render_roster()
        self._rebuild_target_options()
        self._validate_hp_controls()
        self.status_text.set("")
        log_line = f"DS: {w.name} critical success! HP is restored to 1."
        self._log(log_line)
    # Helper method for target widget.
    def _rebuild_target_options(self):
        prev_label = self.var_target.get()
        if prev_label is not None and prev_label in self._target_values:
            idx = self._target_values.index(prev_label)
            prev_obj = self._target_index_to_warrior[idx]
        else:
            prev_obj = None
        self._target_values.clear()
        self._target_index_to_warrior.clear()
        for w in self.tracker.warriors:
            disp_lbl = w.name
            self._target_values.append(disp_lbl)
            self._target_index_to_warrior.append(w)
        self.targeting["values"] = self._target_values
        if prev_obj is not None and prev_obj in self._target_index_to_warrior:
            new_idx = self._target_index_to_warrior.index(prev_obj)
            self.var_target.set(self._target_values[new_idx])
        elif not self.var_target.get() and self._target_values:
            self.var_target.set(self._target_values[0])
        else:
            if not self._target_values:
                self.var_target.set("")
        self._validate_hp_controls()
    def _get_selected_warrior(self):
        label = self.var_target.get()
        if not label:
            return None
        try:
            idx = self._target_values.index(label)
        except ValueError:
            return None
        return self._target_index_to_warrior[idx]
    def _parse_amount(self):
        s = self.var_amount.get().strip()
        if not s:
            return (False, None)
        try:
            n = int(s, 10)
        except ValueError:
            return (False, None)
        if n < 0:
            return (False, None)
        return (True, n)
    # Helper for updating status strip.
    def _update_status_strip_for_target(self):
        w = self._get_selected_warrior()
        if w is None:
            return
        self.status_text.set(f"{w.name} • {w.side} • ({w.hp_current}/{w.hp_current_max})")
    # Enables/Disables Damage, Heal, and Death Save buttons, sets the status strip text.
    def _validate_hp_controls(self):
        w = self._get_selected_warrior()
        ok_amt, _ = self._parse_amount()
        dmg_ok = (w is not None) and ok_amt
        heal_ok = (w is not None) and ok_amt
        ds_ok = bool(w and (w.hp_current == 0) and (not w.is_dead()) and (w._find_condition_by_name("stable") is None))
        if w is None:
            try:
                self.dmg_btn.state(["disabled"])
                self.hl_btn.state(["disabled"])
                self.fail_btn.state(["disabled"])
                self.crit_fail_btn.state(["disabled"])
                self.pass_btn.state(["disabled"])
                self.crit_pass_btn.state(["disabled"])
            finally:
                self.status_text.set("Select a target")
            return
        self.dmg_btn.state(["!disabled"] if dmg_ok else ["disabled"])
        self.hl_btn.state(["!disabled"] if heal_ok else ["disabled"])
        if ds_ok:
            self.fail_btn.state(["!disabled"])
            self.crit_fail_btn.state(["!disabled"])
            self.pass_btn.state(["!disabled"])
            self.crit_pass_btn.state(["!disabled"])
        else:
            self.fail_btn.state(["disabled"])
            self.crit_fail_btn.state(["disabled"])
            self.pass_btn.state(["disabled"])
            self.crit_pass_btn.state(["disabled"])
        self._update_status_strip_for_target()
    # Refreshes the condition sources and targets lists.
    def _rebuild_cond_sources_and_targets(self):
        prev_source_display = self.var_cond_source.get()
        prev_target_indices = set(self.targs.curselection())
        prev_scroll = self.targs.yview()[0]
        roster_in_order = sorted(self.tracker.warriors, key=lambda w: w.name.lower())
        display_list = [w.name for w in roster_in_order]
        values = ["None"] + display_list
        self._cond_source_items = [None] + roster_in_order
        self.cond_sources['values'] = values
        if prev_source_display in values:
            self.var_cond_source.set(prev_source_display)
        else:
            self.var_cond_source.set("None")
        self.targs.delete(0, tk.END)
        self._cond_targets_index_to_warrior = []
        for display_str, w in zip(display_list, roster_in_order):
            self.targs.insert(tk.END, display_str)
            self._cond_targets_index_to_warrior.append(w)
        for idx in prev_target_indices:
            if 0 <= idx < len(self._cond_targets_index_to_warrior):
                self.targs.selection_set(idx)
        if prev_scroll is not None and self.targs.size() > 0:
            self.targs.yview_moveto(prev_scroll)
        self._update_concentration_toggle_state()
        self._validate_conditions_block()
    # Updates concentration toggle status.
    def _update_concentration_toggle_state(self):
        val = self.var_cond_source.get()
        if val == "None":
            self.tie_checkbox.configure(state="disabled")
            self.var_cond_concentration_tie.set(False)
        else:
            self.tie_checkbox.configure(state="normal")
    # Duration handler.
    def _on_duration_change(self, *args):
        self._validate_conditions_block()
    # Conditions block validation.
    def _validate_conditions_block(self):
        pass
    # Logging helper.
    def _log(self):
        pass
# Primary function/entry point.
#def main():
    #tracker = Tracker()

if __name__ == "__main__":
    tracker = Tracker()
    window = Window(tracker)
    window.root.mainloop()
    #main()