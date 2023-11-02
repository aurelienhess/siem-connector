from celery import Celery
from celery.schedules import crontab
from .validate_config import validate_config_json
from .validate_config import read_config
import os

app = Celery('vectra-connector',
             broker=f"amqp://{str(os.environ.get('rabbitmq_user')).strip()}:{str(os.environ.get('rabbitmq_pass')).strip()}@rabbitmq",
             include=['vectra-connector.tasks', 'vectra-connector.push_data_to_syslog'])

app.config_from_object('vectra-connector.celeryconfig')
app.conf.update(
    result_expires=3600,
)

# Reading config file
conf_data = read_config()
validate_config_json(conf_data)

cron_scheduler_dict = {}
for task, cron_schedule in conf_data.get('configuration').get('scheduler').items():
    fields = cron_schedule.split()
    minute, hour, day_of_month, month_of_year, day_of_week = fields
    cron_scheduler_dict[task] = crontab(
        minute=minute,
        hour=hour,
        day_of_week=day_of_week,
        day_of_month=day_of_month,
        month_of_year=month_of_year
    )
app.conf.beat_schedule = {
    # Executes at every cron scheduler
    'get_data_from_audit_api': {
        'task': 'vectra-connector.tasks.get_data_from_audit_api',
        'schedule': cron_scheduler_dict.get('audit'),
    },
    'get_data_from_entity_api': {
        'task': 'vectra-connector.tasks.get_data_from_entity_api',
        'schedule': cron_scheduler_dict.get('entity_scoring'),
    },
    'get_data_from_detection': {
        'task': 'vectra-connector.tasks.get_data_from_detection',
        'schedule': cron_scheduler_dict.get('detections'),
    },
}

if __name__ == '__main__':
    app.start()
