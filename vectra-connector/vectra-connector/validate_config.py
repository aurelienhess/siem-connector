import jsonschema
import json
import sys
import socket
import ssl
from .logger import logger

# Config schema
configSchema = {
    "definitions": {
        "scheduler_properties": {
            "type": "string",
            "pattern": r"^(?:(?:(\*|\d{1,2}|\d{1,2}-\d{1,2}|\d{1,2}\/\d{1,2}|\d{1,2},\d{1,2}|\?|\*\/\d{1,2})\s+){4}"
            r"(\*|\d{1,2}|\d{1,2}-\d{1,2}|\d{1,2}\/\d{1,2}|\d{1,2},\d{1,2}|\?|\*\/\d{1,2}))$",
            "error_msg": "Please provide valid cron expression.",
        }
    },
    "type": "object",
    "properties": {
        "configuration": {
            "type": "object",
            "properties": {
                "server": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "minLength": 1,
                                "pattern": r"^[a-zA-Z0-9_.-]*$",
                                "error_msg": "Name should be minimum 1 character.",
                            },
                            "server_protocol": {
                                "type": "string",
                                "enum": ["TCP", "UDP", "TLS", "tcp", "udp", "tls"],
                                "error_msg": "Please provide valid server_protocol. "
                                "Should be one of ['TCP', 'UDP', 'TLS']",
                            },
                            "server_host": {
                                "type": "string",
                                "pattern": r"^(https?:\/\/)?(?:(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
                                r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|^([0-9a-fA-F]){1,4}"
                                r"(:([0-9a-fA-F]){1,4}){7}$|(?:[a-zA-Z0-9][a-zA-Z0-9\-]*\.)+[a-zA-Z]{2,6})$",
                                "error_msg": "Please provide valid Host or IP.",
                            },
                            "server_port": {
                                "type": "number",
                                "minimum": 1,
                                "maximum": 65535,
                                "error_msg": "Please provide valid integer Port Number. Should be in range 1 to 65535",
                            },
                        },
                        "required": [
                            "name",
                            "server_protocol",
                            "server_host",
                            "server_port",
                        ],
                    },
                },
                "scheduler": {
                    "type": "object",
                    "properties": {
                        "audit": {"$ref": "#/definitions/scheduler_properties"},
                        "detections": {"$ref": "#/definitions/scheduler_properties"},
                        "entity_scoring": {
                            "$ref": "#/definitions/scheduler_properties"
                        },
                    },
                    "required": ["audit", "detections", "entity_scoring"],
                },
                "retry_count": {
                    "type": "number",
                    "error_msg": "Please provide number not string.",
                },
            },
            "required": ["server", "scheduler", "retry_count"],
        }
    },
    "required": ["configuration"],
}


def read_config():
    try:
        logger.info("Reading 'conf.json'.")
        with open("./config.json", "r") as f:
            conf_data = json.load(f)
        return conf_data
    except FileNotFoundError as e:
        logger.error(f"File 'config.json' not found: {e}")
        sys.exit()
    except ValueError:
        logger.error("File 'config.json' is corrupted or not in correct json format.")
        sys.exit()
    except Exception as e:
        logger.error(f"Error while reading 'config.json': {e}")
        sys.exit()


def validate_config_json(jsonData):
    """Function for validating config.json file.

    Args:
        jsonData (dict): Read config data from config.json
    """
    try:
        logger.info("Validating Config JSON")
        jsonschema.validate(instance=jsonData, schema=configSchema)
        test_connectivity_syslog(jsonData)
        logger.info("Config validation is successful.")
    except jsonschema.exceptions.ValidationError:
        validator = jsonschema.Draft7Validator(schema=configSchema)
        errors = validator.iter_errors(jsonData)
        for err in errors:
            error_message = (
                err.schema["error_msg"] if "error_msg" in err.schema else err.message
            )
            logger.error(f"Config validation failed. ERROR: {error_message}")
        sys.exit()


def test_connectivity_syslog(json_data):
    """Test configured server is reachable or not.

    Args:
        json_data (dict): Read config data from config.json
    """
    server_status = {}
    for server in range(len(json_data.get("configuration").get("server"))):
        server_host = str(
            json_data.get("configuration").get("server")[server].get("server_host")
        ).strip()
        server_port = int(
            json_data.get("configuration").get("server")[server].get("server_port")
        )
        server_name = str(
            json_data.get("configuration").get("server")[server].get("name")
        ).strip()
        server_protocol = str(
            json_data.get("configuration").get("server")[server].get("server_protocol")
        ).strip()
        logger.info(f"Testing connectivity for server '{server_name}'")
        status = True
        if server_protocol.upper() == "TLS":
            try:
                tls_certificate_path = f"./cert/{server_name}.pem"

                tls_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                tls_socket.settimeout(60)
                tls_wrap_sock = ssl.wrap_socket(
                    tls_socket,
                    ca_certs=tls_certificate_path,
                    cert_reqs=ssl.CERT_REQUIRED,
                )

                # Connect to the TLS server
                logger.info(f"Connecting {server_protocol} server '{server_name}'")
                tls_wrap_sock.connect((server_host, server_port))
                logger.info(f"Server '{server_name}' is connected.")
                tls_wrap_sock.close()

            except socket.error as e:
                logger.error(f"Connection error: {str(e)}")
                status = False
            except Exception as e:
                logger.error(f"An error occurred: {str(e)}")
                status = False
                sys.exit()
            finally:
                server_status.update({f"{server_name}": status})

        else:
            # Set UDP socket by default
            socket_type = socket.SOCK_DGRAM
            if server_protocol.upper() == "TCP":
                # Set TCP socket
                socket_type = socket.SOCK_STREAM
            try:
                server_socket = socket.socket(socket.AF_INET, socket_type)
                server_socket.settimeout(60)

                logger.info(f"Connecting {server_protocol} server '{server_name}'")
                server_socket.connect((server_host, server_port))
                logger.info(f"Server '{server_name}' is connected.")
                server_socket.close()

            except socket.error as e:
                logger.error(f"Connection error: {str(e)}")
                status = False
            except Exception as e:
                logger.error(f"An error occurred: {str(e)}")
                status = False
                sys.exit()
            finally:
                server_status.update({f"{server_name}": status})
    with open("./server_status.json", "w") as file:
        file.write(json.dumps(server_status))
    if len(json_data.get("configuration").get("server")) == 1 and not status:
        sys.exit()
