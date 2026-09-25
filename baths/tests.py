from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from .models import Bath, Inquiry, Message, Publication, Service


class SiteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)
        cls.visitor = User.objects.create_user(
            "tester", "tester@example.com", "TestPassword2026!", first_name="Иван"
        )
        cls.other = User.objects.create_user(
            "another", "another@example.com", "TestPassword2026!"
        )
        cls.admin = User.objects.create_user(
            "manager", "manager@example.com", "TestPassword2026!", is_staff=True
        )
        cls.inquiry = Inquiry.objects.create(
            user=cls.visitor,
            name="Иван",
            email="tester@example.com",
            subject="Вопрос о бане",
            text="Можно взять свои полотенца?",
        )

    def setUp(self):
        cache.clear()

    def inquiry_data(self):
        return {
            "name": "Гость",
            "email": "guest@example.com",
            "subject": "Вопрос",
            "text": "Есть ли свободное помещение?",
            "consent": "on",
        }

    def test_public_pages(self):
        pages = [
            "/",
            "/about/",
            "/baths/",
            "/services/",
            "/journal/",
            "/news/",
            "/contacts/",
            "/account/",
            "/search/",
            "/sitemap/",
        ]
        titles = []
        for path in pages:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, '<html lang="ru">')
                self.assertEqual(response.content.count(b"<h1"), 1)
                titles.append(response.context["title"])
        self.assertEqual(len(titles), len(set(titles)))

    def test_seed_is_repeatable_and_preserves_edits(self):
        bath = Bath.objects.first()
        bath.price = 9999
        bath.save()
        call_command("seed_demo", verbosity=0)
        self.assertEqual(Bath.objects.count(), 5)
        self.assertEqual(Service.objects.count(), 5)
        self.assertEqual(Publication.objects.count(), 15)
        bath.refresh_from_db()
        self.assertEqual(bath.price, 9999)
        for category in ["visit", "baths", "news"]:
            self.assertEqual(Publication.objects.filter(category=category).count(), 5)

    def test_search_russian_case_and_private_data(self):
        self.assertContains(
            self.client.get("/search/", {"q": "САУНА"}), "Камерная сауна"
        )
        self.assertContains(
            self.client.get("/search/", {"q": "несуществующее-слово-999"}),
            "Ничего не найдено",
        )
        self.assertContains(self.client.get("/search/"), "Введите название")
        response = self.client.get("/search/", {"q": self.inquiry.text})
        self.assertEqual(len(response.context["results"]), 0)

    def test_unpublished_and_future_articles_are_hidden(self):
        article = Publication.objects.first()
        article.title = "скрытыйматериал999"
        article.is_published = False
        article.save()
        self.assertNotContains(self.client.get("/news/"), article.title)
        self.assertEqual(
            len(self.client.get("/search/", {"q": article.title}).context["results"]), 0
        )
        article.is_published = True
        article.published_at = timezone.localdate() + timedelta(days=2)
        article.save()
        self.assertEqual(
            len(self.client.get("/search/", {"q": article.title}).context["results"]), 0
        )

    def test_guest_inquiry_saved_without_account_attachment(self):
        data = self.inquiry_data()
        data["email"] = self.visitor.email
        response = self.client.post("/contacts/", data)
        self.assertEqual(response.status_code, 302)
        inquiry = Inquiry.objects.latest("id")
        self.assertIsNone(inquiry.user)
        self.client.force_login(self.visitor)
        self.assertEqual(
            self.client.get("/account/", {"thread": inquiry.pk}).status_code, 404
        )

    def test_invalid_inquiry_not_saved(self):
        before = Inquiry.objects.count()
        data = self.inquiry_data()
        data["email"] = "wrong"
        data.pop("consent")
        response = self.client.post("/contacts/", data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)
        self.assertIn("consent", response.context["form"].errors)
        self.assertEqual(Inquiry.objects.count(), before)

    def test_booking_date_and_hours(self):
        data = self.inquiry_data()
        data["bath"] = Bath.objects.first().pk
        tomorrow = timezone.localdate() + timedelta(days=1)
        for value in ["", "2020-01-01T12:00", f"{tomorrow}T20:30", f"{tomorrow}T08:00"]:
            with self.subTest(value=value):
                data["visit_at"] = value
                response = self.client.post("/contacts/", data)
                self.assertIn("visit_at", response.context["form"].errors)
        cache.clear()
        data["visit_at"] = f"{tomorrow}T20:00"
        self.assertEqual(self.client.post("/contacts/", data).status_code, 302)

    def test_empty_post_does_not_crash(self):
        for unused in range(7):
            self.assertEqual(self.client.post("/contacts/", {}).status_code, 200)

    def test_registration_login_logout(self):
        data = {
            "action": "register",
            "register-first_name": "Анна",
            "register-username": "anna",
            "register-email": "anna@example.com",
            "register-password1": "NewPassword2026!",
            "register-password2": "NewPassword2026!",
            "is_staff": "on",
        }
        response = self.client.post("/account/", data)
        self.assertRedirects(response, "/account/")
        user = User.objects.get(username="anna")
        self.assertFalse(user.is_staff)
        self.assertTrue(user.check_password("NewPassword2026!"))
        self.assertNotEqual(user.password, "NewPassword2026!")
        self.assertEqual(self.client.get("/logout/").status_code, 405)
        self.client.post("/logout/")
        self.assertNotIn("_auth_user_id", self.client.session)
        self.client.post(
            "/account/",
            {"action": "login", "username": "anna", "password": "NewPassword2026!"},
        )
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_duplicate_email_and_weak_password(self):
        response = self.client.post(
            "/account/",
            {
                "action": "register",
                "register-first_name": "Иван",
                "register-username": "newname",
                "register-email": "TESTER@EXAMPLE.COM",
                "register-password1": "123",
                "register-password2": "123",
            },
        )
        self.assertIn("email", response.context["register_form"].errors)
        self.assertIn("password2", response.context["register_form"].errors)
        self.assertFalse(User.objects.filter(username="newname").exists())

    def test_wrong_login_and_rate_limit(self):
        for unused in range(11):
            response = self.client.post(
                "/account/", {"username": "tester", "password": "wrong"}
            )
        self.assertContains(response, "Слишком много попыток входа")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_visitor_cannot_access_staff(self):
        self.assertEqual(self.client.get("/staff/").status_code, 302)
        self.client.force_login(self.visitor)
        self.assertEqual(self.client.get("/staff/").status_code, 403)
        self.assertEqual(
            self.client.post(
                "/staff/",
                {"action": "access", "user_id": self.visitor.pk, "role": "admin"},
            ).status_code,
            403,
        )
        self.visitor.refresh_from_db()
        self.assertFalse(self.visitor.is_staff)

    def test_other_user_cannot_read_or_reply(self):
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get("/account/", {"thread": self.inquiry.pk}).status_code, 404
        )
        self.assertEqual(
            self.client.post(
                f"/inquiries/{self.inquiry.pk}/reply/", {"text": "чужое сообщение"}
            ).status_code,
            404,
        )
        self.assertEqual(Message.objects.count(), 0)

    def test_correspondence_and_closing(self):
        self.client.force_login(self.visitor)
        self.assertEqual(
            self.client.post(
                f"/inquiries/{self.inquiry.pk}/reply/", {"text": "Нужно два комплекта."}
            ).status_code,
            302,
        )
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/staff/").status_code, 200)
        self.client.post(
            f"/inquiries/{self.inquiry.pk}/reply/",
            {"text": "Подготовим два комплекта."},
        )
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.status, "active")
        self.client.post(
            "/staff/",
            {"action": "status", "inquiry_id": self.inquiry.pk, "status": "closed"},
        )
        self.client.force_login(self.visitor)
        self.assertContains(
            self.client.get("/account/", {"thread": self.inquiry.pk}),
            "Подготовим два комплекта.",
        )
        self.client.post(f"/inquiries/{self.inquiry.pk}/reply/", {"text": "ещё"})
        self.assertEqual(Message.objects.count(), 2)

    def test_publication_create_edit_and_hide(self):
        self.client.force_login(self.admin)
        data = {
            "action": "publication",
            "title": "Новое объявление",
            "slug": "test-notice",
            "summary": "Описание",
            "body": "Текст новости",
            "category": "news",
            "image": "images/sauna.webp",
            "image_alt": "Сауна",
            "published_at": str(timezone.localdate()),
            "is_published": "on",
        }
        self.assertEqual(self.client.post("/staff/", data).status_code, 302)
        article = Publication.objects.get(slug="test-notice")
        self.assertContains(self.client.get("/news/"), article.title)
        data.pop("is_published")
        self.assertEqual(
            self.client.post(f"/staff/?edit={article.pk}", data).status_code, 302
        )
        self.assertNotContains(self.client.get("/news/"), article.title)

    def test_staff_can_manage_client_but_not_self(self):
        self.client.force_login(self.admin)
        self.client.post(
            "/staff/",
            {"action": "access", "user_id": self.other.pk, "role": "inactive"},
        )
        self.other.refresh_from_db()
        self.assertFalse(self.other.is_active)
        self.client.post(
            "/staff/",
            {"action": "access", "user_id": self.admin.pk, "role": "inactive"},
        )
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
        self.assertTrue(self.admin.is_staff)

    def test_bad_ids_and_empty_reply(self):
        self.client.force_login(self.visitor)
        self.assertEqual(self.client.get("/account/?thread=bad").status_code, 404)
        self.client.post(f"/inquiries/{self.inquiry.pk}/reply/", {"text": "   "})
        self.assertEqual(Message.objects.count(), 0)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/staff/?edit=bad").status_code, 404)
        self.assertEqual(
            self.client.post(
                "/staff/", {"action": "status", "inquiry_id": "bad"}
            ).status_code,
            404,
        )

    def test_404_and_seo_files(self):
        self.assertContains(
            self.client.get("/missing-page/"), "Такой страницы нет", status_code=404
        )
        sitemap = self.client.get("/sitemap.xml")
        self.assertContains(sitemap, "http://127.0.0.1:8000/baths/")
        self.assertNotContains(sitemap, "/staff/")
        self.assertContains(self.client.get("/robots.txt"), "Disallow: /account/")
        self.assertContains(
            self.client.get("/account/"), 'name="robots" content="noindex, nofollow"'
        )

    def test_csrf_and_html_escaping(self):
        secure_client = Client(enforce_csrf_checks=True)
        response = secure_client.post("/contacts/", self.inquiry_data())
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Обновите страницу", status_code=403)
        self.client.force_login(self.visitor)
        self.inquiry.text = '<script>alert("test")</script>'
        self.inquiry.save()
        response = self.client.get("/account/", {"thread": self.inquiry.pk})
        self.assertNotContains(response, self.inquiry.text)
        self.assertContains(response, "&lt;script&gt;")
