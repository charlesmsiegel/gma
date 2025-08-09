from django.db import models


class HealthCheckLog(models.Model):
    """Simple model to test database migrations and connections."""

    timestamp = models.DateTimeField(auto_now_add=True)  # type: ignore[var-annotated]
    service = models.CharField(  # type: ignore[var-annotated]
        max_length=20,
        choices=[
            ("database", "Database"),
            ("redis", "Redis"),
        ],
    )
    status = models.CharField(  # type: ignore[var-annotated]
        max_length=10,
        choices=[
            ("success", "Success"),
            ("failure", "Failure"),
        ],
    )
    details = models.TextField(blank=True)  # type: ignore[var-annotated]

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"{self.service} - {self.status} at {self.timestamp}"
