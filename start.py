import subprocess
import sys
import time

bot_process = subprocess.Popen(
    [sys.executable, "-m", "bot.main"]
)

web_process = subprocess.Popen(
    [sys.executable, "-m", "webapp.run"]
)

try:
    while True:
        if bot_process.poll() is not None:
            print("Bot process exited.")
            break

        if web_process.poll() is not None:
            print("Web process exited.")
            break

        time.sleep(1)

except KeyboardInterrupt:
    print("\nStopping HyperAuth...")

finally:
    if bot_process:
        bot_process.terminate()

    if web_process:
        web_process.terminate()
