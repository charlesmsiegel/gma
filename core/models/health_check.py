from django.db import models


class HealthCheckLog(models.Model):
    """Simple model to test database migrations and connections."""

    timestamp = models.DateTimeField(auto_now_add=True)
    service = models.CharField(
        max_length=20,
        choices=[
            ("database", "Database"),
            ("redis", "Redis"),
        ],
    )
    status = models.CharField(
        max_length=10,
        choices=[
            ("success", "Success"),
            ("failure", "Failure"),
        ],
    )
    details = models.TextField(blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"{self.service} - {self.status} at {self.timestamp}"
