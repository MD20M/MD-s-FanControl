import psutil
import glob
import subprocess
import os
import time

def get_cpu_info():
    """Get CPU temperature, power consumption, and usage percentage."""
    cpu_temp = psutil.sensors_temperatures().get('coretemp', []) 
    cpu_temps = [t.current for t in cpu_temp] if cpu_temp else []
    cpu_power = None
    rapl_path = '/sys/class/powercap/intel-rapl:0/energy_uj'
    if os.path.exists(rapl_path):
        with open(rapl_path) as f:
            energy1 = int(f.read())
        time.sleep(0.1)  
        with open(rapl_path) as f:
            energy2 = int(f.read())
        
        energy_diff = energy2 - energy1
        if energy_diff < 0: 
            energy_diff += 2**32
        cpu_power = (energy_diff / 1e6) / 0.1 
    
    cpu_usage = psutil.cpu_percent(interval=0.1)
    cpu_usage_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
    
    return {
        'temps': cpu_temps, 
        'power_w': cpu_power,
        'usage_percent': cpu_usage,
        'usage_per_core': cpu_usage_per_core
    }

def get_gpu_info():
    """Get GPU temperature, power consumption, and usage percentage for NVIDIA and AMD GPUs."""
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        gpu_temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        gpu_power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000  # mW to W
        gpu_name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(gpu_name, bytes):
            gpu_name = gpu_name.decode('utf-8')
        
        utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
        gpu_usage = utilization.gpu 
        gpu_memory_usage = utilization.memory
        
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        gpu_memory_used = mem_info.used / (1024**3)  # Convert to GB
        gpu_memory_total = mem_info.total / (1024**3)  # Convert to GB
        
        return {
            'vendor': 'NVIDIA', 
            'model': gpu_name, 
            'temp': gpu_temp, 
            'power_w': gpu_power,
            'usage_percent': gpu_usage,
            'memory_usage_percent': gpu_memory_usage,
            'memory_used_gb': gpu_memory_used,
            'memory_total_gb': gpu_memory_total
        }
    except (ImportError, Exception):
        pass

    # Check for AMD GPU
    amd_paths = glob.glob('/sys/class/drm/card*/device/hwmon/hwmon*/temp*_input')
    if amd_paths:
        try:
            gpu_temp = None
            gpu_power = None
            gpu_name = None
            gpu_usage = None
            
            # Get GPU model name
            card_path = amd_paths[0].split('/hwmon')[0]
            model_files = [
                os.path.join(card_path, 'product_name'),
                os.path.join(card_path, 'model'),
                '/sys/class/drm/card0/device/product_name'
            ]
            for model_file in model_files:
                if os.path.exists(model_file):
                    try:
                        with open(model_file) as f:
                            gpu_name = f.read().strip()
                        if gpu_name:
                            break
                    except (PermissionError, FileNotFoundError):
                        pass
            
            if not gpu_name:
                try:
                    lspci_out = subprocess.getoutput('lspci | grep -i vga')
                    if 'amd' in lspci_out.lower() or 'radeon' in lspci_out.lower():
                        gpu_name = lspci_out.split(': ')[-1].strip()
                except:
                    gpu_name = "AMD GPU"
            
            # Get temperature
            for temp_path in amd_paths:
                label_path = temp_path.replace('_input', '_label')
                if os.path.exists(label_path):
                    with open(label_path) as f:
                        label = f.read().strip().lower()
                    if 'edge' in label or 'junction' in label:
                        with open(temp_path) as f:
                            gpu_temp = int(f.read()) / 1000.0
                        break
                else:
                    with open(temp_path) as f:
                        gpu_temp = int(f.read()) / 1000.0
                    break
            
            # Get power
            hwmon_dir = os.path.dirname(amd_paths[0])
            power_paths = glob.glob(os.path.join(hwmon_dir, 'power*_average'))
            if power_paths:
                with open(power_paths[0]) as f:
                    gpu_power = int(f.read()) / 1e6 
            
            # Get GPU usage (AMD)
            gpu_busy_path = os.path.join(card_path, 'gpu_busy_percent')
            if os.path.exists(gpu_busy_path):
                try:
                    with open(gpu_busy_path) as f:
                        gpu_usage = int(f.read())
                except (PermissionError, FileNotFoundError, ValueError):
                    pass
            
            return {
                'vendor': 'AMD', 
                'model': gpu_name or 'Unknown', 
                'temp': gpu_temp, 
                'power_w': gpu_power,
                'usage_percent': gpu_usage
            }
        except (FileNotFoundError, ValueError, PermissionError):
            pass
    
    return "No GPU detected or install nvidia-ml-py for NVIDIA"

def get_ram_info():
    """Get RAM usage and temperature information."""
    ram = psutil.virtual_memory()
    ram_info = {'used_gb': ram.used / (1024**3), 'total_gb': ram.total / (1024**3)}
    
    ram_temps = []
    
    sensors_out = subprocess.getoutput('sensors')
    lines = sensors_out.split('\n')
    
    in_ram_block = False
    for line in lines:
        line_lower = line.lower()
        
        if any(keyword in line_lower for keyword in ['spd5118', 'dimm', 'dimmtemp']):
            in_ram_block = True
            continue
        
        if line and not line.startswith(' ') and 'adapter' not in line_lower:
            if ':' not in line or line_lower.startswith(('adapter', 'temp', 'fan', 'in', 'curr', 'pwm', 'intrusion', 'beep')):
                in_ram_block = False
        
        if in_ram_block and 'temp' in line_lower and '°c' in line_lower and ':' in line:
            try:
                temp_str = line.split(':')[1].strip().split()[0].replace('+', '')
                ram_temps.append(float(temp_str))
            except (IndexError, ValueError):
                pass
    
    if not ram_temps:
        hwmon_paths = glob.glob('/sys/class/hwmon/hwmon*/name')
        for name_path in hwmon_paths:
            try:
                with open(name_path) as f:
                    name = f.read().strip().lower()
                if 'spd5118' in name or 'dimm' in name:
                    hwmon_dir = os.path.dirname(name_path)
                    temp_inputs = glob.glob(os.path.join(hwmon_dir, 'temp*_input'))
                    for temp_path in temp_inputs:
                        with open(temp_path) as f:
                            temp_millidegrees = int(f.read())
                            ram_temps.append(temp_millidegrees / 1000.0)
            except (FileNotFoundError, ValueError, PermissionError):
                pass
    
    ram_info['temps'] = ram_temps if ram_temps else None
    return ram_info

if __name__ == "__main__":
    ram_info = get_ram_info()
    gpu_info = get_gpu_info()
    
    print("CPU:", get_cpu_info())
    print("GPU:", gpu_info)
    print("RAM:", ram_info)
