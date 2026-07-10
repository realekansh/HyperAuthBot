import subprocess
import signal
import sys

bot_process = None
web_process = None

try:
    bot_process = subprocess.Popen(
        [sys.executable, "-m", "bot.main"]
    )

    web_process = subprocess.Popen(
        [sys.executable, "-m", "webapp.run"]
    )

    bot_process.wait()

except KeyboardInterrupt:
    print("\nStopping HyperAuth...")

finally:
    if bot_process:
        bot_process.terminate()

    if web_process:
        web_process.terminate()
