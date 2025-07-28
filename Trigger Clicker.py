import cv2
import numpy as np
import pyautogui
import time
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageTk
import json
import keyboard
import threading
from datetime import datetime

class ImageClicker:
    def __init__(self, template_folder: str = "templates", confidence_threshold: float = 0.8, scale_factor: float = 0.5, interval: float = 0.5):
        self.templates: List[Tuple[np.ndarray, str, str]] = []  # (template, path, click_action)
        self.template_folder = template_folder
        self.confidence_threshold = confidence_threshold
        self.scale_factor = scale_factor
        self.interval = interval
        self.running = False
        self.paused = False
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.05
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.load_templates()

    def load_templates(self) -> None:
        """Load all images from the specified folder as templates with default click action."""
        self.templates.clear()
        if not os.path.isdir(self.template_folder):
            print(f"Template folder not found: {self.template_folder}")
            return

        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp')
        for filename in os.listdir(self.template_folder):
            if filename.lower().endswith(valid_extensions):
                image_path = os.path.join(self.template_folder, filename)
                template = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                if template is None:
                    print(f"Failed to load image: {image_path}")
                    continue
                template = cv2.resize(template, (0, 0), fx=self.scale_factor, fy=self.scale_factor)
                self.templates.append((template, image_path, "Left Click"))
                print(f"Added template: {image_path}")

    def add_template(self, image_path: str, click_action: str = "Left Click") -> bool:
        """Add a single template image with specified click action."""
        if not os.path.exists(image_path):
            print(f"Image not found: {image_path}")
            return False
        template = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            print(f"Failed to load image: {image_path}")
            return False
        template = cv2.resize(template, (0, 0), fx=self.scale_factor, fy=self.scale_factor)
        self.templates.append((template, image_path, click_action))
        print(f"Added template: {image_path} with action {click_action}")
        return True

    def remove_template(self, image_path: str) -> bool:
        """Remove a specific template by its path."""
        for template, path, _ in self.templates[:]:
            if path == image_path:
                self.templates.remove((template, path, _))
                print(f"Removed template: {image_path}")
                return True
        print(f"Template not found: {image_path}")
        return False

    def update_click_action(self, image_path: str, click_action: str) -> bool:
        """Update the click action for a specific template."""
        for i, (template, path, _) in enumerate(self.templates):
            if path == image_path:
                self.templates[i] = (template, path, click_action)
                print(f"Updated click action for {image_path} to {click_action}")
                return True
        return False

    def capture_screen(self) -> np.ndarray:
        """Capture the current screen as a grayscale image."""
        screenshot = pyautogui.screenshot()
        screen = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
        screen = cv2.resize(screen, (0, 0), fx=self.scale_factor, fy=self.scale_factor)
        return screen

    def find_template(self, screen: np.ndarray, template: np.ndarray, image_path: str) -> Tuple[float, Tuple[int, int], str]:
        """Find the best match for a template in the screen image."""
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        return max_val, max_loc, image_path

    def click_on_template(self, max_loc: Tuple[int, int], template_shape: Tuple[int, int], image_path: str, click_action: str, log_callback):
        """Click at the center of the matched template with specified action and log the action."""
        center_x = int(max_loc[0] / self.scale_factor) + template_shape[1] // 2
        center_y = int(max_loc[1] / self.scale_factor) + template_shape[0] // 2
        if click_action == "Left Click":
            pyautogui.click(center_x, center_y)
        elif click_action == "Right Click":
            pyautogui.rightClick(center_x, center_y)
        elif click_action == "Double Click":
            pyautogui.doubleClick(center_x, center_y)
        log_callback(f"{click_action} on {os.path.basename(image_path)} at ({center_x}, {center_y})")

    def process_template(self, template: np.ndarray, image_path: str, click_action: str, screen: np.ndarray, log_callback):
        """Process a single template match and click if found."""
        max_val, max_loc, image_path = self.find_template(screen, template, image_path)
        if max_val >= self.confidence_threshold:
            print(f"Found match for {image_path}: confidence={max_val:.2f}")
            log_callback(f"Match found for {os.path.basename(image_path)}: confidence={max_val:.2f}")
            self.click_on_template(max_loc, template.shape, image_path, click_action, log_callback)
        else:
            print(f"No match for {image_path}: confidence={max_val:.2f}")

    def run(self, log_callback):
        """Main loop with parallel template matching."""
        self.running = True
        try:
            while self.running:
                if not self.paused:
                    start_time = time.time()
                    screen = self.capture_screen()
                    futures = [
                        self.executor.submit(self.process_template, template, image_path, click_action, screen, log_callback)
                        for template, image_path, click_action in self.templates
                    ]
                    for future in futures:
                        future.result()
                    elapsed = time.time() - start_time
                    time.sleep(max(0, self.interval - elapsed))
                else:
                    time.sleep(0.1)
        except KeyboardInterrupt:
            print("Program terminated by user")
            self.executor.shutdown()

    def stop(self):
        """Stop the clicking process."""
        self.running = False

    def toggle_pause(self):
        """Toggle pause state."""
        self.paused = not self.paused
        return self.paused

class ClickerGUI:
    def __init__(self, clicker: ImageClicker):
        self.clicker = clicker
        self.root = tk.Tk()
        self.root.title("Trigger Clicker")
        self.root.geometry("600x850")
        self.root.resizable(False, False)

        # Theme definitions
        self.themes = {
            "Light": {
                "bg": "#f0f0f0",
                "fg": "#333333",
                "entry_bg": "#ffffff",
                "button_bg": "#e0e0e0",
                "highlight": "#0078d7",
                "listbox_bg": "#ffffff",
                "listbox_fg": "#333333",
                "listbox_select_bg": "#0078d7",
                "listbox_select_fg": "#ffffff"
            },
            "Dark": {
                "bg": "#212121",
                "fg": "#e0e0e0",
                "entry_bg": "#333333",
                "button_bg": "#424242",
                "highlight": "#42a5f5",
                "listbox_bg": "#333333",
                "listbox_fg": "#e0e0e0",
                "listbox_select_bg": "#42a5f5",
                "listbox_select_fg": "#ffffff"
            }
        }
        self.current_theme = "Light"

        # Available hotkeys and click actions
        self.hotkey_options = ["Ctrl+P", "Ctrl+S", "Ctrl+Q", "F1", "F2", "F3", "Custom"]
        self.click_actions = ["Left Click", "Right Click", "Double Click"]
        self.last_selected_template = None  # Track last selected template index
        self.is_selecting_action = False  # Flag to prevent dropdown reset during selection

        # Style configuration
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Theme selection
        ttk.Label(self.main_frame, text="Theme:").pack(anchor="w")
        self.theme_var = tk.StringVar(value="Light")
        theme_combo = ttk.Combobox(self.main_frame, textvariable=self.theme_var, values=list(self.themes.keys()), state="readonly")
        theme_combo.pack(anchor="w", pady=5)
        theme_combo.bind("<<ComboboxSelected>>", self.change_theme)

        # Template folder
        ttk.Label(self.main_frame, text="Template Folder:").pack(anchor="w")
        self.folder_var = tk.StringVar(value=self.clicker.template_folder)
        folder_frame = ttk.Frame(self.main_frame)
        folder_frame.pack(fill=tk.X, pady=5)
        ttk.Entry(folder_frame, textvariable=self.folder_var, width=40, state='readonly').pack(side=tk.LEFT)
        ttk.Button(folder_frame, text="Browse", command=self.select_folder).pack(side=tk.LEFT, padx=5)

        # Template management
        ttk.Label(self.main_frame, text="Loaded Templates:").pack(anchor="w")
        self.template_frame = ttk.Frame(self.main_frame)
        self.template_frame.pack(fill=tk.X, pady=5)
        self.template_listbox = tk.Listbox(self.template_frame, height=5, width=40, selectmode=tk.SINGLE)
        self.template_listbox.pack(side=tk.LEFT, fill=tk.X)
        self.template_listbox.bind('<<ListboxSelect>>', self.on_template_select)
        self.action_var = tk.StringVar(value="Left Click")
        self.action_combo = ttk.Combobox(self.template_frame, textvariable=self.action_var, values=self.click_actions, state="readonly", width=15)
        self.action_combo.pack(side=tk.LEFT, padx=5)
        self.action_combo.bind("<<ComboboxSelected>>", self.on_action_select)
        ttk.Button(self.template_frame, text="Apply Action", command=self.update_click_action).pack(side=tk.LEFT, padx=5)
        template_button_frame = ttk.Frame(self.main_frame)
        template_button_frame.pack(fill=tk.X)
        ttk.Button(template_button_frame, text="Add Template", command=self.add_template).pack(side=tk.LEFT, padx=5)
        ttk.Button(template_button_frame, text="Remove Selected", command=self.remove_template).pack(side=tk.LEFT, padx=5)
        ttk.Button(template_button_frame, text="View Templates", command=self.view_templates).pack(side=tk.LEFT, padx=5)
        self.update_template_list()

        # Confidence threshold
        ttk.Label(self.main_frame, text="Confidence Threshold (0.0-1.0):").pack(anchor="w")
        self.confidence_var = tk.DoubleVar(value=self.clicker.confidence_threshold)
        ttk.Entry(self.main_frame, textvariable=self.confidence_var, width=10).pack(anchor="w", pady=5)

        # Scale factor
        ttk.Label(self.main_frame, text="Scale Factor (0.1-1.0):").pack(anchor="w")
        self.scale_var = tk.DoubleVar(value=self.clicker.scale_factor)
        ttk.Entry(self.main_frame, textvariable=self.scale_var, width=10).pack(anchor="w", pady=5)

        # Scan interval
        ttk.Label(self.main_frame, text="Scan Interval (0.1-2.0 seconds):").pack(anchor="w")
        self.interval_var = tk.DoubleVar(value=self.clicker.interval)
        ttk.Entry(self.main_frame, textvariable=self.interval_var, width=10).pack(anchor="w", pady=5)

        # Hotkey selection
        ttk.Label(self.main_frame, text="Toggle Hotkey:").pack(anchor="w")
        self.hotkey_var = tk.StringVar(value="Ctrl+P")
        hotkey_combo = ttk.Combobox(self.main_frame, textvariable=self.hotkey_var, values=self.hotkey_options, state="readonly")
        hotkey_combo.pack(anchor="w", pady=5)
        hotkey_combo.bind("<<ComboboxSelected>>", self.update_hotkey)
        self.hotkey_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.main_frame, text="Enable Toggle Hotkey", variable=self.hotkey_enabled_var, 
                       command=self.toggle_hotkey).pack(anchor="w", pady=5)
        self.custom_hotkey_var = tk.StringVar(value="")
        self.custom_hotkey_entry = ttk.Entry(self.main_frame, textvariable=self.custom_hotkey_var, width=20, state='disabled')
        self.custom_hotkey_entry.pack(anchor="w", pady=5)
        self.custom_hotkey_entry.bind("<KeyRelease>", self.validate_custom_hotkey)
        self.update_hotkey()

        # Control buttons
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        ttk.Button(button_frame, text="Start", command=self.start_clicker).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Stop", command=self.stop_clicker).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Reload Templates", command=self.reload_templates).pack(side=tk.LEFT, padx=5)

        # Match log
        ttk.Label(self.main_frame, text="Match Log:").pack(anchor="w")
        self.log_text = tk.Text(self.main_frame, height=8, width=50, state='disabled', font=("Helvetica", 9))
        self.log_text.pack(fill=tk.BOTH, pady=5)
        scrollbar = ttk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text['yscrollcommand'] = scrollbar.set

        # Status bar
        self.status_var = tk.StringVar(value=f"Loaded {len(self.clicker.templates)} templates")
        ttk.Label(self.main_frame, textvariable=self.status_var).pack(fill=tk.X, pady=5)

        # Warning
        ttk.Label(self.main_frame, text="Warning: Avoid using in online games to prevent bans.", 
                 foreground="red", font=("Helvetica", 10, "bold")).pack(pady=5)

        # Apply theme after all widgets are created
        self.update_theme()

        # Load settings
        self.load_settings()

        # Bind window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def update_theme(self):
        """Update widget styles based on the current theme."""
        theme = self.themes[self.current_theme]
        self.root.configure(bg=theme["bg"])
        self.main_frame.configure(style="Main.TFrame")
        self.style.configure("Main.TFrame", background=theme["bg"])
        self.style.configure("TLabel", background=theme["bg"], foreground=theme["fg"])
        self.style.configure("TButton", background=theme["button_bg"], foreground=theme["fg"])
        self.style.configure("TEntry", fieldbackground=theme["entry_bg"], foreground=theme["fg"])
        self.style.configure("TCombobox", fieldbackground=theme["entry_bg"], foreground=theme["fg"], 
                           selectbackground=theme["listbox_select_bg"], selectforeground=theme["listbox_select_fg"])
        self.style.configure("TCombobox.TEntry", fieldbackground=theme["entry_bg"], foreground=theme["fg"])
        if hasattr(self, 'log_text'):
            self.log_text.configure(bg=theme["listbox_bg"], fg=theme["listbox_fg"], 
                                  selectbackground=theme["listbox_select_bg"], selectforeground=theme["listbox_select_fg"])
        if hasattr(self, 'template_listbox'):
            self.template_listbox.configure(bg=theme["listbox_bg"], fg=theme["listbox_fg"], 
                                          selectbackground=theme["listbox_select_bg"], selectforeground=theme["listbox_select_fg"])

    def change_theme(self, event=None):
        """Change the GUI theme."""
        self.current_theme = self.theme_var.get()
        self.update_theme()
        self.log(f"Theme changed to {self.current_theme}")
        self.save_settings()

    def log(self, message: str):
        """Add a message to the log with timestamp."""
        if hasattr(self, 'log_text'):
            self.log_text.configure(state='normal')
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_text.see(tk.END)
            self.log_text.configure(state='disabled')

    def select_folder(self):
        """Open a dialog to select the template folder."""
        folder = filedialog.askdirectory()
        if folder:
            self.folder_var.set(folder)
            self.clicker.template_folder = folder
            self.reload_templates()

    def add_template(self):
        """Add a single template image with selected click action."""
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")])
        if file_path:
            selected_action = self.action_var.get()
            if selected_action not in self.click_actions:
                selected_action = "Left Click"
                self.action_var.set(selected_action)
            if self.clicker.add_template(file_path, selected_action):
                self.update_template_list()
                self.status_var.set(f"Loaded {len(self.clicker.templates)} templates")
                self.log(f"Added template: {os.path.basename(file_path)} with action {selected_action}")
                self.save_settings()

    def remove_template(self):
        """Remove the selected template."""
        if self.last_selected_template is None:
            messagebox.showinfo("Info", "No template selected")
            return
        template_name = self.template_listbox.get(self.last_selected_template)
        for _, path, _ in self.clicker.templates:
            if os.path.basename(path) == template_name:
                self.clicker.remove_template(path)
                self.last_selected_template = None
                self.update_template_list()
                self.status_var.set(f"Loaded {len(self.clicker.templates)} templates")
                self.log(f"Removed template: {template_name}")
                self.save_settings()
                break

    def on_template_select(self, event=None):
        """Handle template listbox selection and store the selected index."""
        selection = self.template_listbox.curselection()
        if selection:
            self.last_selected_template = selection[0]
            self.log(f"Template selected: {self.template_listbox.get(self.last_selected_template)}, index: {self.last_selected_template}")
            self.update_action_dropdown()
        else:
            self.last_selected_template = None
            self.action_var.set("Left Click")
            self.action_combo['values'] = self.click_actions
            self.log("No template selected, set dropdown to default: Left Click")

    def on_action_select(self, event=None):
        """Handle action dropdown selection."""
        self.is_selecting_action = True
        selected_action = self.action_var.get()
        self.log(f"Action selected in dropdown: {selected_action}, last_selected_template: {self.last_selected_template}")
        if self.last_selected_template is not None:
            self.template_listbox.selection_clear(0, tk.END)
            self.template_listbox.selection_set(self.last_selected_template)
            self.template_listbox.activate(self.last_selected_template)
        self.root.after(100, lambda: setattr(self, 'is_selecting_action', False))  # Reset flag after a short delay

    def update_template_list(self):
        """Update the listbox with current templates and set action dropdown."""
        self.template_listbox.delete(0, tk.END)
        for _, path, click_action in self.clicker.templates:
            self.template_listbox.insert(tk.END, os.path.basename(path))
        if self.last_selected_template is not None and self.last_selected_template < self.template_listbox.size():
            self.template_listbox.selection_set(self.last_selected_template)
            self.template_listbox.activate(self.last_selected_template)
            self.log(f"Restored template selection: {self.template_listbox.get(self.last_selected_template)}, index: {self.last_selected_template}")
        self.update_action_dropdown()

    def update_action_dropdown(self):
        """Update the action dropdown to reflect the selected template's click action."""
        self.action_combo['values'] = self.click_actions  # Ensure all actions are available
        if self.is_selecting_action:
            self.log("Skipping dropdown update during action selection")
            return
        selection = self.template_listbox.curselection()
        if selection and self.last_selected_template == selection[0]:
            template_name = self.template_listbox.get(self.last_selected_template)
            for _, path, click_action in self.clicker.templates:
                if os.path.basename(path) == template_name:
                    self.action_var.set(click_action)
                    self.log(f"Set dropdown to {click_action} for {template_name}, index: {self.last_selected_template}")
                    return
        self.last_selected_template = None
        self.action_var.set("Left Click")
        self.log("No template selected or selection mismatch, set dropdown to default: Left Click")

    def update_click_action(self):
        """Update the click action for the selected template."""
        if self.last_selected_template is None or not self.template_listbox.curselection():
            self.log("No template selected for click action update")
            messagebox.showinfo("Info", "Please select a template to update its click action")
            return
        template_name = self.template_listbox.get(self.last_selected_template)
        selected_action = self.action_var.get()
        if selected_action not in self.click_actions:
            self.log(f"Invalid click action selected: {selected_action}")
            self.action_var.set("Left Click")
            selected_action = "Left Click"
        for _, path, _ in self.clicker.templates:
            if os.path.basename(path) == template_name:
                self.clicker.update_click_action(path, selected_action)
                self.log(f"Applied click action for {template_name} to {selected_action}")
                self.save_settings()
                self.update_template_list()  # Refresh to ensure selection is maintained
                break

    def reload_templates(self):
        """Reload templates from the selected folder."""
        try:
            self.clicker.load_templates()
            self.last_selected_template = None
            self.update_template_list()
            self.status_var.set(f"Loaded {len(self.clicker.templates)} templates")
            self.log("Templates reloaded")
            self.save_settings()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load templates: {e}")

    def start_clicker(self):
        """Start the clicker in a separate thread."""
        try:
            confidence = self.confidence_var.get()
            scale = self.scale_var.get()
            interval = self.interval_var.get()
            if not (0.0 <= confidence <= 1.0):
                raise ValueError("Confidence threshold must be between 0.0 and 1.0")
            if not (0.1 <= scale <= 1.0):
                raise ValueError("Scale factor must be between 0.1 and 1.0")
            if not (0.1 <= interval <= 2.0):
                raise ValueError("Scan interval must be between 0.1 and 2.0 seconds")
            if not self.clicker.templates:
                raise ValueError("No templates loaded. Select a folder with images.")
            self.clicker.confidence_threshold = confidence
            self.clicker.scale_factor = scale
            self.clicker.interval = interval
            self.status_var.set("Running...")
            self.log("Clicker started")
            threading.Thread(target=self.clicker.run, args=(self.log,), daemon=True).start()
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def stop_clicker(self):
        """Stop the clicker."""
        self.clicker.stop()
        self.status_var.set("Stopped")
        self.log("Clicker stopped")

    def validate_custom_hotkey(self, event=None):
        """Validate and apply custom hotkey on key release."""
        if self.hotkey_var.get() == "Custom" and self.hotkey_enabled_var.get():
            hotkey = self.custom_hotkey_var.get().strip().lower()
            if hotkey:
                try:
                    # Remove previous hotkey
                    try:
                        keyboard.remove_hotkey(hotkey)
                    except:
                        pass
                    keyboard.add_hotkey(hotkey, self.toggle_pause)
                    self.log(f"Custom hotkey set to {hotkey}")
                    self.custom_hotkey_entry.selection_clear()
                    self.save_settings()
                except ValueError as e:
                    self.log(f"Invalid custom hotkey: {hotkey}")
                    self.custom_hotkey_var.set("")
                    self.hotkey_var.set("Ctrl+P")
                    try:
                        keyboard.add_hotkey("ctrl+p", self.toggle_pause)
                        self.log("Reverted to default hotkey Ctrl+P")
                    except:
                        pass
                    self.custom_hotkey_entry.selection_clear()

    def update_hotkey(self, event=None):
        """Update the hotkey configuration."""
        if self.hotkey_var.get() == "Custom":
            self.custom_hotkey_entry.configure(state='normal')
        else:
            self.custom_hotkey_entry.configure(state='disabled')
            self.custom_hotkey_var.set("")
            if self.hotkey_enabled_var.get():
                try:
                    keyboard.remove_hotkey(self.hotkey_var.get().lower())
                except:
                    pass
                try:
                    keyboard.add_hotkey(self.hotkey_var.get().lower(), self.toggle_pause)
                    self.log(f"Hotkey set to {self.hotkey_var.get()}")
                except ValueError as e:
                    self.log(f"Invalid hotkey: {self.hotkey_var.get()}")
                    messagebox.showerror("Error", f"Invalid hotkey: {self.hotkey_var.get()}")
                    self.hotkey_var.set("Ctrl+P")
                    keyboard.add_hotkey("ctrl+p", self.toggle_pause)
                    self.log("Reverted to default hotkey Ctrl+P")
            self.custom_hotkey_entry.selection_clear()
        self.save_settings()

    def toggle_hotkey(self):
        """Enable or disable the toggle hotkey."""
        if self.hotkey_enabled_var.get():
            hotkey = self.hotkey_var.get().lower() if self.hotkey_var.get() != "Custom" else self.custom_hotkey_var.get().lower()
            if not hotkey and self.hotkey_var.get() == "Custom":
                self.log("Custom hotkey not specified")
                messagebox.showerror("Error", "Please specify a custom hotkey")
                self.hotkey_enabled_var.set(False)
                return
            try:
                keyboard.add_hotkey(hotkey, self.toggle_pause)
                self.log(f"Toggle hotkey enabled: {hotkey}")
            except ValueError as e:
                self.log(f"Invalid hotkey: {hotkey}")
                messagebox.showerror("Error", f"Invalid hotkey: {hotkey}")
                self.hotkey_enabled_var.set(False)
                self.hotkey_var.set("Ctrl+P")
                keyboard.add_hotkey("ctrl+p", self.toggle_pause)
                self.log("Reverted to default hotkey Ctrl+P")
        else:
            try:
                hotkey = self.hotkey_var.get().lower() if self.hotkey_var.get() != "Custom" else self.custom_hotkey_var.get().lower()
                keyboard.remove_hotkey(hotkey)
                self.log("Toggle hotkey disabled")
            except:
                pass
        self.custom_hotkey_entry.selection_clear()
        self.save_settings()

    def toggle_pause(self):
        """Toggle pause state via hotkey."""
        paused = self.clicker.toggle_pause()
        self.status_var.set("Paused" if paused else "Running")
        self.log("Clicker paused" if paused else "Clicker resumed")

    def view_templates(self):
        """Show a window with previews of loaded templates."""
        if not self.clicker.templates:
            messagebox.showinfo("Info", "No templates loaded")
            return

        preview_window = tk.Toplevel(self.root)
        preview_window.title("Template Previews")
        preview_window.geometry("600x400")
        preview_window.configure(bg=self.themes[self.current_theme]["bg"])
        canvas = tk.Canvas(preview_window, bg=self.themes[self.current_theme]["bg"])
        scrollbar = ttk.Scrollbar(preview_window, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for _, image_path, click_action in self.clicker.templates:
            try:
                img = Image.open(image_path)
                img = img.resize((100, 100), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                label = ttk.Label(scrollable_frame, image=photo, text=f"{os.path.basename(image_path)} ({click_action})", 
                                compound=tk.TOP, background=self.themes[self.current_theme]["bg"],
                                foreground=self.themes[self.current_theme]["fg"])
                label.image = photo
                label.pack(pady=5)
            except Exception as e:
                self.log(f"Failed to load preview for {image_path}: {e}")

    def save_settings(self):
        """Save settings to a JSON file."""
        settings = {
            "template_folder": self.folder_var.get(),
            "confidence_threshold": self.confidence_var.get(),
            "scale_factor": self.scale_var.get(),
            "interval": self.interval_var.get(),
            "hotkey_enabled": self.hotkey_enabled_var.get(),
            "hotkey": self.hotkey_var.get(),
            "custom_hotkey": self.custom_hotkey_var.get(),
            "theme": self.current_theme,
            "templates": [
                {"path": path, "click_action": click_action}
                for _, path, click_action in self.clicker.templates
            ]
        }
        try:
            with open("triggerclicker_settings.json", "w") as f:
                json.dump(settings, f, indent=4)
            self.log("Settings saved")
        except Exception as e:
            self.log(f"Failed to save settings: {e}")

    def load_settings(self):
        """Load settings from a JSON file."""
        try:
            if os.path.exists("triggerclicker_settings.json"):
                with open("triggerclicker_settings.json", "r") as f:
                    settings = json.load(f)
                self.folder_var.set(settings.get("template_folder", "templates"))
                self.clicker.template_folder = self.folder_var.get()
                self.confidence_var.set(settings.get("confidence_threshold", 0.8))
                self.scale_var.set(settings.get("scale_factor", 0.5))
                self.interval_var.set(settings.get("interval", 0.5))
                self.hotkey_enabled_var.set(settings.get("hotkey_enabled", False))
                self.hotkey_var.set(settings.get("hotkey", "Ctrl+P"))
                self.custom_hotkey_var.set(settings.get("custom_hotkey", ""))
                self.current_theme = settings.get("theme", "Light")
                self.theme_var.set(self.current_theme)
                self.clicker.templates.clear()
                for template_data in settings.get("templates", []):
                    path = template_data.get("path", "")
                    click_action = template_data.get("click_action", "Left Click")
                    if os.path.exists(path):
                        self.clicker.add_template(path, click_action)
                self.update_template_list()
                self.status_var.set(f"Loaded {len(self.clicker.templates)} templates")
                if self.hotkey_var.get() == "Custom":
                    self.custom_hotkey_entry.configure(state='normal')
                if self.hotkey_enabled_var.get():
                    hotkey = self.hotkey_var.get().lower() if self.hotkey_var.get() != "Custom" else self.custom_hotkey_var.get().lower()
                    try:
                        keyboard.add_hotkey(hotkey, self.toggle_pause)
                        self.log(f"Settings loaded, hotkey enabled: {hotkey}")
                    except ValueError as e:
                        self.log(f"Invalid hotkey in settings: {hotkey}")
                        self.hotkey_var.set("Ctrl+P")
                        self.custom_hotkey_var.set("")
                        keyboard.add_hotkey("ctrl+p", self.toggle_pause)
                        self.log("Reverted to default hotkey Ctrl+P")
                else:
                    self.log("Settings loaded")
        except Exception as e:
            self.log(f"Failed to load settings: {e}")
        self.update_theme()

    def on_closing(self):
        """Handle window close."""
        self.clicker.stop()
        self.save_settings()
        self.root.destroy()

    def run(self):
        """Start the GUI main loop."""
        self.root.mainloop()

def main():
    clicker = ImageClicker(template_folder="templates")
    gui = ClickerGUI(clicker)
    gui.run()

if __name__ == "__main__":
    main()