import json
import socket
import backoff
import ssl
import sys
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
    if server_protocol.upper() == "TLS" and server_status.get(server_name):
        try:
            tls_certificate_path = f"./cert/{server_name}.pem"

            # Connect to the TLS server
            logger.info(f"Connecting {server_protocol} server '{server_name}'.")

            for data in data["events"]:
                tls_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                tls_socket.settimeout(60)
                tls_wrap_sock = ssl.wrap_socket(
                    tls_socket,
                    ca_certs=tls_certificate_path,
                    cert_reqs=ssl.CERT_REQUIRED,
                )
                tls_wrap_sock.connect((server_host, server_port))

                json_data = json.dumps(data).encode()
                # Send the JSON data to the TLS server
                tls_wrap_sock.sendall(json_data)
                tls_wrap_sock.send(b"\n")
                tls_wrap_sock.close()

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
            # Connect to the server
            server_socket = socket.socket(socket.AF_INET, socket_type)
            server_socket.settimeout(60)

            logger.info(f"Connecting {server_protocol} server '{server_name}'.")
            server_socket.connect((server_host, server_port))

            logger.info(f"Server '{server_name}' is connected.")
            for data in data["events"]:
                json_data = json.dumps(data).encode()
                # Send the JSON data to the server
                server_socket.sendall(json_data)
                server_socket.send(b"\n")

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
