![OS support](https://img.shields.io/badge/OS-Linux-green) [![Supported Python Versions](https://img.shields.io/pypi/pyversions/textual)](https://pypi.org/project/textual/)
# MD's FanControl - Simple Linux System Monitor & Fan Controller

A terminal user interface (TUI) application for monitoring system resources and controlling PWM fans on Linux systems. Built with [Textual](https://github.com/Textualize/textual) for a modern, responsive interface in the terminal.

## Features

### 📊 System Monitoring
- **CPU Monitoring**: Temperature, power consumption, and usage percentage
- **GPU Monitoring**: Support for both NVIDIA and AMD GPUs
  - Temperature, power, usage, and memory statistics
- **RAM Monitoring**: Memory usage and temperature (when available)
- **Real-time Graphs**: Interactive plotext-based graphs with multiple views per component
<img width="1051" height="863" alt="image" src="https://github.com/user-attachments/assets/1686e6d7-5516-45bd-9de4-1ddf3814ae58" />   

### 🌡️ Fan Control
- **Automatic Fan Detection**: Discovers all PWM-capable fans via hwmon
- **Multiple Control Modes**:
  - **Auto**: Hardware-controlled fan speeds
  - **Manual**: Set custom fan speeds (0-100%)
  - **Graph**: Apply custom fan curves based on system stats
- **Per-Fan Configuration**: Individual control for each detected fan
- **Real-time RPM & Speed Monitoring**
<img width="1451" height="1063" alt="image" src="https://github.com/user-attachments/assets/398c93d4-d08c-4684-8b1c-fdbad9f9d4b4" />  

### 📈 Custom Fan Curves
- **Graph Editor**: Create custom fan curves with unlimited data points
- **Component-Based Curves**: Link fan speed to any monitored stat:
  - CPU Temperature, Power, or Usage
  - GPU Temperature, Power, or Usage
  - RAM Usage or Temperature
- **Interpolation**: Smooth fan speed transitions between curve points
- **Persistent Storage**: Curves saved to `graphs.json`
<img width="1451" height="1063" alt="image" src="https://github.com/user-attachments/assets/b8ab6b48-c2a1-4888-828d-e8102d0bee14" />


### 🔔 Notifications
- **Threshold Alerts**: Desktop notifications when stats exceed limits
- **Multiple Severity Levels**: Info, Warning, Error, Critical
- **Hysteresis**: 10% deadband prevents notification spam
- **D-Bus Integration**: Works with most Linux notification daemons
- **Sudo Support**: Notifications work even when running as root

## Requirements

### System Requirements
- Linux kernel with hwmon support
- PWM-capable fans (check `/sys/class/hwmon/`)
- Python 3.8 or higher
- Desktop environment with notification daemon (optional)

### Python Dependencies
```py
textual>=0.47.0
psutil>=5.9.0
plotext>=5.3.2
rich>=14.2.0
pynvml>=11.5.0  # For NVIDIA GPU support
dbus-python>=1.3.2  # For notifications
```

## Installation
**1. Clone the repository:** 
```git clone <your-repo-url>
cd <project-directory>
```
**1.5. Optional:**
Create a python virtual enviroment
```
python -m venv venvName
source venv/bin/activate
```

## Usage

### Launching the program
```
sudo python tui.py
```
### Shortcuts
**Keyboard Shortcuts**
- s - Switch to System Stats tab
- n - Switch to Notifications tab
- f - Switch to Fan Control tab
- c - Cycle CPU graph view (Temp → Power → Usage)
- g - Cycle GPU graph view (Temp → Power → Usage)
- r - Cycle RAM graph view (Usage → Temperature)
- Ctrl+q - Quit application

### Fan Control Modes
**Auto Mode**\
Lets hardware/BIOS control fan speeds automatically.

**Manual Mode**
1. Select "Manual" from the mode dropdown
2. Enter desired speed (0-100) in the input field
3. Click "Set" to apply

**Graph Mode**
1. Create a fan curve in the "Fan Graphs" tab:
   - Enter graph title
   - Select component stat (e.g., "CPU Temperature")
   - Add coordinate pairs (Stat Value, Fan Speed %)
   - Click "Add Graph"
2. Return to "Fan Control" tab
3. Select "Graph" mode
4. Choose your curve from the dropdown
5. Fan speed will automatically adjust based on the selected stat

**Creating Notifications**
1. Navigate to the "Notifications" tab
2. Fill in the form:
   - Message: Alert text to display
   - Type: Severity level (Info/Warning/Error/Critical)
   - Component: Which stat to monitor
   - Threshold: Value that triggers the notification
3. Click "Create Notification"
4. Click "Save to File" to persist across sessions

## File Structure
```
.
├── tui.py                       # Main application entry point
├── requirements.txt             # Python dependencies
├── layout.tcss                  # Textual CSS styling
├── graphs.json                  # Saved fan curves
├── notifications.json           # Saved notification rules
├── utils/
│   ├── temps_data.py            # System monitoring functions
│   ├── fancontrol.py            # PWM fan control
│   └── notifier.py              # Desktop notification handler
└── widgets/
    ├── monitor_box.py           # System stat display widget
    ├── graphWidget.py           # Plotext graph wrapper
    ├── notification_manager.py  # Notification UI
    ├── fan_widget.py            # Individual fan control
    ├── fan_control_manager.py   # Fan manager container
    └── graphs_page.py           # Fan curve editor
```

## Troubleshooting
**No fans detected**
- Verify PWM support: `ls /sys/class/hwmon/hwmon*/pwm*`
- Check kernel modules: `lsmod | grep -E '(it87|nct6775|w83627ehf)'`
- Some motherboards require BIOS changes to enable fan control

**Notifications not working**
- Ensure notification daemon is running: `ps aux | grep -E '(dunst|mako|notification)'`
- Check logs in terminal for connection errors

**GPU not detected**
- NVIDIA: Install nvidia-sml driver and pynvml package
- AMD: Ensure amdgpu driver is loaded
- Run sensors to verify GPU sensor availability

**Permission errors**
- Fan control requires root: `sudo venv/bin/python tui.py`
- Alternatively, add your user to appropriate groups (varies by distro)

## Configuration Files
`graphs.json`  
Stores fan curve definitions:
```json
{
  "Quiet Curve": {
    "data": [[30.0, 20.0], [70.0, 60.0], [85.0, 100.0]],
    "xlabel": "CPU Temp (°C)",
    "ylabel": "Fan Speed (%)"
  },
  ...
}
```

`notifications.json`  
Stores notification rules:
```json
{
  "notifications": [
    {
      "id": 0,
      "message": "CPU temperature high!",
      "type": "warning",
      "component": "cpu_temp",
      "threshold": 80.0
    },
    ...
  ]
}
```

## Contributing
Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests. :)

## Author
MD20M

## License
This project is under the MIT license.

## Acknowledgments
[Textual](https://github.com/Textualize/textual) - Modern TUI framework for Python  
[plotext](https://github.com/piccolomo/plotext) - Terminal plotting  
[psutil](https://github.com/giampaolo/psutil) - System monitoring
