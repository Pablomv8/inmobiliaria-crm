from .models import Activity


def log_activity(user, action, description):

    Activity.objects.create(
        user=user,
        action=action,
        description=description
    )