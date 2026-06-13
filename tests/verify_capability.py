"""验证能力覆盖率"""
from infrastructure.health_dashboard import health_dashboard

aphi = health_dashboard.calculate_aphi()
print(f"能力覆盖率: {aphi['capability_coverage']}%")
print(f"APHI: {aphi['aphi']}")
print(f"模式: {aphi['mode']}")