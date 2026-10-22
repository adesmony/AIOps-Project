import structlog


class SafeTelemetry:
    def __init__(self, connection_string: str | None) -> None:
        self._enabled = False
        self._logger = structlog.get_logger("telemetry")
        if not connection_string:
            return
        try:
            from azure.monitor.opentelemetry import configure_azure_monitor

            configure_azure_monitor(connection_string=connection_string)
            self._enabled = True
        except Exception as error:
            self._logger.warning("telemetry_configuration_failed", error_type=type(error).__name__)

    def event(self, name: str, properties: dict[str, str] | None = None) -> None:
        try:
            self._logger.info(name, **(properties or {}), telemetry_enabled=self._enabled)
        except Exception:
            return

    def exception(self, error: Exception, properties: dict[str, str] | None = None) -> None:
        try:
            self._logger.error(
                "operation_failed",
                error_type=type(error).__name__,
                **(properties or {}),
                telemetry_enabled=self._enabled,
            )
        except Exception:
            return
