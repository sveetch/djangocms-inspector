from cms.api import add_plugin, create_page


class PageCreator:
    """
    Helper to create and fill CMS page with plugins.
    """
    def __init__(self, default_placeholder, default_language, default_template,
                 page=None):
        self.default_placeholder = default_placeholder
        self.default_language = default_language
        self.default_template = default_template
        self.page = page

    def get_placeholder(self, page, slot_name):
        return page.placeholders.get(slot=slot_name)

    def create(self, title, template=None, language=None, **kwargs):
        """
        Create a new page

        Reference: https://docs.django-cms.org/en/latest/reference/api_references.html#cms.api.create_page
        """
        self.page = create_page(
            title,
            template or self.default_template,
            language or self.default_language,
            **kwargs
        )

        return self.page

    def add_title(self, page, title, language, **kwargs):
        """
        Add a title to a page (commonly to add a new language)

        Reference: https://docs.django-cms.org/en/latest/reference/api_references.html#cms.api.create_title
        """
        return create_title(
            language,
            title,
            page,
            **kwargs
        )

    def add_plugin(self, plugin, page=None, placeholder=None, language=None, parent=None, **kwargs):
        """
        Create a new plugin into a page placeholder

        Reference: https://docs.django-cms.org/en/latest/reference/api_references.html#cms.api.add_plugin
        """
        page = page or self.page

        assert page is not None

        if not parent:
            placeholder = self.get_placeholder(
                page,
                placeholder or self.default_placeholder
            )
        else:
            placeholder = placeholder or parent.placeholder

        created = add_plugin(
            placeholder,
            plugin,
            language or self.default_language,
            target=parent,
            **kwargs,
        )

        return created

    def publish(self, language=None):
        language = language or self.default_language

        assert self.page is not None

        self.page.publish(language)
