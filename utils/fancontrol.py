import os
import glob
import re

class FanController:
    """
    Class to control and monitor PWM fan devices on Linux systems.
    """
    def __init__(self):
        self.pwm_devices = self._find_pwm_devices()
        self.original_modes = {}
        self._save_original_modes()
        
    def _find_pwm_devices(self):
        """Locate PWM fan control files in /sys/class/hwmon."""
        pwm_files = glob.glob("/sys/class/hwmon/hwmon*/pwm*")
        pwm_devices = [f for f in pwm_files if f.split('/')[-1].startswith('pwm') 
                       and f.split('/')[-1][3:].isdigit()]
        return pwm_devices
    
    def _save_original_modes(self):
        """Save the original control modes to restore later."""
        for pwm_path in self.pwm_devices:
            enable_path = pwm_path + '_enable'
            if os.path.exists(enable_path):
                try:
                    with open(enable_path, 'r') as f:
                        self.original_modes[enable_path] = f.read().strip()
                except IOError:
                    pass
    
    def is_available(self):
        """Check if any PWM devices are available."""
        return len(self.pwm_devices) > 0
    
    def set_manual_mode(self):
        """Set all fans to manual control mode."""
        for pwm_path in self.pwm_devices:
            enable_path = pwm_path + '_enable'
            if os.path.exists(enable_path):
                try:
                    with open(enable_path, 'w') as f:
                        f.write('1')
                except IOError as e:
                    print(f"⚠️  Cannot set manual mode for {pwm_path}: {e}")
    
    def get_supported_modes(self, pwm_path):
        """Check what modes are supported by reading available values"""
        enable_path = pwm_path + '_enable'
        if not os.path.exists(enable_path):
            return []
        
        for possible_file in [enable_path, enable_path.replace('_enable', '_enable_available')]:
            if os.path.exists(possible_file):
                try:
                    with open(possible_file, 'r') as f:
                        content = f.read().strip()
                        return content
                except IOError:
                    pass
        return None
    
    def set_auto_mode(self):
        """Set all fans to automatic control mode (might not work on all systems!)."""
        success_count = 0
        for pwm_path in self.pwm_devices:
            enable_path = pwm_path + '_enable'
            if os.path.exists(enable_path):
                for auto_value in ['2', '3', '5']:
                    try:
                        with open(enable_path, 'w') as f:
                            f.write(auto_value)
                        print(f"✓ Set {pwm_path} to automatic mode (value={auto_value})")
                        success_count += 1
                        break
                    except IOError as e:
                        if auto_value == '5':  # Last attempt
                            print(f"⚠️  Cannot set auto mode for {pwm_path}: Hardware may not support automatic control")
                            print(f"    Supported modes info: {self.get_supported_modes(pwm_path)}")
        
        if success_count == 0:
            print("\n⚠️  WARNING: Your hardware doesn't support automatic fan control.")
            print("    You'll need to control fans manually or rely on BIOS/UEFI settings.")
        
        return success_count > 0
    
    def restore_auto_mode(self):
        """Restore original control modes for all fans."""
        for enable_path, original_value in self.original_modes.items():
            try:
                with open(enable_path, 'w') as f:
                    f.write(original_value)
            except IOError:
                pass
    
    def set_speed(self, pwm_path, percentage):
        """Set fan speed for a specific PWM device"""
        percentage = max(0, min(100, percentage))
        
        pwm_value = int((percentage / 100) * 255)
        
        try:
            with open(pwm_path, 'w') as f:
                f.write(str(pwm_value))
            return True
        except IOError as e:
            print(f"⚠️  Cannot set fan speed for {pwm_path}: {e}")
            return False
    
    def set_speed_all(self, percentage):
        """Set speed for all PWM devices"""
        if not self.is_available():
            return False
        
        success = True
        for pwm_path in self.pwm_devices:
            if not self.set_speed(pwm_path, percentage):
                success = False
        
        return success
    
    def get_speed(self, pwm_path):
        """Get current fan speed percentage for a specific PWM device"""
        try:
            with open(pwm_path, 'r') as f:
                pwm_value = int(f.read().strip())
                percentage = (pwm_value / 255) * 100
                return round(percentage, 1)
        except (IOError, ValueError):
            return None
    
    def get_all_speeds(self):
        """Get current fan speeds for all PWM devices"""
        speeds = {}
        for pwm_path in self.pwm_devices:
            speed = self.get_speed(pwm_path)
            if speed is not None:
                fan_name = os.path.basename(pwm_path)
                speeds[fan_name] = speed
        return speeds
    
    def emergency_max_speed(self):
        """Set all fans to maximum speed (255) (this feature is depricated and not used in the project)"""
        print("🚨 EMERGENCY: Setting all fans to maximum speed!")
        for pwm_path in self.pwm_devices:
            try:
                with open(pwm_path, 'w') as f:
                    f.write('255')
            except IOError:
                pass
    
    def _get_fan_label(self, pwm_path):
        """Get the label/name of the fan from the kernel"""
        pwm_match = re.search(r'pwm(\d+)$', pwm_path)
        if not pwm_match:
            return None
        
        pwm_num = pwm_match.group(1)
        hwmon_dir = os.path.dirname(pwm_path)
        
        label_path = os.path.join(hwmon_dir, f'pwm{pwm_num}_label')
        if os.path.exists(label_path):
            try:
                with open(label_path, 'r') as f:
                    return f.read().strip()
            except IOError:
                pass
        
        fan_label_path = os.path.join(hwmon_dir, f'fan{pwm_num}_label')
        if os.path.exists(fan_label_path):
            try:
                with open(fan_label_path, 'r') as f:
                    return f.read().strip()
            except IOError:
                pass
        
        return None
    
    def _get_fan_rpm(self, pwm_path):
        """Get current RPM of the fan"""
        pwm_match = re.search(r'pwm(\d+)$', pwm_path)
        if not pwm_match:
            return None
        
        pwm_num = pwm_match.group(1)
        hwmon_dir = os.path.dirname(pwm_path)
        
        fan_input_path = os.path.join(hwmon_dir, f'fan{pwm_num}_input')
        if os.path.exists(fan_input_path):
            try:
                with open(fan_input_path, 'r') as f:
                    return int(f.read().strip())
            except (IOError, ValueError):
                pass
        
        return None
    
    def _get_hwmon_name(self, pwm_path):
        """Get the hardware monitor chip name"""
        hwmon_dir = os.path.dirname(pwm_path)
        name_path = os.path.join(hwmon_dir, 'name')
        
        if os.path.exists(name_path):
            try:
                with open(name_path, 'r') as f:
                    return f.read().strip()
            except IOError:
                pass
        
        return None
    
    def print_fan_info(self):
        """Print detailed fan information"""
        info = self.get_info()
        
        if not info['available']:
            print("No PWM devices found")
            return
        
        print("\n=== Fan Information ===")
        for device in info['devices']:
            label = device['label'] or 'Unknown'
            print(f"\n{device['name']} - {label}")
            print(f"  Path: {device['path']}")
            print(f"  Chip: {device['hwmon_chip']}")
            print(f"  Speed: {device['current_speed']}%")
            print(f"  RPM: {device['current_rpm']}")
            print(f"  Mode: {device.get('mode', 'unknown')}")
    
    def get_info(self):
        """Get detailed fan information as a dictionary."""
        info = {
            'available': self.is_available(),
            'devices': []
        }
        
        for pwm_path in self.pwm_devices:
            device_info = {
                'path': pwm_path,
                'name': os.path.basename(pwm_path),
                'label': self._get_fan_label(pwm_path),
                'hwmon_chip': self._get_hwmon_name(pwm_path),
                'current_speed': self.get_speed(pwm_path),
                'current_rpm': self._get_fan_rpm(pwm_path)
            }

            if (device_info["label"] == None):
                continue
            
            enable_path = pwm_path + '_enable'
            if os.path.exists(enable_path):
                try:
                    with open(enable_path, 'r') as f:
                        mode = f.read().strip()
                        device_info['mode'] = {
                            '0': 'disabled',
                            '1': 'manual',
                            '2': 'automatic',
                            '3': 'automatic_fan_speed_cruise',
                        }.get(mode, f'unknown({mode})')
                except IOError:
                    device_info['mode'] = 'unknown'
            
            info['devices'].append(device_info)
        
        return info
    
    def set_mode(self, pwm_path, mode):
        """
        Set control mode for a specific fan.
        
        Args:
            pwm_path: Path to the PWM device (e.g., '/sys/class/hwmon/hwmon7/pwm1')
            mode: 'auto' or 'manual'
        
        Returns:
            True if successful, False otherwise
        """
        enable_path = pwm_path + '_enable'
        if not os.path.exists(enable_path):
            return False
        
        if mode == 'manual':
            try:
                with open(enable_path, 'w') as f:
                    f.write('1')
                return True
            except IOError as e:
                print(f"⚠️  Cannot set manual mode for {pwm_path}: {e}")
                return False
        
        elif mode == 'auto':
            for auto_value in ['2', '3', '5']:
                try:
                    with open(enable_path, 'w') as f:
                        f.write(auto_value)
                    return True
                except IOError:
                    if auto_value == '5': 
                        print(f"⚠️  Cannot set auto mode for {pwm_path}")
                        return False
            return False
        
        else:
            print(f"⚠️  Unknown mode: {mode}")
            return False
