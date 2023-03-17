.. _intro_install:

=======
Install
=======

Install package in your environment : ::

    pip install djangocms-inspector

For development usage see :ref:`install_development`.

Configuration
*************

Add it to your installed Django apps in settings : ::

    INSTALLED_APPS = (
        ...
        "djangocms_inspector",
    )

Then load default application settings in your settings file: ::

    from djangocms_inspector.settings import *

Then mount applications URLs: ::

    urlpatterns = [
        ...
        path("", include("djangocms_inspector.urls")),
    ]

And finally apply database migrations.

Settings
********

.. automodule:: djangocms_inspector.settings
   :members:
