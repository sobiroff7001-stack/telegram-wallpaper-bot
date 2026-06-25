from flask import Flask
from threading import Thread
import os

app = Flask('')

@app.route('/')
def home():
    return "Wallpaper Bot is running!"

def run():
    # Render or other hosts set the PORT environment variable
    port = int(os.environ.get('PORT', 8080))
    # Run Flask server
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
