import os
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Server is running!"

def run():
    # แก้ลูกน้ำเป็นจุด (0.0.0.0) และให้ Render เป็นคนกำหนด Port อัตโนมัติ
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def server_on():
    t = Thread(target=run)
    t.start()