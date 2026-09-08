from django import template
from django.templatetags.static import static

register = template.Library()

COVER_COUNT = 12


@register.simple_tag
def cover_url(obj):
\
\
\
\

    image = getattr(obj, 'image', None)
    if image:
        try:
            return image.url
        except ValueError:
            pass
    pk = getattr(obj, 'pk', None) or 0
    return static(f'img/covers/cover-{(pk % COVER_COUNT) + 1:02d}.jpg')


@register.filter
def money(value):
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return value
    return f'{n:,}'.replace(',', ' ')


@register.filter
def plural_ru(n, forms):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return forms.split(',')[-1]
    one, few, many = (forms.split(',') + ['', '', ''])[:3]
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


@register.simple_tag(takes_context=True)
def query_replace(context, **kwargs):
    request = context.get('request')
    params = request.GET.copy() if request else {}
    try:
        params = request.GET.copy()
    except AttributeError:
        from django.http import QueryDict
        params = QueryDict(mutable=True)
    for key, value in kwargs.items():
        if value in (None, ''):
            params.pop(key, None)
        else:
            params[key] = value
    return params.urlencode()
