import pytest
from main import LogAnalyzer, ReportGenerator
from pathlib import Path
import tempfile


@pytest.fixture
def sample_log_file():
    """Создаем временный файл с тестовыми логами"""
    log_content = """2025-03-28 12:44:46,000 INFO django.request: GET /api/v1/test/ 204 OK [192.168.1.1]
2025-03-28 12:44:47,000 DEBUG django.request: POST /api/v1/test/ 201 Created [192.168.1.2]
2025-03-28 12:44:48,000 ERROR django.request: GET /api/v1/error/ 500 Error [192.168.1.3]"""

    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
        f.write(log_content)
        f.flush()
        yield Path(f.name)
    Path(f.name).unlink()


def test_log_analyzer_process_line():
    analyzer = LogAnalyzer()
    line = "2025-03-28 12:44:46,000 INFO django.request: GET /api/v1/test/ 204 OK [192.168.1.1]"
    analyzer.process_line(line)
    assert analyzer.total_requests == 1
    assert analyzer.handlers_data['/api/v1/test/']['INFO'] == 1


def test_log_analyzer_process_file(sample_log_file):
    analyzer = LogAnalyzer()
    result = analyzer.process_file(sample_log_file)
    assert result['total_requests'] == 3
    assert result['handlers_data']['/api/v1/test/']['INFO'] == 1
    assert result['handlers_data']['/api/v1/test/']['DEBUG'] == 1
    assert result['handlers_data']['/api/v1/error/']['ERROR'] == 1


def test_report_generation():
    test_data = [
        {
            'total_requests': 3,
            'handlers_data': {
                '/api/v1/test/': {'INFO': 1, 'DEBUG': 1},
                '/api/v1/error/': {'ERROR': 1}
            }
        }
    ]
    report = ReportGenerator.generate_handlers_report(test_data)
    assert "Total requests: 3" in report
    assert "/api/v1/test/" in report
    assert "/api/v1/error/" in report