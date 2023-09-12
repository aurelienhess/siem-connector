import json
import os
from .logger import logger


class Checkpoint:
    """Checkpoint class for event collection."""

    def __init__(self) -> None:
        """Initialization function"""
        pass

    def read_checkpoint_from_file(file_name):
        """Read saved checkpoint from file to start collection.

        Args:
            file_name (str): Checkpoint file name

        Returns:
            int: Checkpoint value
        """
        checkpoint_file_path = f"./{file_name}_checkpoint.json"
        next_checkpoint = 0

        if not os.path.exists(checkpoint_file_path):
            return 0
        try:
            logger.info(f"Read checkpoint from '{file_name}'.")
            with open(checkpoint_file_path, "r") as f:
                data = f.read()
            data = json.loads(data)
            next_checkpoint = data.get(f"{file_name}_next_checkpoint")
            return next_checkpoint
        except FileNotFoundError:
            logger.error(
                f"Checkpoint file for '{file_name}' was not found or file is empty."
            )
            logger.info(f"Starting collection from last 24 hours for '{file_name}'.")
            return -1
        except ValueError:
            logger.error(
                f"Checkpoint file for '{file_name}' is corrupted or not in correct json format."
            )
            logger.info(f"Creating new file for '{file_name}'.")
            os.remove(checkpoint_file_path)
            return -1
        except Exception as e:
            logger.error(f"Error while reading checkpoint: {e}")

    def save_checkpoint_to_file(checkpoint, file_name):
        """Save checkpoint after collection.

        Args:
            checkpoint (dict): Checkpoint value
            file_name (str): Checkpoint file
        """
        try:
            logger.info(f"Saving checkpoint in '{file_name}'.")
            with open(f"./{file_name}_checkpoint.json", "w") as f:
                f.write(json.dumps(checkpoint))
            logger.info(f"Checkpoint saved for '{file_name}'. {checkpoint}")
        except Exception as e:
            logger.error(f"Error saving checkpoint. {e}")
