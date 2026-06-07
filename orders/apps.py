from django.apps import AppConfig


class OrdersConfig(AppConfig):
    name = 'orders'

    def ready(self):
        # এই লাইনটি যুক্ত করার মাধ্যমে জ্যাঙ্গো আপনার সিগন্যালটিকে অ্যাক্টিভেট করে নেবে
        import orders.signals
