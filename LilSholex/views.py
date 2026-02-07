from django.http import HttpRequest, HttpResponse


def index(request: HttpRequest) -> HttpResponse:
    return HttpResponse('Up and Running!')
