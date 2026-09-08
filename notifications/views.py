from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from housing.views_dashboard import _ctx

from .models import Notification


@login_required
def notification_list(request):
    qs = Notification.objects.filter(user=request.user)
    return render(request, 'notifications/list.html',
                  _ctx(request, 'notifications', items=qs[:50]))


@login_required
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect('notifications')
