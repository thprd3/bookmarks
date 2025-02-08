import tkinter as tk
from tkinter import messagebox, simpledialog
import sqlite3
import pyperclip  # To copy URLs to clipboard
import requests # HTTP requests
from bs4 import BeautifulSoup # To fetch data from HTML?
import random
from io import BytesIO
from PIL import Image, ImageTk
import urllib.parse

def init_db():
    conn = sqlite3.connect("bookmarks.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            title TEXT,
            tags TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

FAVICON_SIZE = (16, 16)  # Small icons for UI

TAG_COLORS = [
    "#FF9999", "#99FF99", "#9999FF", "#FFCC99", "#CC99FF", "#99FFFF", "#FFFF99", "#FFB3E6",
    "#C2F0C2", "#B3D9FF", "#FF6666", "#66FF66", "#6666FF", "#FF9966", "#9966FF", "#66FFFF",
    "#FFFF66", "#FF80B3", "#A2F0A2", "#80B3FF"
]

ASSIGNED_COLORS = {}  # Dictionary to track used colors

def get_tag_color(tag):
    """Assigns a unique color to each tag. Removes used colors from the pool."""
    global TAG_COLORS
    if tag in ASSIGNED_COLORS:
        return ASSIGNED_COLORS[tag]  # Return the existing color for this tag

    if TAG_COLORS:  # If there are available colors
        color = TAG_COLORS.pop(0)  # Take and remove the first available color
    else:
        color = "#D3D3D3"  # Default gray if colors are exhausted

    ASSIGNED_COLORS[tag] = color  # Save the assigned color
    return color

def get_favicon(url):
    """Fetch the favicon for a given URL."""
    try:
        # Extract domain name from URL
        parsed_url = urllib.parse.urlparse(url)
        domain = f"{parsed_url.scheme}://{parsed_url.netloc}"

        # Construct the favicon URL
        favicon_url = f"{domain}/favicon.ico"

        # Fetch the image
        response = requests.get(favicon_url, timeout=3)
        if response.status_code == 200:
            image = Image.open(BytesIO(response.content))
            image = image.resize(FAVICON_SIZE, Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(image)
    except Exception:
        pass
    return None  # Return None if fetching fails

def fetch_page_title(url):
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()  # Raise error if response is bad
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string.strip() if soup.title else "No Title"
        return title
    except requests.RequestException:
        return "Title Not Found"

def get_bookmarks(tag_filter=""):
    conn = sqlite3.connect("bookmarks.db")
    cursor = conn.cursor()
    if tag_filter:
        cursor.execute("SELECT id, url, title, tags FROM bookmarks WHERE tags LIKE ?", ('%' + tag_filter + '%',))
    else:
        cursor.execute("SELECT id, url, title, tags FROM bookmarks")
    bookmarks = cursor.fetchall()
    conn.close()
    return bookmarks

def add_bookmark():
    """Adds a new bookmark, preventing duplicates."""
    url = simpledialog.askstring("Add Bookmark", "Enter URL:")
    if not url:
        return

    conn = sqlite3.connect("bookmarks.db")
    cursor = conn.cursor()

    # Check if URL already exists
    cursor.execute("SELECT COUNT(*) FROM bookmarks WHERE url = ?", (url,))
    if cursor.fetchone()[0] > 0:
        messagebox.showerror("Duplicate Entry", "This URL already exists in your bookmarks!")
        conn.close()
        return

    tags = simpledialog.askstring("Add Tags", "Enter tags (comma-separated):")
    tags = ",".join([t.strip() for t in tags.split(",")]) if tags else ""

    title = fetch_page_title(url)  # Get the page title

    cursor.execute("INSERT INTO bookmarks (url, title, tags) VALUES (?, ?, ?)", (url, title, tags))
    conn.commit()
    conn.close()

    refresh_list(force_refresh=True)  # Refresh after adding

def delete_bookmark(bookmark_id):
    """Deletes a bookmark and refreshes the list."""
    conn = sqlite3.connect("bookmarks.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
    conn.commit()
    conn.close()

    refresh_list(force_refresh=True)  # Refresh list after deletion

# GUI
def copy_to_clipboard(url):
    pyperclip.copy(url)
    messagebox.showinfo("Copied!", f"Copied to clipboard:\n{url}")

def filter_by_tag(tag):
    """Set the filter entry to the clicked tag and refresh the list."""
    tag_entry.delete(0, tk.END)
    tag_entry.insert(0, tag)
    refresh_list()

def edit_bookmark(bookmark_id):
    """Show options to edit a bookmark (title, tags, or delete)."""
    context_menu = tk.Menu(root, tearoff=0)
    context_menu.add_command(label="Edit Title", command=lambda: edit_bookmark_title(bookmark_id))
    context_menu.add_command(label="Edit Tags", command=lambda: edit_bookmark_tags(bookmark_id))
    context_menu.add_separator()
    context_menu.add_command(label="Delete", command=lambda: delete_bookmark(bookmark_id))
    
    # Show the menu at the mouse position
    context_menu.tk_popup(root.winfo_pointerx(), root.winfo_pointery())

def edit_bookmark_title(bookmark_id):
    """Allow the user to edit the title of a bookmark."""
    new_title = simpledialog.askstring("Edit Title", "Enter new title:")
    if new_title:
        conn = sqlite3.connect("bookmarks.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE bookmarks SET title = ? WHERE id = ?", (new_title, bookmark_id))
        conn.commit()
        conn.close()
        refresh_list()

def edit_bookmark_tags(bookmark_id):
    """Allow the user to edit the tags of a bookmark."""
    conn = sqlite3.connect("bookmarks.db")
    cursor = conn.cursor()
    cursor.execute("SELECT tags FROM bookmarks WHERE id = ?", (bookmark_id,))
    
    row = cursor.fetchone()
    current_tags = row[0] if row and row[0] else ""  # Ensure it's a valid string

    new_tags = simpledialog.askstring("Edit Tags", "Enter new tags (comma-separated):", initialvalue=current_tags)
    if new_tags is not None:
        new_tags = ",".join([t.strip() for t in new_tags.split(",")])  # Clean up spaces
        cursor.execute("UPDATE bookmarks SET tags = ? WHERE id = ?", (new_tags, bookmark_id))
        conn.commit()
    
    conn.close()
    refresh_list()

def refresh_list(force_refresh=False):
    for widget in list_frame.winfo_children():
        widget.destroy()
    
    tag_filter = "" if force_refresh else tag_entry.get()

    conn = sqlite3.connect("bookmarks.db")
    cursor = conn.cursor()

    if tag_filter:
        cursor.execute("SELECT id, url, title, tags FROM bookmarks WHERE tags LIKE ?", ('%' + tag_filter + '%',))
    else:
        cursor.execute("SELECT id, url, title, tags FROM bookmarks")
    
    bookmarks = cursor.fetchall()
    conn.close()

    for bookmark in bookmarks:
        id, url, title, tags = bookmark

        frame = tk.Frame(list_frame)
        frame.pack(fill="x", pady=2)

        row_frame = tk.Frame(frame)
        row_frame.pack(fill="x", padx=5)

        # "Edit" Button at the start
        edit_btn = tk.Button(row_frame, text="✏", command=lambda i=id: edit_bookmark(i))
        edit_btn.pack(side="left", padx=5)

        # Fetch favicon
        favicon_image = get_favicon(url)

        if favicon_image:
            favicon_label = tk.Label(row_frame, image=favicon_image)
            favicon_label.image = favicon_image
            favicon_label.pack(side="left", padx=5)

        # Show the page title
        title_label = tk.Label(row_frame, text=title, font=("Arial", 10, "bold"))
        title_label.pack(side="left", padx=5)

        # URL button
        url_btn = tk.Button(row_frame, text=url, command=lambda u=url: copy_to_clipboard(u), anchor="w")
        url_btn.pack(side="left", fill="x", expand=True, padx=5)

        # Display clickable tags
        if tags:
            tag_list = tags.split(",")
            tag_frame = tk.Frame(row_frame)
            tag_frame.pack(side="left")

            for tag in tag_list:
                tag = tag.strip()
                tag_btn = tk.Button(
                    tag_frame,
                    text=tag,
                    bg=get_tag_color(tag),
                    fg="black",
                    relief="ridge",
                    padx=5,
                    command=lambda t=tag: filter_by_tag(t)
                )
                tag_btn.pack(side="left", padx=3)

        # Delete button
        del_btn = tk.Button(row_frame, text="🗑", command=lambda i=id: delete_bookmark(i))
        del_btn.pack(side="right")

def setup_gui():
    """Initializes and sets up the Tkinter GUI."""
    global root, tag_entry, list_frame

    root = tk.Tk()
    root.title("Bookmark Manager")

    # Top control bar
    top_frame = tk.Frame(root)
    top_frame.pack(pady=5)

    add_button = tk.Button(top_frame, text="➕ Add URL", command=add_bookmark)
    add_button.pack(side="left", padx=5)

    tag_entry = tk.Entry(top_frame, width=20, fg="gray")
    tag_entry.insert(0, "Filter by tag...")
    tag_entry.pack(side="left")

    filter_button = tk.Button(top_frame, text="🔍", command=refresh_list)
    filter_button.pack(side="left", padx=5)

    refresh_button = tk.Button(top_frame, text="🔄 Refresh", command=lambda: refresh_list(True))
    refresh_button.pack(side="left", padx=5)

    list_frame = tk.Frame(root)
    list_frame.pack(fill="both", expand=True)

    refresh_list(force_refresh=True)  # Load all URLs on startup

    root.mainloop()

if __name__ == "__main__":
    setup_gui()  # Initialize the GUI