#!/usr/bin/env python3
"""
Echo Platform - One-Click Server Starter
"""
import subprocess
import threading
import time
import sys
import os

def start_servers():
    print("="*60)
    print("🚀 ECHO SCHOOL PLATFORM")
    print("="*60)
    
    # Kill any existing ngrok
    print("🛑 Cleaning up old processes...")
    os.system('taskkill /f /im ngrok.exe 2>nul')
    time.sleep(1)
    
    # Start Flask
    print("\n📦 Starting Flask server...")
    flask_env = os.environ.copy()
    flask_env.update({'FLASK_APP': 'app.py', 'FLASK_ENV': 'development'})
    
    flask = subprocess.Popen(
        ['flask', 'run'],
        env=flask_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Read Flask output
    def read_flask():
        for line in iter(flask.stdout.readline, ''):
            if "Running on" in line:
                print(f"✅ {line.strip()}")
    
    threading.Thread(target=read_flask, daemon=True).start()
    time.sleep(3)
    
    # Start ngrok
    print("🌐 Starting ngrok tunnel...")
    ngrok = subprocess.Popen(
        ['C:/Users/USER/Desktop/ngrok.exe', 'http', '5000', '--pooling-enabled'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Read ngrok output
    def read_ngrok():
        url_printed = False
        for line in iter(ngrok.stdout.readline, ''):
            if 'Forwarding' in line and 'ngrok-free.dev' in line:
                if not url_printed:
                    # Extract URL
                    parts = line.strip().split()
                    for part in parts:
                        if 'ngrok-free.dev' in part:
                            print(f"\n🎉 PUBLIC URL: {part}")
                            print("="*60)
                            url_printed = True
                            break
    
    threading.Thread(target=read_ngrok, daemon=True).start()
    
    print("\n⏳ Waiting for ngrok URL (5-10 seconds)...")
    time.sleep(8)
    
    print("\n" + "="*60)
    print("📊 SERVER READY!")
    print("="*60)
    print("📍 Local:  http://localhost:5000")
    print("🌐 Public: https://archegonial-untenderly-barney.ngrok-free.dev")
    print("\n📢 Share this URL with Trecks!")
    print("\n🎯 Test with:")
    print("   curl https://archegonial-untenderly-barney.ngrok-free.dev/api/schools")
    print("\n🛑 Press Ctrl+C to stop both servers")
    print("="*60)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping servers...")
    finally:
        flask.terminate()
        ngrok.terminate()
        print("✅ Servers stopped")

if __name__ == "__main__":
    start_servers()