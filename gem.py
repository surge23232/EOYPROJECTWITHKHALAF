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

model = genai.GenerativeModel(
    model_name="gemini-3-flash-preview",
    system_instruction=kratos_instructions
)

chat = model.start_chat(history=[])

BG_DARK      = "#0a0a0a"
BG_MID       = "#111111"
BG_PANEL     = "#161616"
ACCENT_RED   = "#c0392b"
ACCENT_GOLD  = "#b8860b"
TEXT_LIGHT   = "#e8e0d0"
TEXT_DIM     = "#7a7060"
BORDER       = "#2a2a2a"
USER_COLOR   = "#d4af6a"
KRATOS_COLOR = "#e8e0d0"

GIF_SIZE     = (220, 220)
GIF_PATH     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kratos_thinking.gif")

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

class KratosApp:
    def __init__(self, root):
        self.root = root
        self.root.title("KRATOS — God of War")
        self.root.configure(bg=BG_DARK)
        self.root.geometry("1060x700")
        self.root.minsize(760, 520)
        self.root.resizable(True, True)

        self.gif_frames  = []
        self.gif_index   = 0
        self.gif_job     = None
        self.gif_playing = False
        self.idle_photo  = None

        self._build_fonts()
        self._load_gif()
        self._build_ui()
        self._greet()

    def _build_fonts(self):
        self.font_title = font.Font(family="Georgia", size=18, weight="bold")
        self.font_sub   = font.Font(family="Georgia", size=9,  slant="italic")
        self.font_chat  = font.Font(family="Courier", size=11)
        self.font_btn   = font.Font(family="Georgia", size=10, weight="bold")
        self.font_input = font.Font(family="Courier", size=11)

    def _load_gif(self):
        if not os.path.exists(GIF_PATH):
            print(f"[GIF not found] Expected: {GIF_PATH}")
            return
        try:
            self.gif_frames = load_gif_frames(GIF_PATH, GIF_SIZE)
            self.idle_photo = self.gif_frames[0][0]
        except Exception as e:
            print(f"[GIF load error] {e}")

    def _gif_tick(self):
        if not self.gif_playing or not self.gif_frames:
            return
        photo, delay = self.gif_frames[self.gif_index]
        self.avatar_label.configure(image=photo)
        self.gif_index = (self.gif_index + 1) % len(self.gif_frames)
        self.gif_job = self.root.after(delay, self._gif_tick)

    def _start_gif(self):
        if not self.gif_frames:
            return
        self.gif_playing = True
        self.gif_index   = 0
        self._gif_tick()

    def _stop_gif(self):
        self.gif_playing = False
        if self.gif_job:
            self.root.after_cancel(self.gif_job)
            self.gif_job = None
        if self.idle_photo:
            self.avatar_label.configure(image=self.idle_photo)

    def _build_ui(self):
        tk.Frame(self.root, bg=ACCENT_RED, height=3).pack(fill="x")

        header = tk.Frame(self.root, bg=BG_DARK, pady=8)
        header.pack(fill="x", padx=20)
        title_frame = tk.Frame(header, bg=BG_DARK)
        title_frame.pack()
        tk.Label(title_frame, text="⚔  KRATOS",
                 font=self.font_title, fg=ACCENT_GOLD, bg=BG_DARK).pack(side="left")
        tk.Label(title_frame, text="  GOD OF WAR",
                 font=self.font_sub, fg=TEXT_DIM, bg=BG_DARK).pack(side="left", padx=(6,0))
        tk.Label(self.root, text="Speak. Be judged.",
                 font=self.font_sub, fg=TEXT_DIM, bg=BG_DARK).pack()
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", pady=(6,0))

        body = tk.Frame(self.root, bg=BG_DARK)
        body.pack(fill="both", expand=True, padx=14, pady=10)

        avatar_col = tk.Frame(body, bg=BG_DARK, width=GIF_SIZE[0]+16)
        avatar_col.pack(side="left", fill="y", padx=(0,12))
        avatar_col.pack_propagate(False)

        avatar_border = tk.Frame(avatar_col, bg=ACCENT_RED, padx=2, pady=2)
        avatar_border.pack(pady=(6,0))

        self.avatar_label = tk.Label(
            avatar_border, bg=BG_DARK,
            width=GIF_SIZE[0], height=GIF_SIZE[1],
            text="[ KRATOS ]", fg=TEXT_DIM, font=self.font_sub,
        )
        self.avatar_label.pack()

        if self.idle_photo:
            self.avatar_label.configure(image=self.idle_photo, text="")

        self.status_var = tk.StringVar(value="Waiting...")
        tk.Label(avatar_col, textvariable=self.status_var,
                 font=self.font_sub, fg=TEXT_DIM, bg=BG_DARK).pack(pady=(6,0))

        chat_col = tk.Frame(body, bg=BG_DARK)
        chat_col.pack(side="left", fill="both", expand=True)

        chat_frame = tk.Frame(chat_col, bg=BG_MID, padx=2, pady=2)
        chat_frame.pack(fill="both", expand=True)

        self.chat_box = scrolledtext.ScrolledText(
            chat_frame,
            font=self.font_chat,
            bg=BG_PANEL, fg=TEXT_LIGHT,
            insertbackground=TEXT_LIGHT,
            selectbackground=ACCENT_RED,
            relief="flat", wrap="word",
            state="disabled",
            padx=14, pady=10, spacing3=4,
        )
        self.chat_box.pack(fill="both", expand=True)

        self.chat_box.tag_configure("user",   foreground=USER_COLOR,
                                    font=font.Font(family="Courier", size=11, weight="bold"))
        self.chat_box.tag_configure("kratos", foreground=KRATOS_COLOR, font=self.font_chat)
        self.chat_box.tag_configure("system", foreground=TEXT_DIM,
                                    font=font.Font(family="Georgia", size=10, slant="italic"))
        self.chat_box.tag_configure("header", foreground=ACCENT_GOLD,
                                    font=font.Font(family="Georgia", size=10, weight="bold"))

        btn_row = tk.Frame(self.root, bg=BG_DARK)
        btn_row.pack(fill="x", padx=14, pady=(0,6))
        for label, cmd in [
            ("📎 Image",       self._attach_image),
            ("🎥 Video",       self._attach_video),
            ("🎯 Weak Points", self._attach_weakpoints),
        ]:
            tk.Button(
                btn_row, text=label, command=cmd,
                font=self.font_btn, bg=BG_PANEL, fg=TEXT_DIM,
                activebackground=ACCENT_RED, activeforeground=TEXT_LIGHT,
                relief="flat", bd=0, padx=12, pady=5, cursor="hand2",
            ).pack(side="left", padx=(0,6))

        input_row = tk.Frame(self.root, bg=BG_DARK)
        input_row.pack(fill="x", padx=14, pady=(0,12))

        self.input_var = tk.StringVar()
        entry_border = tk.Frame(input_row, bg=BORDER, bd=1, relief="flat")
        entry_border.pack(side="left", fill="x", expand=True, padx=(0,8))
        self.entry = tk.Entry(
            entry_border, textvariable=self.input_var,
            font=self.font_input, bg=BG_PANEL, fg=TEXT_LIGHT,
            insertbackground=ACCENT_GOLD, selectbackground=ACCENT_RED,
            relief="flat", bd=0,
        )
        self.entry.pack(fill="x", expand=True, ipady=8, padx=8)
        self.entry.bind("<Return>", lambda e: self._send())

        self.send_btn = tk.Button(
            input_row, text="SPEAK", command=self._send,
            font=self.font_btn, bg=ACCENT_RED, fg=TEXT_LIGHT,
            activebackground="#8b1a1a", activeforeground=TEXT_LIGHT,
            relief="flat", bd=0, padx=18, pady=8, cursor="hand2",
        )
        self.send_btn.pack(side="right")

        tk.Frame(self.root, bg=ACCENT_RED, height=3).pack(fill="x", side="bottom")

    def _append(self, text, tag="kratos"):
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", text, tag)
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")

    def _greet(self):
        self._append("⚔  KRATOS SPEAKS\n", "header")
        self._append("I am here, boy. Ask what you must.\n\n", "kratos")

    def _send(self, message=None, image=None, video_path=None, mode="text"):
        text = message or self.input_var.get().strip()
        if not text and mode == "text":
            return
        if mode == "text":
            self._append(f"You: {text}\n", "user")
            self.input_var.set("")
        self.send_btn.configure(state="disabled", text="…")
        self.status_var.set("Thinking...")
        self._start_gif()
        threading.Thread(target=self._call_api,
                         args=(text, image, video_path, mode), daemon=True).start()

    def _call_api(self, text, image, video_path, mode):
        try:
            if mode == "image" and image:
                response = chat.send_message([
                    "Study this image as a warrior. Judge strength and weakness.", image])
            elif mode == "video" and video_path:
                frames = extract_frames(video_path)
                if not frames:
                    self.root.after(0, lambda: self._append(
                        "Kratos: There is nothing to analyze.\n\n", "kratos"))
                    return
                response = chat.send_message([
                    "Analyze this combat. Judge technique, mistakes, aggression, and intent.",
                    *frames])
            elif mode == "weakpoints" and image:
                response = chat.send_message([
                    "Study this enemy as a warrior. Describe weak points and approximate "
                    "location visually (e.g., 'left shoulder', 'center chest').", image])
                draw = ImageDraw.Draw(image)
                w, h = image.size
                for _ in range(3):
                    x, y, r = random.randint(0, w), random.randint(0, h), 14
                    draw.ellipse((x-r, y-r, x+r, y+r), fill=(220, 30, 30, 200))
                save_path = "weakpoints_marked.png"
                image.save(save_path)
                self.root.after(0, lambda: self._append(
                    f"[Weak points marked → saved as '{save_path}']\n", "system"))
            else:
                response = chat.send_message(text)

            reply = response.text
            self.root.after(0, lambda: self._on_response(reply))
        except Exception as e:
            err = str(e)
            self.root.after(0, lambda: self._on_error(err))

    def _on_response(self, reply):
        self._stop_gif()
        self.status_var.set("Waiting...")
        self._append(f"Kratos: {reply}\n\n", "kratos")
        self.send_btn.configure(state="normal", text="SPEAK")

    def _on_error(self, err):
        self._stop_gif()
        self.status_var.set("Waiting...")
        self._append(f"[Error: {err}]\n\n", "system")
        self.send_btn.configure(state="normal", text="SPEAK")

    def _attach_image(self):
        path = filedialog.askopenfilename(
            title="Choose an image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"), ("All", "*.*")])
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
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp"), ("All", "*.*")])
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
    app = KratosApp(root)
    root.mainloop()
