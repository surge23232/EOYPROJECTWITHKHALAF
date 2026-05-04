import tkinter as tk
from tkinter import scrolledtext, filedialog, font
import threading
import google.generativeai as genai
import os
import requests
import cv2
from io import BytesIO
from PIL import Image, ImageDraw, ImageTk, ImageSequence
from dotenv import load_dotenv
import random

load_dotenv()

genai.configure(api_key=os.getenv("API_KEY"))

kratos_instructions = (
    "You are Kratos from God of War (2018 and Ragnarök). "
    "You speak in a deep, calm, and intimidating tone. "
    "Your responses are short, blunt, and serious. "
    "You rarely joke and never use modern slang. "
    "You often give harsh wisdom and speak with authority. "
    "You may call the user 'Boy' when appropriate. "
    "You give harsh but meaningful combat wisdom. "
    "Stay fully in character at all times."
)

leon_instructions = (
    "You are Leon S. Kennedy from Resident Evil 4 (2005 and 2023 remake). "
    "You are a seasoned government agent with a dry, sarcastic wit. "
    "You make quippy one-liners and dark jokes even in tense situations. "
    "You're confident, professional, and coolly detached under pressure. "
    "You occasionally reference your experience fighting Ganados, cultists, and bio-weapons. "
    "You speak casually but with a underlying tactical sharpness. "
    "You sometimes say things like 'Heard that', 'Your right hand comes off?', "
    "'Where's everyone going? Bingo?', and similar iconic quips. "
    "You call the user 'rookie' when appropriate. "
    "Stay fully in character at all times."
)

THEMES = {
    "kratos": {
        "name":         "KRATOS",
        "subtitle":     "GOD OF WAR",
        "tagline":      "Speak. Be judged.",
        "greet_header": "⚔  KRATOS SPEAKS\n",
        "greet_body":   "I am here, boy. Ask what you must.\n\n",
        "send_label":   "SPEAK",
        "status_idle":  "Waiting...",
        "status_think": "Thinking...",
        "title_icon":   "⚔",
        "BG_DARK":      "#0a0a0a",
        "BG_MID":       "#111111",
        "BG_PANEL":     "#161616",
        "ACCENT":       "#c0392b",
        "ACCENT2":      "#b8860b",
        "TEXT_LIGHT":   "#e8e0d0",
        "TEXT_DIM":     "#7a7060",
        "BORDER":       "#2a2a2a",
        "USER_COLOR":   "#d4af6a",
        "BOT_COLOR":    "#e8e0d0",
        "TAB_ACTIVE_BG":   "#c0392b",
        "TAB_ACTIVE_FG":   "#e8e0d0",
        "TAB_INACTIVE_BG": "#1a1a1a",
        "TAB_INACTIVE_FG": "#7a7060",
        "instructions":    kratos_instructions,
        "gif_name":        "kratos_thinking.gif",
        "placeholder":     "[ KRATOS ]",
    },
    "leon": {
        "name":         "LEON S. KENNEDY",
        "subtitle":     "RESIDENT EVIL",
        "tagline":      "Can't let you do that.",
        "greet_header": "🔫  LEON S. KENNEDY\n",
        "greet_body":   "Leon Kennedy, U.S. government. Ask away, rookie.\n\n",
        "send_label":   "SEND",
        "status_idle":  "Standing by...",
        "status_think": "Checking...",
        "title_icon":   "🔫",
        "BG_DARK":      "#080c08",
        "BG_MID":       "#0d120d",
        "BG_PANEL":     "#111811",
        "ACCENT":       "#2e5c2e",
        "ACCENT2":      "#8db84a",
        "TEXT_LIGHT":   "#d4dcc8",
        "TEXT_DIM":     "#5a6a50",
        "BORDER":       "#1e2a1e",
        "USER_COLOR":   "#8db84a",
        "BOT_COLOR":    "#d4dcc8",
        "TAB_ACTIVE_BG":   "#2e5c2e",
        "TAB_ACTIVE_FG":   "#d4dcc8",
        "TAB_INACTIVE_BG": "#111811",
        "TAB_INACTIVE_FG": "#5a6a50",
        "instructions":    leon_instructions,
        "gif_name":        "leon_thinking.gif",
        "placeholder":     "[ LEON ]",
    },
}

GIF_SIZE = (220, 220)

def load_image(source):
    if source.startswith("http://") or source.startswith("https://"):
        response = requests.get(source)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
    return Image.open(source)


def extract_frames(video_path, every_n_seconds=1, max_frames=6):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        raise ValueError("Unable to read video.")
    frame_interval = int(fps * every_n_seconds)
    frames, frame_count = [], 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % frame_interval == 0:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(Image.fromarray(frame_rgb))
            if len(frames) >= max_frames:
                break
        frame_count += 1
    cap.release()
    return frames


def load_gif_frames(path, size):
    gif = Image.open(path)
    frames = []
    try:
        while True:
            frame = gif.copy().convert("RGBA").resize(size, Image.LANCZOS)
            frames.append((ImageTk.PhotoImage(frame), gif.info.get("duration", 80)))
            gif.seek(gif.tell() + 1)
    except EOFError:
        pass
    return frames


class MultiCharApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Character AI Chat")
        self.root.geometry("1060x720")
        self.root.minsize(760, 540)
        self.root.resizable(True, True)

        self.active_char = "kratos"

        self.models = {}
        self.chats  = {}
        for key, t in THEMES.items():
            m = genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                system_instruction=t["instructions"],
            )
            self.models[key] = m
            self.chats[key]  = m.start_chat(history=[])

        self.gif_frames  = {k: [] for k in THEMES}
        self.gif_index   = {k: 0   for k in THEMES}
        self.idle_photo  = {k: None for k in THEMES}
        self.gif_playing = False
        self.gif_job     = None

        self._build_fonts()
        self._load_gifs()
        self._build_ui()
        self._apply_theme(self.active_char, initial=True)
        self._greet(self.active_char)

    def _build_fonts(self):
        self.font_title  = font.Font(family="Georgia", size=18, weight="bold")
        self.font_sub    = font.Font(family="Georgia", size=9,  slant="italic")
        self.font_chat   = font.Font(family="Courier", size=11)
        self.font_btn    = font.Font(family="Georgia", size=10, weight="bold")
        self.font_input  = font.Font(family="Courier", size=11)
        self.font_tab    = font.Font(family="Georgia", size=10, weight="bold")

    def _load_gifs(self):
        base = os.path.dirname(os.path.abspath(__file__))
        for key, t in THEMES.items():
            path = os.path.join(base, t["gif_name"])
            if not os.path.exists(path):
                print(f"[GIF not found] {path}")
                continue
            try:
                frames = load_gif_frames(path, GIF_SIZE)
                self.gif_frames[key] = frames
                self.idle_photo[key] = frames[0][0]
            except Exception as e:
                print(f"[GIF load error for {key}] {e}")

    def _gif_tick(self):
        if not self.gif_playing:
            return
        key    = self.active_char
        frames = self.gif_frames[key]
        if not frames:
            return
        photo, delay = frames[self.gif_index[key]]
        self.avatar_label.configure(image=photo)
        self.gif_index[key] = (self.gif_index[key] + 1) % len(frames)
        self.gif_job = self.root.after(delay, self._gif_tick)

    def _start_gif(self):
        if not self.gif_frames[self.active_char]:
            return
        self.gif_playing = True
        self.gif_index[self.active_char] = 0
        self._gif_tick()

    def _stop_gif(self):
        self.gif_playing = False
        if self.gif_job:
            self.root.after_cancel(self.gif_job)
            self.gif_job = None
        photo = self.idle_photo[self.active_char]
        if photo:
            self.avatar_label.configure(image=photo)

    def _build_ui(self):
        t = THEMES[self.active_char]

        self.top_bar = tk.Frame(self.root, height=3)
        self.top_bar.pack(fill="x")

        self.tab_strip = tk.Frame(self.root)
        self.tab_strip.pack(fill="x", padx=0, pady=0)

        self.tab_buttons = {}
        for key in THEMES:
            btn = tk.Button(
                self.tab_strip,
                text=f"{THEMES[key]['title_icon']}  {THEMES[key]['name']}",
                font=self.font_tab,
                relief="flat", bd=0,
                padx=20, pady=8,
                cursor="hand2",
                command=lambda k=key: self._switch_char(k),
            )
            btn.pack(side="left")
            self.tab_buttons[key] = btn

        self.tab_sep = tk.Frame(self.root, height=1)
        self.tab_sep.pack(fill="x")

        self.header = tk.Frame(self.root, pady=8)
        self.header.pack(fill="x", padx=20)

        self.title_frame = tk.Frame(self.header)
        self.title_frame.pack()

        self.title_label = tk.Label(
            self.title_frame, font=self.font_title)
        self.title_label.pack(side="left")

        self.subtitle_label = tk.Label(
            self.title_frame, font=self.font_sub, padx=6)
        self.subtitle_label.pack(side="left")

        self.tagline_label = tk.Label(self.root, font=self.font_sub)
        self.tagline_label.pack()

        self.header_sep = tk.Frame(self.root, height=1)
        self.header_sep.pack(fill="x", pady=(6, 0))

        self.body = tk.Frame(self.root)
        self.body.pack(fill="both", expand=True, padx=14, pady=10)

        self.avatar_col = tk.Frame(self.body, width=GIF_SIZE[0] + 16)
        self.avatar_col.pack(side="left", fill="y", padx=(0, 12))
        self.avatar_col.pack_propagate(False)

        self.avatar_border = tk.Frame(self.avatar_col, padx=2, pady=2)
        self.avatar_border.pack(pady=(6, 0))

        self.avatar_label = tk.Label(
            self.avatar_border,
            width=GIF_SIZE[0], height=GIF_SIZE[1],
            font=self.font_sub,
        )
        self.avatar_label.pack()

        self.status_var = tk.StringVar(value=t["status_idle"])
        self.status_label = tk.Label(
            self.avatar_col, textvariable=self.status_var,
            font=self.font_sub)
        self.status_label.pack(pady=(6, 0))

        self.chat_col = tk.Frame(self.body)
        self.chat_col.pack(side="left", fill="both", expand=True)

        self.chat_frame = tk.Frame(self.chat_col, padx=2, pady=2)
        self.chat_frame.pack(fill="both", expand=True)

        self.chat_box = scrolledtext.ScrolledText(
            self.chat_frame,
            font=self.font_chat,
            insertbackground="#ffffff",
            relief="flat", wrap="word",
            state="disabled",
            padx=14, pady=10, spacing3=4,
        )
        self.chat_box.pack(fill="both", expand=True)

        self.chat_box.tag_configure("user")
        self.chat_box.tag_configure("bot")
        self.chat_box.tag_configure("system")
        self.chat_box.tag_configure("header")

        self.btn_row = tk.Frame(self.root)
        self.btn_row.pack(fill="x", padx=14, pady=(0, 6))

        self.attach_btns = []
        for label, cmd in [
            ("📎 Image",       self._attach_image),
            ("🎥 Video",       self._attach_video),
            ("🎯 Weak Points", self._attach_weakpoints),
        ]:
            b = tk.Button(
                self.btn_row, text=label, command=cmd,
                font=self.font_btn,
                relief="flat", bd=0, padx=12, pady=5, cursor="hand2",
            )
            b.pack(side="left", padx=(0, 6))
            self.attach_btns.append(b)

        self.input_row = tk.Frame(self.root)
        self.input_row.pack(fill="x", padx=14, pady=(0, 12))

        self.input_var = tk.StringVar()
        self.entry_border = tk.Frame(self.input_row, bd=1, relief="flat")
        self.entry_border.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.entry = tk.Entry(
            self.entry_border, textvariable=self.input_var,
            font=self.font_input,
            relief="flat", bd=0,
        )
        self.entry.pack(fill="x", expand=True, ipady=8, padx=8)
        self.entry.bind("<Return>", lambda e: self._send())

        self.send_btn = tk.Button(
            self.input_row,
            font=self.font_btn,
            relief="flat", bd=0, padx=18, pady=8, cursor="hand2",
            command=self._send,
        )
        self.send_btn.pack(side="right")

        self.bottom_bar = tk.Frame(self.root, height=3)
        self.bottom_bar.pack(fill="x", side="bottom")

    def _apply_theme(self, key, initial=False):
        t = THEMES[key]

        self.root.configure(bg=t["BG_DARK"])
        self.top_bar.configure(bg=t["ACCENT"])
        self.bottom_bar.configure(bg=t["ACCENT"])

        self.tab_strip.configure(bg=t["BG_MID"])
        for k, btn in self.tab_buttons.items():
            if k == key:
                btn.configure(
                    bg=t["TAB_ACTIVE_BG"], fg=t["TAB_ACTIVE_FG"],
                    activebackground=t["ACCENT"], activeforeground=t["TEXT_LIGHT"])
            else:
                btn.configure(
                    bg=t["TAB_INACTIVE_BG"], fg=t["TAB_INACTIVE_FG"],
                    activebackground=t["BG_MID"], activeforeground=t["TEXT_DIM"])

        self.tab_sep.configure(bg=t["BORDER"])
        self.header.configure(bg=t["BG_DARK"])
        self.title_frame.configure(bg=t["BG_DARK"])
        self.title_label.configure(
            text=f"{t['title_icon']}  {t['name']}",
            fg=t["ACCENT2"], bg=t["BG_DARK"])
        self.subtitle_label.configure(
            text=f"  {t['subtitle']}",
            fg=t["TEXT_DIM"], bg=t["BG_DARK"])
        self.tagline_label.configure(
            text=t["tagline"], fg=t["TEXT_DIM"], bg=t["BG_DARK"])
        self.header_sep.configure(bg=t["BORDER"])

        self.body.configure(bg=t["BG_DARK"])
        self.avatar_col.configure(bg=t["BG_DARK"])
        self.avatar_border.configure(bg=t["ACCENT"])
        self.avatar_label.configure(
            bg=t["BG_DARK"], fg=t["TEXT_DIM"],
            text="" if self.idle_photo[key] else t["placeholder"])
        if self.idle_photo[key]:
            self.avatar_label.configure(image=self.idle_photo[key])

        self.status_label.configure(fg=t["TEXT_DIM"], bg=t["BG_DARK"])
        self.status_var.set(t["status_idle"])

        self.chat_col.configure(bg=t["BG_DARK"])
        self.chat_frame.configure(bg=t["BG_MID"])
        self.chat_box.configure(
            bg=t["BG_PANEL"], fg=t["TEXT_LIGHT"],
            selectbackground=t["ACCENT"],
            insertbackground=t["TEXT_LIGHT"])
        self.chat_box.tag_configure(
            "user", foreground=t["USER_COLOR"],
            font=font.Font(family="Courier", size=11, weight="bold"))
        self.chat_box.tag_configure(
            "bot", foreground=t["BOT_COLOR"], font=self.font_chat)
        self.chat_box.tag_configure(
            "system", foreground=t["TEXT_DIM"],
            font=font.Font(family="Georgia", size=10, slant="italic"))
        self.chat_box.tag_configure(
            "header", foreground=t["ACCENT2"],
            font=font.Font(family="Georgia", size=10, weight="bold"))

        self.btn_row.configure(bg=t["BG_DARK"])
        for b in self.attach_btns:
            b.configure(
                bg=t["BG_PANEL"], fg=t["TEXT_DIM"],
                activebackground=t["ACCENT"], activeforeground=t["TEXT_LIGHT"])

        self.input_row.configure(bg=t["BG_DARK"])
        self.entry_border.configure(bg=t["BORDER"])
        self.entry.configure(
            bg=t["BG_PANEL"], fg=t["TEXT_LIGHT"],
            insertbackground=t["ACCENT2"],
            selectbackground=t["ACCENT"])

        self.send_btn.configure(
            text=t["send_label"],
            bg=t["ACCENT"], fg=t["TEXT_LIGHT"],
            activebackground=t["ACCENT2"], activeforeground=t["TEXT_LIGHT"])

    def _switch_char(self, key):
        if key == self.active_char:
            return
        self._stop_gif()
        self.active_char = key
        self._apply_theme(key)
        self._reload_chat_display()

    def _reload_chat_display(self):
        """Clear and re-render the chat box for the current character's stored history."""
        self.chat_box.configure(state="normal")
        self.chat_box.delete("1.0", "end")
        self.chat_box.configure(state="disabled")
        if not self.chats[self.active_char].history:
            self._greet(self.active_char)
        else:
            t = THEMES[self.active_char]
            self._append(f"— switched to {t['name']} —\n\n", "system")

    def _greet(self, key):
        t = THEMES[key]
        self._append(t["greet_header"], "header")
        self._append(t["greet_body"],   "bot")

    def _append(self, text, tag="bot"):
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", text, tag)
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")

    def _send(self, message=None, image=None, video_path=None, mode="text"):
        text = message or self.input_var.get().strip()
        if not text and mode == "text":
            return
        if mode == "text":
            self._append(f"You: {text}\n", "user")
            self.input_var.set("")
        self.send_btn.configure(state="disabled",
                                text=THEMES[self.active_char]["status_think"])
        self.status_var.set(THEMES[self.active_char]["status_think"])
        self._start_gif()
        threading.Thread(
            target=self._call_api,
            args=(text, image, video_path, mode, self.active_char),
            daemon=True,
        ).start()

    def _call_api(self, text, image, video_path, mode, char_key):
        chat_session = self.chats[char_key]
        try:
            if mode == "image" and image:
                response = chat_session.send_message([
                    "Study this image as a warrior. Judge strength and weakness.", image])
            elif mode == "video" and video_path:
                frames = extract_frames(video_path)
                if not frames:
                    self.root.after(0, lambda: self._append(
                        "There is nothing to analyze.\n\n", "bot"))
                    return
                response = chat_session.send_message([
                    "Analyze this combat. Judge technique, mistakes, aggression, and intent.",
                    *frames])
            elif mode == "weakpoints" and image:
                response = chat_session.send_message([
                    "Study this enemy as a warrior. Describe weak points and approximate "
                    "location visually (e.g., 'left shoulder', 'center chest').", image])
                draw = ImageDraw.Draw(image)
                w, h = image.size
                for _ in range(3):
                    x, y, r = random.randint(0, w), random.randint(0, h), 14
                    draw.ellipse((x - r, y - r, x + r, y + r),
                                 fill=(220, 30, 30, 200))
                save_path = "weakpoints_marked.png"
                image.save(save_path)
                self.root.after(0, lambda: self._append(
                    f"[Weak points marked → saved as '{save_path}']\n", "system"))
            else:
                response = chat_session.send_message(text)

            reply = response.text
            if self.active_char == char_key:
                self.root.after(0, lambda: self._on_response(reply, char_key))
        except Exception as e:
            err = str(e)
            if self.active_char == char_key:
                self.root.after(0, lambda: self._on_error(err, char_key))

    def _on_response(self, reply, char_key):
        self._stop_gif()
        t = THEMES[char_key]
        self.status_var.set(t["status_idle"])
        self._append(f"{t['name'].split()[0].capitalize()}: {reply}\n\n", "bot")
        self.send_btn.configure(state="normal", text=t["send_label"])

    def _on_error(self, err, char_key):
        self._stop_gif()
        t = THEMES[char_key]
        self.status_var.set(t["status_idle"])
        self._append(f"[Error: {err}]\n\n", "system")
        self.send_btn.configure(state="normal", text=t["send_label"])

    def _attach_image(self):
        path = filedialog.askopenfilename(
            title="Choose an image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"),
                       ("All", "*.*")])
        if not path:
            return
        try:
            image = load_image(path)
            self._append(f"You: [Image attached: {os.path.basename(path)}]\n", "user")
            self._send(message="image", image=image, mode="image")
        except Exception as e:
            self._append(f"[Could not load image: {e}]\n", "system")

    def _attach_video(self):
        path = filedialog.askopenfilename(
            title="Choose a video",
            filetypes=[("Videos", "*.mp4 *.avi *.mov *.mkv"), ("All", "*.*")])
        if not path:
            return
        self._append(f"You: [Video attached: {os.path.basename(path)}]\n", "user")
        self._send(message="video", video_path=path, mode="video")

    def _attach_weakpoints(self):
        path = filedialog.askopenfilename(
            title="Choose an enemy image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp"),
                       ("All", "*.*")])
        if not path:
            return
        try:
            image = load_image(path)
            self._append(f"You: [Weak point scan: {os.path.basename(path)}]\n", "user")
            self._send(message="weakpoints", image=image, mode="weakpoints")
        except Exception as e:
            self._append(f"[Could not load image: {e}]\n", "system")


if __name__ == "__main__":
    root = tk.Tk()
    app = MultiCharApp(root)
    root.mainloop()