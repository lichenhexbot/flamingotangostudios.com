import time
import sys
import psutil
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# --- CONFIGURATION ---
TARGET_PROCESS_NAME = "llama"  # Change to "ollama", "python", etc.
CPU_MAX_CEILING = 90.0        # Max CPU percentage allowed before alert
ALERT_DURATION_LIMIT = 5      # Seconds in danger zone before process dump
INTERVAL_MS = 200             # Polling speed (200ms)

# Tracking data for Matplotlib
cpu_history = [0] * 50
time_steps = list(range(50))
danger_timer = 0

# Set up the Matplotlib figure
fig, ax = plt.subplots(figsize=(8, 4))
line, = ax.plot(time_steps, cpu_history, color="#de3a3a", linewidth=2)
ax.axhline(y=CPU_MAX_CEILING, color='yellow', linestyle='--', label="Alert Ceiling")
ax.set_ylim(0, 100)
ax.set_title("LLM Telemetry Background: 'Beta brain wave' / Electrical Load")
ax.set_ylabel("CPU Core Saturation (%)")
ax.set_xlabel("Time (Ticks)")
ax.grid(True, color="#333333", alpha=0.3)

def trigger_warning_beep():
    """Emits an audible warning when the model is working too hard."""
    if sys.platform == "win32":
        import winsound
        winsound.Beep(2000, 150)  # High pitch beep
    else:
        # Linux/Mac terminal bell
        print('\a', end='', flush=True)

def dump_model():
    """Finds and kills the LLM runner to prevent thermal situation."""
    print(f"\n[!!!] ENTROPY CRITICAL: Dumping process '{TARGET_PROCESS_NAME}' immediately!")
    for proc in psutil.process_iter(['pid', 'name']):
        if TARGET_PROCESS_NAME.lower() in proc.info['name'].lower():
            try:
                proc.kill()
                print(f" -> Successfully terminated PID {proc.info['pid']}")
            except Exception as e:
                print(f" -> Failed to kill PID {proc.info['pid']}: {e}")
    plt.close('all')
    sys.exit()

def update_telemetry(frame):
    global danger_timer, cpu_history
    
    # Fetch real-time total CPU utilization
    current_load = psutil.cpu_percent(interval=None)
    
    # Update data array
    cpu_history.append(current_load)
    cpu_history = cpu_history[-50:]
    line.set_ydata(cpu_history)
    
    # Check if we crossed the threshold
    if current_load >= CPU_MAX_CEILING:
        danger_timer += (INTERVAL_MS / 1000)
        trigger_warning_beep()
        # Change plot color to highlight emergency state
        line.set_color('#ff0055')
        print(f"\r⚠️ High Load Detected! Time remaining: {max(0.0, ALERT_DURATION_LIMIT - danger_timer):.1f}s", end="")
    else:
        # Cool down / reset timer if load drops
        danger_timer = max(0.0, danger_timer - (INTERVAL_MS / 1000))
        line.set_color('#3a9ade')
        
    # Act of Defusal: Dump the model if it refuses to drop its usage
    if danger_timer >= ALERT_DURATION_LIMIT:
        dump_model()
        
    return line,

# Run the live visualization
ani = animation.FuncAnimation(fig, update_telemetry, interval=INTERVAL_MS, blit=True)
plt.show()
