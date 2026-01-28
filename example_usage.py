"""
Пример использования Steam Download Monitor
Демонстрирует базовые возможности скрипта
"""

from steam_download_monitor import SteamDownloadMonitor

def example_basic_usage():
    """Базовый пример: мониторинг на 5 минут"""
    print("=== Пример 1: Базовое использование ===\n")
    
    monitor = SteamDownloadMonitor()
    
    # Проверяем, что Steam найден
    if not monitor.steam_path:
        print("Steam не найден на этом компьютере!")
        return
    
    print(f"Steam найден: {monitor.steam_path}\n")
    
    # Запускаем мониторинг на 5 минут
    monitor.monitor(duration_minutes=5, interval_seconds=60)


def example_quick_check():
    """Пример: быстрая проверка текущего статуса"""
    print("=== Пример 2: Быстрая проверка ===\n")
    
    monitor = SteamDownloadMonitor()
    
    if not monitor.steam_path:
        print("Steam не найден!")
        return
    
    # Получаем текущий статус загрузки
    status = monitor.get_current_download_status()
    
    if status:
        print(f"Игра: {status['game_name']}")
        print(f"Скорость: {status['speed_mbps']:.2f} MB/s")
        print(f"Статус: {status['status']}")
    else:
        print("Нет активных загрузок")


def example_custom_duration():
    """Пример: настраиваемая длительность мониторинга"""
    print("=== Пример 3: Мониторинг 10 минут с проверкой каждые 30 секунд ===\n")
    
    monitor = SteamDownloadMonitor()
    
    if not monitor.steam_path:
        print("Steam не найден!")
        return
    
    # Мониторинг 10 минут, проверка каждые 30 секунд
    monitor.monitor(duration_minutes=10, interval_seconds=30)


if __name__ == "__main__":
    print("ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ STEAM DOWNLOAD MONITOR")
    print("=" * 70)
    print()
    
    # Выберите пример для запуска:
    
    # 1. Базовое использование (5 минут, проверка каждую минуту)
    example_basic_usage()
    
    # 2. Быстрая однократная проверка
    # example_quick_check()
    
    # 3. Настраиваемая длительность
    # example_custom_duration()
