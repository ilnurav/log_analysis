import argparse
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional
import sys
import multiprocessing


class LogAnalyzer:
    """Базовый класс для анализа логов"""

    def __init__(self):
        self.handlers_data = defaultdict(lambda: defaultdict(int))
        self.total_requests = 0

    def process_line(self, line: str) -> None:
        """Обработка одной строки лога"""
        if 'django.request' not in line:
            return

        self.total_requests += 1

        try:
            # Разбираем строку вида: "2025-03-28 12:44:46,000 INFO django.request: GET /api/v1/reviews/ 204 OK [192.168.1.59]"
            parts = line.split()

            # Уровень логирования (INFO, DEBUG, WARNING, ERROR, CRITICAL)
            level = parts[2]

            # Метод и путь запроса (часть после django.request:)
            request_part = line.split('django.request:')[1].strip()
            method_path = request_part.split()[1] if len(request_part.split()) > 1 else ''

            if method_path:
                self.handlers_data[method_path][level] += 1

        except Exception as e:
            print(f"Error processing line: {e} - {line}", file=sys.stderr)

    def process_file(self, file_path: Path) -> Dict:
        """Обработка одного файла логов"""
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                self.process_line(line)
        return {
            'handlers_data': dict(self.handlers_data),
            'total_requests': self.total_requests
        }


class ReportGenerator:
    """Генератор отчетов"""

    @staticmethod
    def generate_handlers_report(results: List[Dict]) -> str:
        """Генерация отчета handlers"""
        # Объединяем данные из всех файлов
        merged_data = defaultdict(lambda: defaultdict(int))
        total_requests = 0

        for result in results:
            total_requests += result['total_requests']
            for handler, levels in result['handlers_data'].items():
                for level, count in levels.items():
                    merged_data[handler][level] += count

        # Определяем все уровни логирования
        levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

        # Подготавливаем данные для вывода
        rows = []
        for handler in sorted(merged_data.keys()):
            row = [handler]
            for level in levels:
                row.append(str(merged_data[handler].get(level, 0)))
            rows.append(row)

        # Подсчитываем итоги по уровням
        totals = [''] + [str(sum(int(row[i]) for row in rows)) for i in range(1, len(levels) + 1)]

        # Форматируем вывод
        header = ["HANDLER"] + levels

        # Вычисляем ширину столбцов
        all_data = rows + [header, totals]
        col_widths = []
        for col_idx in range(len(header)):
            max_width = max(len(str(row[col_idx])) for row in all_data)
            col_widths.append(max_width)

        # Строим строки таблицы
        lines = []
        lines.append(f"Total requests: {total_requests}\n")
        lines.append("".join(f"{h:<{w}} " for h, w in zip(header, col_widths)))

        for row in rows:
            lines.append("".join(f"{col:<{w}} " for col, w in zip(row, col_widths)))

        lines.append("".join(f"{col:<{w}} " for col, w in zip(totals, col_widths)))

        return "\n".join(lines)


def process_single_file(file_path: Path) -> Dict:
    """Обработка одного файла в отдельном процессе"""
    analyzer = LogAnalyzer()
    return analyzer.process_file(file_path)


def main():
    """Точка входа в приложение"""
    parser = argparse.ArgumentParser(description='Анализатор логов Django')
    parser.add_argument('log_files', nargs='+', help='Пути к файлам логов')
    parser.add_argument('--report', required=True, help='Тип отчета (handlers)')

    args = parser.parse_args()

    # Проверка файлов
    for file_path in args.log_files:
        if not Path(file_path).exists():
            print(f"Ошибка: файл {file_path} не существует", file=sys.stderr)
            sys.exit(1)

    # Проверка типа отчета
    if args.report not in ['handlers']:
        print(f"Ошибка: неизвестный тип отчета {args.report}", file=sys.stderr)
        sys.exit(1)

    # Параллельная обработка файлов
    with multiprocessing.Pool() as pool:
        results = pool.map(process_single_file, [Path(f) for f in args.log_files])

    # Генерация отчета
    if args.report == 'handlers':
        report = ReportGenerator.generate_handlers_report(results)
        print(report)


if __name__ == '__main__':
    main()