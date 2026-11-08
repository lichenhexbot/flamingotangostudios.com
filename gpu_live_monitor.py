import csv
import time
from datetime import datetime
import pynvml
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.dates as mdates

# Configuration
LOG_FILE = "gpu_power_log.csv"
INTERVAL_MS = 100  # Update graph every 100ms (0.1 seconds)
MAX_POINTS = 200   # Number of points to display on the live window

# Initialize lists to store live data
timestamps = []
powers = []
peak_consecutive_count = 0  # Safety watchdog counter

# Initialize NVML for NVIDIA GPU tracking
pynvml.nvmlInit()
handle = pynvml.nvmlDeviceGetHandleByIndex(0)

# Prepare the CSV file with headers
with open(LOG_FILE, mode="w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["Timestamp", "Power (Watts)"])

# Setup the live Matplotlib Plot
fig, (ax, ax_bar) = plt.subplots(1, 2, figsize=(12, 5), gridspec_kw={'width_ratios': [5, 1]})
fig.suptitle("GPU Live Power Analyzer & Watchdog", fontsize=14, fontweight='bold')

# Main chart settings
line, = ax.plot([], [], label="Live Power", color="#1f77b4", linewidth=2)
ax.set_xlabel("Time (HH:MM:SS)")
ax.set_ylabel("Power Consumption (Watts)")
ax.grid(True, linestyle="--", alpha=0.6)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))

# Define power range thresholds for your 3090
COLORS = ["#2ca02c", "#ff7f0e", "#d62728", "#7f7f7f"]  # Green, Orange, Red, Grey

# Bar chart setting for mode classification
bar = ax_bar.bar(["Current Mode"], [0], color="green")
ax_bar.set_ylim(0, 400)
ax_bar.set_ylabel("Watts")

def get_mode_string(wattage):
    """Classifies your 3090 behavior based on observed ranges."""
    if wattage <= 35:
        return f"Idle / Baseline (~22W)"
    elif wattage <= 90:
        return f"Low Load / Setup (~60W)"
    elif wattage <= 200:
        return f"Moderate Crunch (~125W)"
    else:
        return f"Peak Generation (~340W)"

def update(frame):
    global timestamps, powers, peak_consecutive_count
    
    # 1. Fetch real-time wattage from NVML
    try:
        current_power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
    except Exception:
        return line, bar
    
    current_time = datetime.now()
    
    # 2. Append to tracking lists
    timestamps.append(current_time)
    powers.append(current_power)
    
    # 3. Stream data to CSV file continuously
    with open(LOG_FILE, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([current_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3], current_power])
        
    # 4. Cap data vectors to keep the window sliding smoothly
    if len(timestamps) > MAX_POINTS:
        timestamps = timestamps[-MAX_POINTS:]
        powers = powers[-MAX_POINTS:]
        
    # 5. Watchdog Protection Safety Mechanism
    # 50 frames at 100ms intervals = 5 consecutive seconds of peak load
    if current_power >= 300.0:
        peak_consecutive_count += 1
        if peak_consecutive_count >= 50:
            print(f"\a⚠️ WARNING: Sustained Peak Power! ({current_power:.1f}W for >5s) Check for stuck token loop.")
    else:
        peak_consecutive_count = 0  # Reset counter immediately if power drops below 300W
        
    # 6. Determine current behavior zone color
    if current_power <= 35:
        current_color = COLORS[0]  # Green
    elif current_power <= 90:
        current_color = COLORS[1]  # Orange
    elif current_power <= 200:
        current_color = COLORS[2]  # Red
    else:
        current_color = COLORS[3]  # Grey (Peak)

    # 7. Dynamic graphical updates
    line.set_data(timestamps, powers)
    bar[0].set_height(current_power)
    bar[0].set_color(current_color)
    
    # Adjust time frame viewport dynamically
    ax.set_xlim(timestamps[0], timestamps[-1])
    ax.set_ylim(0, max(max(powers) + 20, 360))
    
    # Update title with immediate metrics
    mode_text = get_mode_string(current_power)
    ax.set_title(f"Live Draw: {current_power:.1f}W | {mode_text}", color=current_color, fontweight='bold')
    
    # Clean up timestamp overlap layout
    fig.autofmt_xdate()
    
    return line, bar

# Instantiate the live animation engine
ani = animation.FuncAnimation(fig, update, interval=INTERVAL_MS, cache_frame_data=False)

try:
    plt.tight_layout()
    plt.show()
except KeyboardInterrupt:
    print("\nMonitoring closed safely.")
finally:
    try:
        pynvml.nvmlShutdown()
    except Exception:
        pass

