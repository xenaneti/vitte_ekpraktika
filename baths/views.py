import hashlib

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import InquiryForm, MessageForm, PublicationForm, RegisterForm
from .models import Bath, Inquiry, Publication, Service

PUBLIC_PAGES = [
    "home",
    "about",
    "baths",
    "services",
    "journal",
    "news",
    "contacts",
    "sitemap",
]


def published():
    return Publication.objects.filter(
        is_published=True, published_at__lte=timezone.localdate()
    )


def limited(request, action, maximum=10):
    address = request.META.get("REMOTE_ADDR", "unknown")
    identity = str(request.user.pk) if request.user.is_authenticated else address
    digest = hashlib.sha256((action + identity).encode()).hexdigest()
    key = "limit:" + digest
    if cache.add(key, 1, timeout=300):
        return False
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=300)
        count = 1
    return count > maximum


def home(request):
    return render(
        request,
        "home.html",
        {
            "baths": Bath.objects.filter(
                slug__in=["russian-bath", "finnish-sauna", "small-sauna"]
            ),
            "news": published().filter(category="news")[:3],
            "title": "Баня и сауна в Москве — Тихий пар",
            "description": "Отдельные бани и сауны для компаний до 10 человек. Выберите помещение, посмотрите цены и оставьте заявку на посещение комплекса «Тихий пар».",
        },
    )


def about(request):
    return render(
        request,
        "about.html",
        {
            "title": "О комплексе и правила посещения — Тихий пар",
            "description": "Как устроен банный комплекс «Тихий пар»: отдельные помещения, часы работы, условия аренды и ответы на вопросы перед посещением.",
        },
    )


def bath_list(request):
    return render(
        request,
        "baths.html",
        {
            "baths": Bath.objects.all(),
            "title": "Бани и сауны: помещения и вместимость — Тихий пар",
            "description": "Пять вариантов бань и саун: фотографии, вместимость, состав помещений и цена за час. Аренда отдельного зала от двух часов.",
        },
    )


def services(request):
    return render(
        request,
        "services.html",
        {
            "services": Service.objects.all(),
            "baths": Bath.objects.all(),
            "title": "Услуги и цены на посещение — Тихий пар",
            "description": "Стоимость аренды бань, парения, проката полотенец, веников и чая. Полный список услуг учебного комплекса «Тихий пар».",
        },
    )


def publication_list(request, is_news):
    articles = list(published())
    if is_news:
        articles = [item for item in articles if item.category == "news"]
    else:
        articles = [item for item in articles if item.category != "news"]
        articles.sort(key=lambda item: item.category != "visit")
    for item in articles:
        item.related_articles = [
            other
            for other in articles
            if other.pk != item.pk and other.category == item.category
        ][:2]
    return render(
        request,
        "publications.html",
        {
            "articles": articles,
            "is_news": is_news,
            "title": (
                "Новости и предложения — Тихий пар"
                if is_news
                else "Журнал о банях и подготовке к посещению — Тихий пар"
            ),
            "description": (
                "Новости комплекса, изменения в расписании и предложения для гостей."
                if is_news
                else "Что взять с собой, как выбрать помещение и рассчитать стоимость посещения. Практические статьи для гостей банного комплекса."
            ),
        },
    )


def journal(request):
    return publication_list(request, False)


def news(request):
    return publication_list(request, True)


def contacts(request):
    initial = {}
    if request.user.is_authenticated:
        initial = {
            "name": request.user.first_name or request.user.username,
            "email": request.user.email,
        }
    bath_slug = request.GET.get("bath", "")
    bath = Bath.objects.filter(slug=bath_slug).first()
    if bath:
        initial.update({"bath": bath, "subject": "Заявка: " + bath.name})
    form = InquiryForm(
        request.POST if request.method == "POST" else None, initial=initial
    )
    if request.method == "POST":
        if limited(request, "inquiry", 5):
            form.add_error(
                None, "Слишком много обращений. Попробуйте через пять минут."
            )
        elif form.is_valid():
            inquiry = form.save(commit=False)
            if request.user.is_authenticated:
                inquiry.user = request.user
            inquiry.save()
            messages.success(
                request,
                f"Обращение № {inquiry.pk} сохранено. Администратор подтвердит время отдельно.",
            )
            if inquiry.user:
                return redirect(reverse("account") + f"?thread={inquiry.pk}")
            return redirect(reverse("contacts") + "#contact-form")
    return render(
        request,
        "contacts.html",
        {
            "form": form,
            "title": "Контакты и заявка на посещение — Тихий пар",
            "description": "Часы работы и контакты комплекса «Тихий пар». Отправьте вопрос или заявку с выбором помещения и желаемого времени посещения.",
        },
    )


def selected_inquiry(request, queryset):
    value = request.GET.get("thread", "")
    if not value:
        return None
    if not value.isdecimal():
        raise Http404
    return get_object_or_404(queryset, pk=value)


def account(request):
    register_form = RegisterForm(prefix="register")
    login_form = AuthenticationForm(request)
    mode = request.GET.get("mode", "login")
    if not request.user.is_authenticated and request.method == "POST":
        mode = request.POST.get("action", "login")
        if mode == "register":
            register_form = RegisterForm(request.POST, prefix="register")
            if limited(request, "register", 5):
                register_form.add_error(
                    None, "Попробуйте зарегистрироваться через пять минут."
                )
            elif register_form.is_valid():
                user = register_form.save()
                login(request, user)
                messages.success(request, "Учётная запись создана.")
                return redirect("account")
        else:
            login_form = AuthenticationForm(request, data=request.POST)
            if limited(request, "login", 10):
                login_form.add_error(
                    None, "Слишком много попыток входа. Подождите пять минут."
                )
            elif login_form.is_valid():
                login(request, login_form.get_user())
                return redirect("account")
    inquiries = Inquiry.objects.none()
    current = None
    if request.user.is_authenticated:
        inquiries = (
            Inquiry.objects.filter(user=request.user)
            .select_related("bath")
            .prefetch_related("replies__author")
        )
        current = selected_inquiry(request, inquiries)
    return render(
        request,
        "account.html",
        {
            "register_form": register_form,
            "login_form": login_form,
            "mode": mode,
            "inquiries": inquiries,
            "current": current,
            "reply_form": MessageForm(),
            "title": "Личный кабинет — Тихий пар",
            "noindex": True,
        },
    )


@require_POST
def sign_out(request):
    logout(request)
    return redirect("home")


@login_required
@require_POST
def reply(request, pk):
    inquiries = (
        Inquiry.objects.all()
        if request.user.is_staff
        else Inquiry.objects.filter(user=request.user)
    )
    inquiry = get_object_or_404(inquiries, pk=pk)
    form = MessageForm(request.POST)
    destination = "staff" if request.user.is_staff else "account"
    if inquiry.status == "closed":
        messages.error(request, "Обращение закрыто. Создайте новое обращение.")
    elif limited(request, "reply", 20):
        messages.error(request, "Слишком много сообщений. Подождите пять минут.")
    elif form.is_valid():
        message = form.save(commit=False)
        message.inquiry = inquiry
        message.author = request.user
        message.save()
        if request.user.is_staff and inquiry.status == "new":
            inquiry.status = "active"
            inquiry.save(update_fields=["status"])
        messages.success(request, "Сообщение сохранено.")
    else:
        messages.error(request, "Сообщение должно содержать от 1 до 3000 символов.")
    return redirect(reverse(destination) + f"?thread={inquiry.pk}#conversation")


@login_required
def staff(request):
    if not request.user.is_staff:
        raise PermissionDenied
    edit_id = request.GET.get("edit", "")
    editing = None
    if edit_id:
        if not edit_id.isdecimal():
            raise Http404
        editing = get_object_or_404(Publication, pk=edit_id)
    publication_form = PublicationForm(instance=editing)
    user_form = RegisterForm(prefix="newuser")
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "publication":
            publication_form = PublicationForm(request.POST, instance=editing)
            if publication_form.is_valid():
                publication_form.save()
                messages.success(request, "Публикация сохранена.")
                return redirect(reverse("staff") + "#publications")
        elif action == "user":
            user_form = RegisterForm(request.POST, prefix="newuser")
            if user_form.is_valid():
                user_form.save()
                messages.success(request, "Пользователь создан.")
                return redirect(reverse("staff") + "#users")
        elif action == "status":
            value = request.POST.get("inquiry_id", "")
            if not value.isdecimal():
                raise Http404
            inquiry = get_object_or_404(Inquiry, pk=value)
            status = request.POST.get("status")
            if status in dict(Inquiry.STATUSES):
                inquiry.status = status
                inquiry.save(update_fields=["status"])
                messages.success(request, "Статус изменён.")
            return redirect(reverse("staff") + f"?thread={inquiry.pk}")
        elif action == "access":
            value = request.POST.get("user_id", "")
            if not value.isdecimal():
                raise Http404
            user = get_object_or_404(User, pk=value)
            if user.pk == request.user.pk:
                messages.error(request, "Нельзя изменить свои права в этой форме.")
            else:
                role = request.POST.get("role")
                if role in ["client", "admin", "inactive"]:
                    user.is_staff = role == "admin"
                    user.is_active = role != "inactive"
                    user.save(update_fields=["is_staff", "is_active"])
                    messages.success(request, "Права пользователя изменены.")
            return redirect(reverse("staff") + "#users")
    inquiries = Inquiry.objects.select_related("bath", "user").prefetch_related(
        "replies__author"
    )
    return render(
        request,
        "staff.html",
        {
            "inquiries": inquiries,
            "current": selected_inquiry(request, inquiries),
            "reply_form": MessageForm(),
            "statuses": Inquiry.STATUSES,
            "publication_form": publication_form,
            "editing": editing,
            "publications": Publication.objects.all(),
            "users": User.objects.order_by("username"),
            "user_form": user_form,
            "title": "Управление сайтом — Тихий пар",
            "noindex": True,
        },
    )


def search(request):
    query = request.GET.get("q", "").strip()[:120]
    results = []
    if query:
        words = query.casefold().split()
        for item in Bath.objects.all():
            text = (item.name + " " + item.description + " " + item.features).casefold()
            if all(word in text for word in words):
                results.append(
                    {
                        "title": item.name,
                        "text": item.description,
                        "url": item.get_absolute_url(),
                        "category": "Бани и сауны",
                    }
                )
        for item in Service.objects.all():
            text = (item.name + " " + item.description).casefold()
            if all(word in text for word in words):
                results.append(
                    {
                        "title": item.name,
                        "text": item.description,
                        "url": item.get_absolute_url(),
                        "category": "Услуги",
                    }
                )
        for item in published():
            text = (item.title + " " + item.summary + " " + item.body).casefold()
            if all(word in text for word in words):
                results.append(
                    {
                        "title": item.title,
                        "text": item.summary,
                        "url": item.get_absolute_url(),
                        "category": item.get_category_display(),
                    }
                )
    return render(
        request,
        "search.html",
        {
            "query": query,
            "results": results,
            "title": "Поиск по сайту — Тихий пар",
            "noindex": True,
        },
    )


def sitemap(request):
    return render(
        request,
        "sitemap.html",
        {
            "title": "Карта сайта — Тихий пар",
            "description": "Все разделы сайта банного комплекса: помещения, услуги, журнал, новости, контакты и личный кабинет.",
        },
    )


def sitemap_xml(request):
    urls = [settings.SITE_URL + reverse(name) for name in PUBLIC_PAGES]
    return render(
        request, "sitemap.xml", {"urls": urls}, content_type="application/xml"
    )


def robots(request):
    content = (
        "User-agent: *\nDisallow: /account/\nDisallow: /staff/\nDisallow: /inquiries/\nDisallow: /search/\nDisallow: /logout/\nSitemap: "
        + settings.SITE_URL
        + "/sitemap.xml\n"
    )
    return HttpResponse(content, content_type="text/plain")


def not_found(request, exception=None):
    return render(
        request,
        "error.html",
        {
            "code": 404,
            "heading": "Такой страницы нет",
            "explanation": "Проверьте адрес или вернитесь на главную.",
            "title": "Страница не найдена — Тихий пар",
            "noindex": True,
        },
        status=404,
    )


def forbidden(request, exception):
    return render(
        request,
        "error.html",
        {
            "code": 403,
            "heading": "Нет доступа",
            "explanation": "Эта страница доступна администратору.",
            "title": "Нет доступа — Тихий пар",
            "noindex": True,
        },
        status=403,
    )


def csrf_error(request, reason=""):
    return render(
        request,
        "error.html",
        {
            "code": 403,
            "heading": "Обновите страницу",
            "explanation": "Срок действия формы истёк. Откройте страницу заново и повторите отправку.",
            "title": "Повторите отправку — Тихий пар",
            "noindex": True,
        },
        status=403,
    )
