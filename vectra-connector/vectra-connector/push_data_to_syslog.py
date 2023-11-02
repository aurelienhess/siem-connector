import json
import socket
import backoff
import sys
import os
import signal
import logging
import datetime
from .syslog_handler import SSLSysLogHandler
from .celery import app
from .logger import logger
from .validate_config import read_config

# Reading Config file
conf_data = read_config()

logger.info("Reading 'server_status.json' for check server status.")
with open("./server_status.json", "r") as f:
    server_status = json.load(f)


def kill_process_and_exit(e):
    """
    Exit the current execution
    """
    logger.error("Exiting current proccess.")
    os.kill(os.getpid(), signal.SIGTERM)
    sys.exit()


@app.task
@backoff.on_exception(
    backoff.expo,
    socket.error,
    max_tries=conf_data.get("configuration").get("retry_count")
    if conf_data.get("configuration").get("retry_count") in range(0, 11)
    else 10,
    on_giveup=kill_process_and_exit,
)
def push_data_to_syslog(data, server=0):
    """Celery task for push events to configured server."""
    conf_data = read_config()
    server_host = str(
        conf_data.get("configuration").get("server")[server].get("server_host")
    ).strip()
    server_port = int(
        conf_data.get("configuration").get("server")[server].get("server_port")
    )
    server_name = str(conf_data.get("configuration").get("server")[server].get("name"))
    server_protocol = str(
        conf_data.get("configuration").get("server")[server].get("server_protocol")
    ).strip()
    logger.info(f"Push data to '{server_name}' server.")
    syslogger = logging.getLogger()
    syslogger.setLevel(logging.INFO)
    syslogger.handlers = []
    syslogger.propagate = False

    if server_protocol.upper() == "TLS" and server_status.get(server_name):
        try:
            tls_certificate_path = f"./cert/{server_name}.pem"

            # Connect to the TLS server
            logger.info(f"Connecting {server_protocol} server '{server_name}'.")
            tls_handler = SSLSysLogHandler(
                transform_data=data,
                protocol=server_protocol,
                address=(
                    server_host,
                    server_port,
                ),
                certs=tls_certificate_path
            )
            host_name = 'VECTRA-SYSLOG-CONNECTOR'
            time = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            formatter = logging.Formatter(f'{time} ' + f'{host_name}: ' + '%(message)s\n')
            tls_handler.setFormatter(formatter)
            tls_handler.append_nul = False
            syslogger.addHandler(tls_handler)
            logger.info(f"Server '{server_name}' is connected.")
            for data in data['events']:
                syslogger.info(
                        json.dumps(data) if isinstance(data, dict) else data
                    )
                syslogger.handlers[0].flush()
            tls_handler.close()
            logger.info(f"Events pushed to '{server_name}'.")

        except socket.error as e:
            logger.error(f"Connection error: {str(e)}")
            if conf_data.get("configuration").get("retry_count") < 0:
                logger.info("Retry count is less than 0. Retrying continuously.")
                push_data_to_syslog.apply_async(args=[data, server])
            else:
                logger.info("Retrying.")
                raise socket.error from e
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")

    elif server_status.get(server_name):
        # Set UDP socket by default
        socket_type = socket.SOCK_DGRAM
        if server_protocol.upper() == "TCP":
            # Set TCP socket
            socket_type = socket.SOCK_STREAM

        try:
            syslogger = logging.getLogger()
            syslogger.setLevel(logging.INFO)
            syslogger.handlers = []
            syslogger.propagate = False
            handler = SSLSysLogHandler(
                data,
                server_protocol,
                address=(
                    server_host,
                    server_port,
                ),
                socktype=socket_type,
            )
            host_name = 'VECTRA-SYSLOG-CONNECTOR'
            time = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            formatter = logging.Formatter(f'{time} ' + f'{host_name}: ' + '%(message)s\n')
            handler.setFormatter(formatter)
            handler.append_nul = False
            syslogger.addHandler(handler)
            logger.info(f"Server '{server_name}' is connected.")
            for data in data['events']:
                syslogger.info(
                        json.dumps(data) if isinstance(data, dict) else data
                    )
                syslogger.handlers[0].flush()
            handler.close()

            logger.info(f"Events pushed to '{server_name}'.")

        except socket.error as e:
            logger.error(f"Connection error: {str(e)}")
            if conf_data.get("configuration").get("retry_count") < 0:
                logger.info("Retry count is less than 0. Retrying continuously.")
                push_data_to_syslog.apply_async(args=[data, server])
            else:
                logger.info("Retrying.")
                raise socket.error from e
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
