from django.shortcuts import render

def index(request):
    return render(request, "housing/index.html")

def catalog(request):
    return render(request, "housing/catalog.html")
# Create your views here.
