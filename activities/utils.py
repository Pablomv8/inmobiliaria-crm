from .models import Activity


def log_activity(user, action, description, contact = None, task = None):

    Activity.objects.create(
        user=user,
        action=action,
        description=description,
        contact = contact,
        task = task
    )