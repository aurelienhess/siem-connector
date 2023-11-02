import os
import logging
import logging.handlers


if not os.path.exists(f"{os.getcwd()}/logs"):
    os.makedirs(f"{os.getcwd()}/logs")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# configure the handler and formatter as needed
log_handler = logging.handlers.TimedRotatingFileHandler(
    "./logs/vectra_syslog_connector.log", when="midnight", backupCount=5
)
log_format = logging.Formatter(
    "%(asctime)s: %(levelname)s: (%(filename)s) %(message)s"
)


# add formatter to the handler
log_handler.setFormatter(log_format)
# add handler to the logger
logger.addHandler(log_handler)
