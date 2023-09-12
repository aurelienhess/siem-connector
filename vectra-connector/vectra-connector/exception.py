class CustomException(Exception):
    "Custom Exception raised while failure occurs."
    pass


class TooManyRequestException(Exception):
    """Custom Exception raised while requests exceeds."""
    pass
