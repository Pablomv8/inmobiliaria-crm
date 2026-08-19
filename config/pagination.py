from django.core.paginator import Paginator


DEFAULT_PAGE_SIZE = 15


def paginate(request, object_list, per_page=DEFAULT_PAGE_SIZE):
    """Return a forgiving page while preserving the filtered queryset."""
    paginator = Paginator(object_list, per_page)
    return paginator.get_page(request.GET.get("page"))
