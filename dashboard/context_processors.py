from .alerts import build_alerts, summarize_alerts


def alert_center(request):
    if not request.user.is_authenticated:
        return {"global_alert_summary": {"total": 0, "high": 0}}
    alerts = getattr(request, "_crm_alerts", None)
    if alerts is None:
        alerts = build_alerts(request.user)
        request._crm_alerts = alerts
    summary = summarize_alerts(alerts)
    return {"global_alert_summary": summary}
