"""
Steam Download Monitor (Alternative Method)
Monitors Steam downloads by reading download scheduling and cache files.
This method is more reliable as it reads Steam's internal state files.
"""

import os
import re
import time
import winreg
import struct
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List


class SteamDownloadMonitorV2:
    def __init__(self):
        self.steam_path = self._find_steam_path()
        self.download_stats = []
        
    def _find_steam_path(self) -> Optional[str]:
        """Find Steam installation path from Windows Registry."""
        registry_paths = [
            (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam"),
        ]
        
        for hkey, subkey in registry_paths:
            try:
                with winreg.OpenKey(hkey, subkey) as key:
                    steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
                    if steam_path and os.path.exists(steam_path):
                        return steam_path
            except (FileNotFoundError, OSError):
                continue
        return None
    
    def _get_app_name(self, app_id: str) -> str:
        """Get game name from appmanifest files."""
        if not self.steam_path:
            return f"AppID {app_id}"
        
        library_folders = [os.path.join(self.steam_path, 'steamapps')]
        
        # Read libraryfolders.vdf
        library_vdf = os.path.join(self.steam_path, 'steamapps', 'libraryfolders.vdf')
        if os.path.exists(library_vdf):
            try:
                with open(library_vdf, 'r', encoding='utf-8') as f:
                    content = f.read()
                    paths = re.findall(r'"path"\s+"([^"]+)"', content)
                    for path in paths:
                        lib_path = os.path.join(path.replace('\\\\', '\\'), 'steamapps')
                        if os.path.exists(lib_path):
                            library_folders.append(lib_path)
            except Exception:
                pass
        
        for folder in library_folders:
            manifest_file = os.path.join(folder, f'appmanifest_{app_id}.acf')
            if os.path.exists(manifest_file):
                try:
                    with open(manifest_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        match = re.search(r'"name"\s+"([^"]+)"', content)
                        if match:
                            return match.group(1)
                except Exception:
                    pass
        
        return f"AppID {app_id}"
    
    def _read_steam_process_stats(self) -> Optional[Dict]:
        """
        Read download statistics from Steam process memory or status files.
        This is a placeholder for reading actual Steam download stats.
        """
        # Check download state file
        download_state_file = os.path.join(self.steam_path, 'appcache', 'appinfo.vdf')
        
        if not os.path.exists(download_state_file):
            return None
        
        # In real implementation, parse VDF format
        # For now, return mock data structure
        return None
    
    def _get_downloading_apps(self) -> List[str]:
        """
        Get list of currently downloading apps by checking .downloading files.
        """
        if not self.steam_path:
            return []
        
        downloading_apps = []
        steamapps_folders = [os.path.join(self.steam_path, 'steamapps')]
        
        # Check for library folders
        library_vdf = os.path.join(self.steam_path, 'steamapps', 'libraryfolders.vdf')
        if os.path.exists(library_vdf):
            try:
                with open(library_vdf, 'r', encoding='utf-8') as f:
                    content = f.read()
                    paths = re.findall(r'"path"\s+"([^"]+)"', content)
                    for path in paths:
                        lib_path = os.path.join(path.replace('\\\\', '\\'), 'steamapps')
                        if os.path.exists(lib_path):
                            steamapps_folders.append(lib_path)
            except Exception:
                pass
        
        # Look for downloading indicators
        for folder in steamapps_folders:
            if not os.path.exists(folder):
                continue
            
            # Check for .downloading files or temp files
            for file in os.listdir(folder):
                if file.startswith('appmanifest_') and file.endswith('.acf'):
                    app_id = file.replace('appmanifest_', '').replace('.acf', '')
                    manifest_path = os.path.join(folder, file)
                    
                    # Check if downloading folder exists
                    downloading_folder = os.path.join(folder, 'downloading', app_id)
                    if os.path.exists(downloading_folder):
                        downloading_apps.append(app_id)
                    
                    # Check manifest for download state
                    try:
                        with open(manifest_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if 'StateFlags' in content:
                                # StateFlags "4" usually means downloading
                                state_match = re.search(r'"StateFlags"\s+"(\d+)"', content)
                                if state_match and state_match.group(1) in ['2', '4', '6']:
                                    if app_id not in downloading_apps:
                                        downloading_apps.append(app_id)
                    except Exception:
                        pass
        
        return downloading_apps
    
    def _estimate_download_speed(self, app_id: str, folder: str) -> float:
        """
        Estimate download speed by monitoring file size changes.
        Returns speed in MB/s.
        """
        downloading_folder = os.path.join(folder, 'downloading', app_id)
        if not os.path.exists(downloading_folder):
            return 0.0
        
        try:
            # Get total size of files in downloading folder
            total_size = 0
            for root, dirs, files in os.walk(downloading_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
            
            # Store current size for speed calculation
            current_time = time.time()
            if app_id in self.download_stats:
                last_size, last_time = self.download_stats[app_id]
                time_diff = current_time - last_time
                if time_diff > 0:
                    size_diff = total_size - last_size
                    speed_bytes_per_sec = size_diff / time_diff
                    speed_mb_per_sec = speed_bytes_per_sec / (1024 * 1024)
                    self.download_stats[app_id] = (total_size, current_time)
                    return max(0, speed_mb_per_sec)
            
            self.download_stats[app_id] = (total_size, current_time)
            return 0.0
            
        except Exception:
            return 0.0
    
    def get_download_info(self) -> List[Dict]:
        """Get information about all current downloads."""
        if not self.steam_path:
            return []
        
        downloads = []
        downloading_apps = self._get_downloading_apps()
        
        for app_id in downloading_apps:
            game_name = self._get_app_name(app_id)
            
            # Try to find the library folder for this app
            steamapps_folder = os.path.join(self.steam_path, 'steamapps')
            speed = self._estimate_download_speed(app_id, steamapps_folder)
            
            # Check if paused by looking at recent file modifications
            downloading_folder = os.path.join(steamapps_folder, 'downloading', app_id)
            is_active = False
            if os.path.exists(downloading_folder):
                # Check if any files were modified in the last 2 minutes
                try:
                    latest_mtime = 0
                    for root, dirs, files in os.walk(downloading_folder):
                        for file in files:
                            file_path = os.path.join(root, file)
                            if os.path.exists(file_path):
                                mtime = os.path.getmtime(file_path)
                                latest_mtime = max(latest_mtime, mtime)
                    
                    if time.time() - latest_mtime < 120:  # Modified in last 2 minutes
                        is_active = True
                except Exception:
                    pass
            
            status = "downloading" if is_active else "paused"
            
            downloads.append({
                'app_id': app_id,
                'game_name': game_name,
                'speed_mbps': speed if is_active else 0.0,
                'status': status
            })
        
        return downloads
    
    def monitor(self, duration_minutes: int = 5, interval_seconds: int = 60):
        """Monitor Steam downloads for specified duration."""
        if not self.steam_path:
            print("Ошибка: Steam не найден. Проверьте установку Steam.")
            return
        
        print("="*70)
        print("МОНИТОРИНГ ЗАГРУЗОК STEAM (Версия 2)")
        print("="*70)
        print(f"Путь к Steam: {self.steam_path}")
        print(f"Длительность: {duration_minutes} минут")
        print(f"Интервал проверки: {interval_seconds} секунд")
        print("="*70)
        print()
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        check_count = 0
        
        while time.time() < end_time:
            check_count += 1
            current_time = datetime.now().strftime("%H:%M:%S")
            
            print(f"\n[{current_time}] Проверка #{check_count}")
            print("-" * 70)
            
            downloads = self.get_download_info()
            
            if downloads:
                for dl in downloads:
                    game_name = dl['game_name']
                    speed = dl['speed_mbps']
                    status = dl['status']
                    
                    if status == "downloading":
                        print(f"📥 Игра: {game_name}")
                        print(f"📊 Скорость: {speed:.2f} MB/s ({speed * 8:.2f} Mbps)")
                        print(f"✓ Статус: Загрузка")
                    else:
                        print(f"⏸️  Игра: {game_name}")
                        print(f"📊 Скорость: 0.00 MB/s")
                        print(f"⏸  Статус: Пауза")
                    print()
            else:
                print("📊 Нет активных загрузок")
                print("ℹ️  Запустите загрузку игры в Steam для начала мониторинга")
            
            print("-" * 70)
            
            remaining_time = end_time - time.time()
            if remaining_time > interval_seconds:
                time.sleep(interval_seconds)
            elif remaining_time > 0:
                time.sleep(remaining_time)
            else:
                break
        
        print("\n" + "="*70)
        print("МОНИТОРИНГ ЗАВЕРШЕН")
        print("="*70)


def main():
    """Main entry point."""
    try:
        monitor = SteamDownloadMonitorV2()
        monitor.monitor(duration_minutes=5, interval_seconds=60)
    except KeyboardInterrupt:
        print("\n\nМониторинг остановлен пользователем.")
    except Exception as e:
        print(f"\nКритическая ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
