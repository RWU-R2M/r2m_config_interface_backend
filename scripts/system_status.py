#!/usr/bin/env python3
"""
Example script that returns system status information in JSON format.
This script demonstrates a synchronous script that returns JSON output.
"""
import json
import os
import subprocess
import platform

def get_cpu_temperature():
    """Get CPU temperature if possible (Linux only)"""
    try:
        if platform.system() == "Linux":
            # Try to get CPU temperature from thermal zone
            if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
                with open("/sys/class/thermal/thermal_zone0/temp") as f:
                    temp = float(f.read()) / 1000.0
                return round(temp, 1)
            
            # If that didn't work, try using vcgencmd (Raspberry Pi)
            try:
                output = subprocess.check_output(
                    ["vcgencmd", "measure_temp"], 
                    text=True, 
                    stderr=subprocess.DEVNULL
                )
                temp = float(output.split("=")[1].split("'")[0])
                return temp
            except:
                pass
    except:
        pass
    
    # Return a placeholder if we couldn't get real temperature
    return 45.0  # Placeholder value

def get_uptime():
    """Get system uptime"""
    try:
        if platform.system() == "Linux":
            with open("/proc/uptime") as f:
                uptime_seconds = float(f.read().split()[0])
            
            days, remainder = divmod(uptime_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            uptime = f"{int(days)}d {int(hours)}h {int(minutes)}m"
            return uptime
    except:
        pass
    
    return "unknown"  # Fallback if we couldn't get uptime

def main():
    """Main function that returns JSON data"""
    data = {
        "status": "operational",
        "cpu_temp": get_cpu_temperature(),
        "uptime": get_uptime(),
        "hostname": platform.node(),
        "platform": platform.system(),
        "cpu_cores": os.cpu_count()
    }
    
    # Print JSON output to stdout
    print(json.dumps(data))

if __name__ == "__main__":
    main()
