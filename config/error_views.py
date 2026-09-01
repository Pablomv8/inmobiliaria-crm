from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import get_template


def bad_request(request, exception=None):
    return render(request, "errors/400.html", status=400)


def permission_denied(request, exception=None):
    return render(request, "errors/403.html", status=403)


def page_not_found(request, exception=None):
    return render(request, "errors/404.html", status=404)


def server_error(request):
    content = get_template("errors/500.html").render(
        {"request_id": getattr(request, "request_id", "")}
    )
    return HttpResponse(content, status=500)
