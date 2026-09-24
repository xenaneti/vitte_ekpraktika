from django.urls import path, re_path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("baths/", views.bath_list, name="baths"),
    path("services/", views.services, name="services"),
    path("journal/", views.journal, name="journal"),
    path("news/", views.news, name="news"),
    path("contacts/", views.contacts, name="contacts"),
    path("account/", views.account, name="account"),
    path("logout/", views.sign_out, name="logout"),
    path("inquiries/<int:pk>/reply/", views.reply, name="reply"),
    path("staff/", views.staff, name="staff"),
    path("search/", views.search, name="search"),
    path("sitemap/", views.sitemap, name="sitemap"),
    path("sitemap.xml", views.sitemap_xml, name="sitemap_xml"),
    path("robots.txt", views.robots, name="robots"),
    re_path(r"^.*$", views.not_found),
]
