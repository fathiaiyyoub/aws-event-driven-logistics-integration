class PartnerConfigurationError(RuntimeError):
    """Raised when partner operational configuration is missing or malformed."""


class UnsupportedDeliveryMethodError(PartnerConfigurationError):
    """Raised when no delivery handler is registered for a configured method."""


class DeliveryError(RuntimeError):
    """Raised when a configured outbound delivery cannot be completed."""


class ResponseMessageError(RuntimeError):
    """Raised when an SQS response message does not match the contract."""
