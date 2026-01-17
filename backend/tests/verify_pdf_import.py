"""
快速集成测试脚本
"""
import sys

sys.path.insert(0, '.')

from fastapi.testclient import TestClient

from src.main import app


def run_tests():
    client = TestClient(app)

    tests = [
        ('/api/pdf-import/info', 'System Info'),
        ('/api/pdf-import/health', 'Health Check'),
        ('/api/pdf-import/performance/realtime', 'Performance'),
        ('/api/pdf-import/sessions', 'Sessions'),
        ('/api/pdf-import/sessions/history', 'Session History'),
    ]

    print('=' * 60)
    print('PDF Import API - Integration Tests')
    print('=' * 60)

    passed = 0
    failed = 0

    for path, name in tests:
        try:
            response = client.get(path)
            if response.status_code == 200:
                print(f'[PASS] {name}: {response.status_code}')
                passed += 1
            else:
                print(f'[FAIL] {name}: {response.status_code}')
                failed += 1
        except Exception as e:
            print(f'[ERROR] {name}: {e}')
            failed += 1

    print('=' * 60)
    print(f'Results: {passed} passed, {failed} failed')
    print('=' * 60)

    return failed == 0


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
