from django.contrib.auth import authenticate
from django.contrib.auth import login
from django.contrib.auth import logout

from django.shortcuts import render
from django.shortcuts import redirect


def login_view(request):

    if request.user.is_authenticated:
        return redirect('dashboard')

    error = None

    if request.method == 'POST':

        username = request.POST.get('username')

        password = request.POST.get('password')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

            return redirect('dashboard')

        else:

            error = 'Usuario o contraseña incorrectos'

    return render(request, 'users/login.html', {
        'error': error
    })


def logout_view(request):

    logout(request)

    return redirect('login')