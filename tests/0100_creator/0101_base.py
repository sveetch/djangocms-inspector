from django.conf import settings
from django.test import modify_settings

from cms.api import add_plugin, create_page
from djangocms_text_ckeditor.cms_plugins import TextPlugin

from tests.utils import FixturesTestCaseMixin
from djangocms_inspector.utils.tests import decode_response_or_string, html_pyquery
from djangocms_inspector.utils.cms_tests import CMSPluginTestCase
from djangocms_inspector.creator import PageCreator


def test_foo(db):
    """
    TODO
    """
    # Create page and return its main content placeholder
    page = create_page(
        "Homepage",
        "pages/test.html",
        settings.LANGUAGE_CODE,
    )
