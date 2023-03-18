import datetime

from django.template import Library

register = Library()


@register.filter(name="split", is_safe=False)
def split_string(value, arg=None):
    """
    A simple string splitter

    So you can do that : ::
        {{ "foo,bar,plop"|split:"," }}

    Or that : ::

        {% if "foo" in "foo,bar,plop"|split:"," %}...{% endif %}

    """
    return value.split(arg)


@register.filter
def iso_to_datetime(value):
    """
    Parse a datetime string in ISO format into a datetime object.

    ISO format expected should be like: ::

        2022-05-09T11:40:28+00:00

    """
    return datetime.datetime.fromisoformat(value)


@register.filter
def distinct_plugins(plugins):
    """
    Return a list of distinct plugin names from given title plugin dict.
    """
    plugins = [v["type"] for k, v in plugins.items()]
    return sorted(list(set(plugins)))


@register.simple_tag(takes_context=True)
def get_pages_languages(context):
    """
    Return a list of distinct used languages with their total pages.
    """
    languages = {}
    for item in context["summaries"]["statistics"]["pages"]["languages"]:
        for lang in item["languages"].split(","):
            if lang not in languages:
                languages[lang] = item["name_count"]
            else:
                languages[lang] += item["name_count"]

    # Title id is stored as a string in ping registry
    return languages


@register.simple_tag(takes_context=True)
def get_title_ping(context, item_name):
    """
    Get an item from ping registry.
    """
    if not context.get("pings"):
        return None

    # Title id is stored as a string in ping registry
    return


@register.simple_tag(takes_context=True)
def get_title_httpstatus(context, title_id):
    """
    Return the HTTP status for given title ID.
    """
    if not context.get("pings") or not title_id:
        return None

    # Title id is stored as a string in ping registry
    ping = context["pings"].get(str(title_id))

    if not ping:
        return None

    return ping


@register.simple_tag(takes_context=True)
def get_page_httpstatus(context, page_titles):
    """
    Return the major HTTP status for given page titles.

    Major status means:

    * If there is only success status, it will be 'success';
    * If there is only error status, it will be 'error';
    * If there is both error or success, it will be 'both';
    * If there is not ping or titles, it will be 'none';
    """
    if not context.get("pings") or not page_titles:
        return "none"

    ids = [item["title_id"] for item in page_titles]

    # Title id is stored as a string in ping registry
    pings = [
        context["pings"].get(str(i))["is_ok"]
        for i in ids
        if context["pings"].get(str(i))
    ]

    if len(pings) == 0:
        code = "none"
    elif True in pings and False in pings:
        code = "both"
    elif all(pings):
        code = "success"
    else:
        code = "error"

    return code
