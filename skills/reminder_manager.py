import threading
import time

def handle(command):
    if "remind me" in command:
        try:
            # Split by "in" to separate task and time
            if " in " in command:
                parts = command.split(" in ")
                task_part = parts[0].replace("remind me to", "").strip()
                time_part = parts[1].strip()
                
                # Extract minutes from time part
                minutes = 1  # default
                if "minute" in time_part:
                    try:
                        minutes = int(time_part.split()[0])
                    except (ValueError, IndexError):
                        minutes = 1
                
                # Use threading to avoid blocking the main application
                def reminder_thread():
                    time.sleep(minutes * 60)
                    print(f"\nReminder: {task_part}!")
                
                thread = threading.Thread(target=reminder_thread, daemon=True)
                thread.start()
                
                return f"Reminder set! I'll remind you to '{task_part}' in {minutes} minutes."
            else:
                return "Couldn't parse reminder. Use format: 'remind me to [task] in [X] minutes'"
        except Exception as e:
            return f"Couldn't parse reminder: {str(e)}"
    return "Couldn't set reminder. Use format: 'remind me to [task] in [X] minutes'"
