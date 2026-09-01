import sys
import customtkinter as ctk
import keyboard
import winsound
import json
import os
import threading
import time
import pystray
from PIL import Image, ImageDraw
import pyperclip


# =========================================================
# Settings
# =========================================================

APP_NAME = "Macro"
MACROS_FILE = "macros.json"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# =========================================================
# Macro Management
# =========================================================

def get_macros_path():
    if getattr(sys, "frozen", False):
        base_path = os.path.dirname(sys.executable)

    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(
        base_path,
        MACROS_FILE
    )


def load_macros():
    path = get_macros_path()

    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as file:
            json.dump({}, file, indent=4, ensure_ascii=False)
        return {}

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception as error:
        print(f"Error loading macros: {error}")
        return {}


def save_macros():
    path = get_macros_path()

    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            macros,
            file,
            indent=4,
            ensure_ascii=False
        )


macros = load_macros()


# =========================================================
# Global Macro Engine
# =========================================================

macro_enabled = True
is_executing_macro = False

buffer = ""
buffer_lock = threading.Lock()


def on_key(event):
    global buffer

    if is_executing_macro:
        return

    if not macro_enabled:
        return

    if event.event_type != keyboard.KEY_DOWN:
        return

    with buffer_lock:

        if len(event.name) == 1:

            buffer += event.name

            if len(buffer) > 150:
                buffer = buffer[-150:]

            for trigger, content in list(macros.items()):

                if buffer.endswith(trigger):

                    print(f"Macro Detected: {trigger}")

                    threading.Thread(
                        target=execute_macro,
                        args=(trigger, content),
                        daemon=True
                    ).start()

                    buffer = ""

                    break

        elif event.name == "space":
            buffer += " "

        elif event.name == "backspace":

            if buffer:
                buffer = buffer[:-1]

        elif event.name in [
            "enter",
            "tab",
            "esc"
        ]:
            buffer = ""


def execute_macro(trigger, content):
    """Execute a macro."""

    global is_executing_macro

    try:

        is_executing_macro = True

        time.sleep(0.05)

        # =================================================
        # Erases the Trigger
        # =================================================

        for _ in range(len(trigger)):
            keyboard.press_and_release("backspace")
            time.sleep(0.01)

        time.sleep(0.05)

        # =================================================
        # Content Insertion
        # =================================================

        try:

            old_clipboard = pyperclip.paste()

            pyperclip.copy(content)

            keyboard.press_and_release("ctrl+v")

            time.sleep(0.2)

            pyperclip.copy(old_clipboard)

        except Exception as error:

            print(f"Error using clipboard: {error}")

            # Fallback
            keyboard.write(content)

        # =================================================
        # Sound
        # =================================================

        winsound.MessageBeep(
            winsound.MB_OK
        )

    except Exception as error:

        print(
            f"Error executing macro: {error}"
        )

    finally:

        time.sleep(0.05)

        is_executing_macro = False


# =========================================================
# Interface
# =========================================================

class MacroApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        # -------------------------------------------------
        # WINDOW
        # -------------------------------------------------

        self.title(APP_NAME)

        self.geometry("850x600")

        self.minsize(
            700,
            500
        )

        # Close Window = Minimize to tray
        self.protocol(
            "WM_DELETE_WINDOW",
            self.hide_window
        )

        # -------------------------------------------------
        # MAIN GRID
        # -------------------------------------------------

        self.grid_columnconfigure(
            0,
            weight=1
        )

        self.grid_rowconfigure(
            2,
            weight=1
        )

        # =================================================
        # Header
        # =================================================

        header = ctk.CTkFrame(
            self,
            height=90,
            corner_radius=0
        )

        header.grid(
            row=0,
            column=0,
            sticky="ew"
        )

        header.grid_columnconfigure(
            0,
            weight=1
        )

        # Title

        title_frame = ctk.CTkFrame(
            header,
            fg_color="transparent"
        )

        title_frame.grid(
            row=0,
            column=0,
            padx=25,
            pady=15,
            sticky="w"
        )

        ctk.CTkLabel(
            title_frame,
            text="⚡ MACRO",
            font=ctk.CTkFont(
                size=28,
                weight="bold"
            )
        ).pack(
            anchor="w"
        )

        ctk.CTkLabel(
            title_frame,
            text="Text Shortcut Manager",
            text_color="gray"
        ).pack(
            anchor="w"
        )

        # Status

        self.status_label = ctk.CTkLabel(
            header,
            text="● ACTIVE",
            text_color="#3CCF4E",
            font=ctk.CTkFont(
                size=14,
                weight="bold"
            )
        )

        self.status_label.grid(
            row=0,
            column=1,
            padx=25
        )

        # =================================================
        # Toolbar
        # =================================================

        toolbar = ctk.CTkFrame(
            self,
            height=65,
            corner_radius=0
        )

        toolbar.grid(
            row=1,
            column=0,
            sticky="ew"
        )

        toolbar.grid_columnconfigure(
            1,
            weight=1
        )

        # Novo Macro

        add_button = ctk.CTkButton(
            toolbar,
            text="+ New Macro",
            command=self.open_add_macro
        )

        add_button.grid(
            row=0,
            column=0,
            padx=20,
            pady=12
        )

        # Pesquisa

        self.search_entry = ctk.CTkEntry(
            toolbar,
            placeholder_text="Search Macros..."
        )

        self.search_entry.grid(
            row=0,
            column=1,
            padx=20,
            pady=12,
            sticky="ew"
        )

        self.search_entry.bind(
            "<KeyRelease>",
            lambda event: self.refresh_macros()
        )

        # Botão Ativar / Desativar

        self.toggle_button = ctk.CTkButton(
            toolbar,
            text="Deactivate",
            width=100,
            fg_color="#8B0000",
            command=self.toggle_macro_system
        )

        self.toggle_button.grid(
            row=0,
            column=2,
            padx=20,
            pady=12
        )

        # =================================================
        # List
        # =================================================

        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            corner_radius=0
        )

        self.scroll_frame.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=15,
            pady=(10, 15)
        )

        self.scroll_frame.grid_columnconfigure(
            0,
            weight=1
        )

        # =================================================
        # Footer
        # =================================================

        self.footer = ctk.CTkLabel(
            self,
            text=f"{len(macros)} set up macros",
            text_color="gray"
        )

        self.footer.grid(
            row=3,
            column=0,
            pady=(0, 10)
        )

        # Load Macros
        self.refresh_macros()

    # =====================================================
    # Update List
    # =====================================================

    def refresh_macros(self):

        # Remove old cards
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        search = self.search_entry.get().lower()

        count = 0

        for trigger, content in macros.items():

            # Search
            if (
                search not in trigger.lower()
                and search not in content.lower()
            ):
                continue

            count += 1

            # Card

            card = ctk.CTkFrame(
                self.scroll_frame,
                corner_radius=12
            )

            card.grid(
                row=count,
                column=0,
                sticky="ew",
                padx=8,
                pady=6
            )

            card.grid_columnconfigure(
                0,
                weight=1
            )

            # Trigger

            trigger_label = ctk.CTkLabel(
                card,
                text=trigger,
                font=ctk.CTkFont(
                    size=18,
                    weight="bold"
                ),
                text_color="#4DA3FF"
            )

            trigger_label.grid(
                row=0,
                column=0,
                padx=18,
                pady=(12, 0),
                sticky="w"
            )

            # Preview

            preview = content.replace(
                "\n",
                " ↵ "
            )

            if len(preview) > 100:
                preview = preview[:100] + "..."

            content_label = ctk.CTkLabel(
                card,
                text=preview,
                text_color="gray",
                anchor="w"
            )

            content_label.grid(
                row=1,
                column=0,
                padx=18,
                pady=(3, 12),
                sticky="ew"
            )

            # Editar

            edit_button = ctk.CTkButton(
                card,
                text="Edit",
                width=75,
                command=lambda t=trigger: self.open_edit_macro(t)
            )

            edit_button.grid(
                row=0,
                column=1,
                rowspan=2,
                padx=(5, 5),
                pady=15
            )

            # Erase

            delete_button = ctk.CTkButton(
                card,
                text="Erase",
                width=75,
                fg_color="#A83232",
                hover_color="#7A2020",
                command=lambda t=trigger: self.delete_macro(t)
            )

            delete_button.grid(
                row=0,
                column=2,
                rowspan=2,
                padx=(0, 15),
                pady=15
            )

        # Update Counter

        self.footer.configure(
            text=f"{len(macros)} set up macros"
        )

    # =====================================================
    # New Macro
    # =====================================================

    def open_add_macro(self):

        self.open_macro_window()

    # =====================================================
    # Edit Macro
    # =====================================================

    def open_edit_macro(self, trigger):

        self.open_macro_window(
            old_trigger=trigger,
            trigger=trigger,
            content=macros[trigger]
        )

    # =====================================================
    # Window Create / Edit
    # =====================================================

    def open_macro_window(
        self,
        old_trigger=None,
        trigger="",
        content=""
    ):

        window = ctk.CTkToplevel(self)

        window.title(
            "Edit Macro"
            if old_trigger
            else "New Macro"
        )

        window.geometry(
            "500x400"
        )

        window.resizable(
            False,
            False
        )

        window.grab_set()

        # -------------------------------------------------
        # Shortcut
        # -------------------------------------------------

        ctk.CTkLabel(
            window,
            text="Shortcut",
            font=ctk.CTkFont(
                size=16,
                weight="bold"
            )
        ).pack(
            anchor="w",
            padx=25,
            pady=(25, 5)
        )

        trigger_entry = ctk.CTkEntry(
            window,
            placeholder_text="Example: .wpp"
        )

        trigger_entry.pack(
            fill="x",
            padx=25
        )

        trigger_entry.insert(
            0,
            trigger
        )

        # -------------------------------------------------
        # Content
        # -------------------------------------------------

        ctk.CTkLabel(
            window,
            text="Content",
            font=ctk.CTkFont(
                size=16,
                weight="bold"
            )
        ).pack(
            anchor="w",
            padx=25,
            pady=(20, 5)
        )

        content_box = ctk.CTkTextbox(
            window,
            height=180
        )

        content_box.pack(
            fill="both",
            expand=True,
            padx=25
        )

        content_box.insert(
            "1.0",
            content
        )

        # -------------------------------------------------
        # Save
        # -------------------------------------------------

        def save():

            new_trigger = trigger_entry.get().strip()

            new_content = content_box.get(
                "1.0",
                "end-1c"
            )

            # Simple Check

            if not new_trigger:
                return

            if not new_content:
                return

            # Remove old if name changed

            if (
                old_trigger
                and old_trigger != new_trigger
            ):
                macros.pop(
                    old_trigger,
                    None
                )

            # Save Macro

            macros[new_trigger] = new_content

            save_macros()

            self.refresh_macros()

            window.destroy()

        save_button = ctk.CTkButton(
            window,
            text="Save Macro",
            command=save
        )

        save_button.pack(
            pady=20
        )

    # =====================================================
    # Erase
    # =====================================================

    def delete_macro(self, trigger):

        macros.pop(
            trigger,
            None
        )

        save_macros()

        self.refresh_macros()

    # =====================================================
    # Activate / Deactivate
    # =====================================================

    def toggle_macro_system(self):

        global macro_enabled

        macro_enabled = not macro_enabled

        if macro_enabled:

            self.status_label.configure(
                text="● ACTIVE",
                text_color="#3CCF4E"
            )

            self.toggle_button.configure(
                text="Deactivate",
                fg_color="#8B0000"
            )

        else:

            self.status_label.configure(
                text="● DEACTIVATED",
                text_color="#FF5555"
            )

            self.toggle_button.configure(
                text="Activate",
                fg_color="#267A3E"
            )

    # =====================================================
    # Close to tray
    # =====================================================

    def hide_window(self):

        self.withdraw()

    # =====================================================
    # Show
    # =====================================================

    def show_window(self):

        self.deiconify()

        self.lift()

        self.focus_force()


# =========================================================
# System Tray
# =========================================================

def create_tray_icon(app):

    # Create Temp Icon

    image = Image.new(
        "RGB",
        (64, 64),
        "#202020"
    )

    draw = ImageDraw.Draw(image)

    draw.rectangle(
        (15, 15, 49, 49),
        fill="#4DA3FF"
    )

    # -----------------------------------------------------
    # Open
    # -----------------------------------------------------

    def show_app(icon, item):

        app.after(
            0,
            app.show_window
        )

    # -----------------------------------------------------
    # Activate / Deactivate
    # -----------------------------------------------------

    def toggle_from_tray(icon, item):

        app.after(
            0,
            app.toggle_macro_system
        )

    # -----------------------------------------------------
    # Exit
    # -----------------------------------------------------

    def quit_app(icon, item):

        icon.stop()

        keyboard.unhook_all()

        app.after(
            0,
            app.destroy
        )

    # -----------------------------------------------------
    # Menu
    # -----------------------------------------------------

    menu = pystray.Menu(

        pystray.MenuItem(
            "Open Macro",
            show_app
        ),

        pystray.MenuItem(
            "Activate / Deactivate",
            toggle_from_tray
        ),

        pystray.Menu.SEPARATOR,

        pystray.MenuItem(
            "Exit",
            quit_app
        )
    )

    # -----------------------------------------------------
    # Create Icon
    # -----------------------------------------------------

    tray = pystray.Icon(
        "Macro",
        image,
        APP_NAME,
        menu
    )

    tray.run()


# =========================================================
# Startup
# =========================================================

if __name__ == "__main__":

    # Global Hook
    keyboard.hook(on_key)

    # Create App
    app = MacroApp()

    # System Tray
    tray_thread = threading.Thread(
        target=create_tray_icon,
        args=(app,),
        daemon=True
    )

    tray_thread.start()

    # Main Interface
    app.mainloop()