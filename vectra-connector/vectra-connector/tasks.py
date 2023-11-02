from .celery import app
import os
import psutil
from datetime import datetime, timedelta
from .vectra_api import VectraAPI
from .logger import logger


def check_disk_space():
    try:
        disk_info = psutil.disk_usage("/")
        use_percent = round(disk_info.percent)
        return use_percent
    except Exception as e:
        logger.error(f"Exception in checking disk space {e}")
        return None


@app.task
def get_data_from_audit_api():
    """Celery task for fetch data from audit API.

    Returns:
        dict: Audit Events
    """
    disk_usage_percent = check_disk_space()
    if disk_usage_percent is None:
        return None
    if int(disk_usage_percent) >= 70:
        logger.info(f"Disk usage is {disk_usage_percent} %. Hence, stop pulling Audit API data.")
        return None
    logger.info("Executing Audit API task.")
    logger.info(f"Disk usage {disk_usage_percent} %.")
    URL = f"{str(os.environ.get('BASE_URL')).strip().strip('/')}/api/v3.3/events/audits"
    checkpoint_file_path = "./audit_checkpoint.json"
    params = {}
    if not os.path.exists(checkpoint_file_path):
        current_time = datetime.utcnow()
        # Subtract 24 hours
        new_time = current_time - timedelta(hours=24)
        # Format as "2023-05-31T14:10:00Z"
        formatted_time = new_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        params = {"event_timestamp_gte": formatted_time}
    total_data = VectraAPI.fetch_data_from_api(url=URL, filename="audit", params=params)
    return total_data


@app.task
def get_data_from_entity_api():
    """Celery task for fetch data from entity_scoring API.

    Returns:
        dict: entity_scoring Events
    """
    URL = f"{str(os.environ.get('BASE_URL')).strip().strip('/')}/api/v3.3/events/entity_scoring"
    types = {
        "account": "./entity_account_checkpoint.json",
        "host": "./entity_host_checkpoint.json",
    }
    for typ, checkpoint_path in types.items():
        disk_usage_percent = check_disk_space()
        if disk_usage_percent is None:
            return None
        if int(disk_usage_percent) >= 70:
            logger.info(f"Disk usage is {disk_usage_percent} %. Hence, stop pulling Entity Scoring API data.")
            return None
        logger.info(f"Executing Entity {typ} API task.")
        logger.info(f"Disk usage {disk_usage_percent} %.")
        params = {"type": typ}
        if not os.path.exists(checkpoint_path):
            current_time = datetime.utcnow()
            new_time = current_time - timedelta(hours=24)
            formatted_time = new_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            params.update({"event_timestamp_gte": formatted_time})
        total_data = VectraAPI.fetch_data_from_api(
            url=URL, params=params, filename=f"entity_{typ}"
        )
    return total_data


@app.task
def get_data_from_detection():
    """Celery task for fetch data from detections API.

    Returns:
        dict: Detections Events
    """
    disk_usage_percent = check_disk_space()
    if disk_usage_percent is None:
        return None
    if int(disk_usage_percent) >= 70:
        logger.info(f"Disk usage is {disk_usage_percent} %. Hence, stop pulling Detection API data.")
        return None
    logger.info("Executing Detection API task.")
    logger.info(f"Disk usage {disk_usage_percent} %.")
    URL = f"{str(os.environ.get('BASE_URL')).strip().strip('/')}/api/v3.3/events/detections"
    checkpoint_file_path = "./detection_checkpoint.json"
    params = {}
    if not os.path.exists(checkpoint_file_path):
        current_time = datetime.utcnow()
        new_time = current_time - timedelta(hours=24)
        formatted_time = new_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        params = {"event_timestamp_gte": formatted_time}
    total_data = VectraAPI.fetch_data_from_api(
        url=URL, filename="detection", params=params
    )
    return total_data
