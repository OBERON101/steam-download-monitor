"""
Steam Download Monitor
Monitors Steam download speed and status by reading Steam logs and registry.
Works independently of Steam installation location.
"""

import os
import re
import time
import winreg
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple


class SteamDownloadMonitor:
    def __init__(self):
        self.steam_path = self._find_steam_path()
        self.log_path = None
        if self.steam_path:
            self.log_path = os.path.join(self.steam_path, 'logs', 'content_log.txt')
        self.last_position = 0
        
    def _find_steam_path(self) -> Optional[str]:
        """
        Find Steam installation path from Windows Registry.
        Checks both 32-bit and 64-bit registry keys.
        """
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
                        print(f"✓ Steam найден: {steam_path}")
                        return steam_path
            except (FileNotFoundError, OSError):
                continue
        
        print("✗ Steam не найден в реестре")
        return None
    
    def _get_app_name(self, app_id: str) -> str:
        """
        Try to get game name from Steam appmanifest files.
        """
        if not self.steam_path:
            return f"AppID {app_id}"
        
        # Check common library folders
        library_folders = [
            os.path.join(self.steam_path, 'steamapps'),
        ]
        
        # Try to read libraryfolders.vdf for additional library locations
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
        
        # Search for appmanifest file
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
    
    def _parse_log_line(self, line: str) -> Optional[Tuple[str, float, str]]:
        """
        Parse Steam log line to extract download information.
        Returns (app_id, speed_mbps, status) or None.
        """
        # Pattern for download progress with speed
        # Example: [2024-01-28 10:30:45] AppID 1234567 update, downloaded 1024.5 MB at 50.2 MB/s
        speed_pattern = r'AppID (\d+).*?(\d+\.?\d*)\s*MB/s'
        match = re.search(speed_pattern, line)
        
        if match:
            app_id = match.group(1)
            speed = float(match.group(2))
            status = "downloading"
            
            # Check if paused
            if 'paused' in line.lower() or 'suspended' in line.lower():
                status = "paused"
            
            return (app_id, speed, status)
        
        # Check for paused state
        if 'paused' in line.lower() or 'suspended' in line.lower():
            app_match = re.search(r'AppID (\d+)', line)
            if app_match:
                return (app_match.group(1), 0.0, "paused")
        
        return None
    
    def _read_new_log_entries(self) -> list:
        """
        Read new entries from Steam log file since last read.
        """
        if not self.log_path or not os.path.exists(self.log_path):
            return []
        
        new_entries = []
        try:
            with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(self.last_position)
                new_entries = f.readlines()
                self.last_position = f.tell()
        except Exception as e:
            print(f"Ошибка чтения лога: {e}")
        
        return new_entries
    
    def get_current_download_status(self) -> Optional[dict]:
        """
        Get current download status by reading Steam logs.
        Returns dict with app_id, game_name, speed, and status.
        """
        entries = self._read_new_log_entries()
        
        # Process entries to find the most recent download info
        latest_info = None
        for line in reversed(entries):  # Start from most recent
            parsed = self._parse_log_line(line)
            if parsed:
                app_id, speed, status = parsed
                game_name = self._get_app_name(app_id)
                latest_info = {
                    'app_id': app_id,
                    'game_name': game_name,
                    'speed_mbps': speed,
                    'status': status,
                    'timestamp': datetime.now()
                }
                break
        
        return latest_info
    
    def monitor(self, duration_minutes: int = 5, interval_seconds: int = 60):
        """
        Monitor Steam downloads for specified duration.
        
        Args:
            duration_minutes: Total monitoring duration in minutes
            interval_seconds: Interval between checks in seconds
        """
        if not self.steam_path:
            print("Ошибка: Steam не найден. Проверьте установку Steam.")
            return
        
        if not os.path.exists(self.log_path):
            print(f"Предупреждение: Лог файл не найден по пути: {self.log_path}")
            print("Ожидание создания лога...")
        
        print("="*70)
        print("МОНИТОРИНГ ЗАГРУЗОК STEAM")
        print("="*70)
        print(f"Путь к Steam: {self.steam_path}")
        print(f"Путь к логам: {self.log_path}")
        print(f"Длительность: {duration_minutes} минут")
        print(f"Интервал проверки: {interval_seconds} секунд")
        print("="*70)
        print()
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        check_count = 0
        last_status = None
        
        while time.time() < end_time:
            check_count += 1
            current_time = datetime.now().strftime("%H:%M:%S")
            
            print(f"\n[{current_time}] Проверка #{check_count}")
            print("-" * 70)
            
            status = self.get_current_download_status()
            
            if status:
                game_name = status['game_name']
                speed = status['speed_mbps']
                download_status = status['status']
                
                if download_status == "downloading":
                    print(f"📥 Игра: {game_name}")
                    print(f"📊 Скорость: {speed:.2f} MB/s ({speed * 8:.2f} Mbps)")
                    print(f"✓ Статус: Загрузка")
                elif download_status == "paused":
                    print(f"⏸️  Игра: {game_name}")
                    print(f"📊 Скорость: 0.00 MB/s")
                    print(f"⏸  Статус: Пауза")
                
                last_status = status
            else:
                if last_status:
                    print(f"ℹ️  Последняя загрузка: {last_status['game_name']}")
                    print(f"📊 Нет активных загрузок")
                else:
                    print("📊 Нет активных загрузок")
                    print("ℹ️  Запустите загрузку игры в Steam для начала мониторинга")
            
            print("-" * 70)
            
            # Wait for next check
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
    """Main entry point for the script."""
    try:
        monitor = SteamDownloadMonitor()
        monitor.monitor(duration_minutes=5, interval_seconds=60)
    except KeyboardInterrupt:
        print("\n\nМониторинг остановлен пользователем.")
    except Exception as e:
        print(f"\nКритическая ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
