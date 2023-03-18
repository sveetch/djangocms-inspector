"""
.. Todo::
    Some options in ``handle()`` are hardcoded and could be command arguments.

"""
import datetime
import json
import time
from pathlib import Path

import requests

from django.core.management import BaseCommand, CommandError
from django.db.models import Count
from django.template import Context
from django.template.loader import get_template

from cms.models.pagemodel import Page
from cms.models.pluginmodel import CMSPlugin


def yes_or_no(value):
    if value is None:
        return "💥"
    return "✅" if value else "❌"


class DummyReponse:
    """
    Fake request response for timeout event
    """
    def __init__(self, status_code):
        self.status_code = status_code


class Command(BaseCommand):
    help = (
        "Inspect DjangoCMS contents to output statistics and summaries about pages and"
        "their plugins. This does not care about tree hierarchy so page summary "
        "and plugins lists will be a flat list, however they are recursively digged."
        "Commonly you will perform the dump first, then reuse the dump to perform ping "
        "and finally render with reused dump again."
        "However you can do all of them in a single execution but this may take a long"
        "time."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--silent",
            action='store_true',
            help=(
                "Don't output results"
            ),
        )

        parser.add_argument(
            "--no-draft",
            action='store_true',
            help=(
                "Ignore draft pages from page summary."
            ),
        )

        parser.add_argument(
            "--slice",
            default=None,
            required=False,
            help=(
                "Page queryset slice given as 'START:END', where START or END can be "
                "empty but not both, also both must be valid integers."
                "Slice is only applied on 'Page summary' queryset."
                "By default there is not slice on page summary, all objects are "
                "fetched. NOTE: This does not work as 'limits', slice behavior is"
                "different (If you start at 5, wanting 10 items then your end should "
                "be 15)."
            ),
        )

        parser.add_argument(
            "--base-url",
            default="http://localhost",
            required=False,
            help=(
                "Base URL (with leading HTTP protocol and without ending slash) used in"
                "URL resolving from objects in results."
            ),
        )

        parser.add_argument(
            "--dump",
            type=Path,
            default=None,
            required=False,
            help=(
                "A filepath destination to write result data to a JSON file."
            )
        )

        parser.add_argument(
            "--reuse",
            type=Path,
            default=None,
            required=False,
            help=(
                "Filepath to an existing dump instead of generating it again. This "
                "will disable the '--dump'. And since it bypasses database operations, "
                "any arguments to change queryset are ignored. You will have the exact"
                "data that you loaded from the reused dump."
            )
        )

        parser.add_argument(
            "--ping",
            type=Path,
            default=None,
            required=False,
            help=(
                "A filepath page for ping status dump. It is used to create a dump for "
                "page ping statuses. If this argument is not given no ping will be "
                "performed."
            )
        )

        parser.add_argument(
            "--render",
            type=Path,
            default=None,
            required=False,
            help=(
                "A filepath destination where to write render HTML summary. If this"
                "argument is not given no render will be performed."
            )
        )

        parser.add_argument(
            "--render-ping",
            type=Path,
            default=None,
            required=False,
            help=(
                "A filepath for a dump to include page ping statuses in rendering. "
                "Without this argument it is assumed there is no ping status to "
                "render."
            )
        )

    def print(self, content=""):
        """
        Print content to stdout if silent mode is disabled.
        """
        if not self.silent:
            self.stdout.write(content)

    def get_pages_stats(self):
        """
        Pages statistics
        """
        self.print("📈 Pages statistics")

        languages_stats = Page.objects.values(
            "languages"
        ).annotate(
            name_count=Count("languages")
        )

        return {
            "total": Page.objects.count(),
            "draft": Page.objects.filter(publisher_is_draft=True).count(),
            "languages": list(languages_stats),
        }

    def get_plugins_stats(self):
        """
        Plugins statistics
        """
        self.print("📈 Plugins statistics")

        plugin_seen = {}

        for plugin in CMSPlugin.objects.all():
            name = plugin.plugin_type

            if name not in plugin_seen:
                plugin_seen[name] = {
                    "total": 0,
                    "as_child": 0,
                    "as_parent": 0,
                }

            plugin_seen[name]["total"] += 1
            if plugin.parent is None:
                plugin_seen[name]["as_parent"] += 1
            else:
                plugin_seen[name]["as_child"] += 1

        return plugin_seen

    def serialize_plugins(self, title, placeholder_ids):
        """
        Get plugin from a Page title object (which the mean for a specific language).
        """
        collected = {}

        plugins = CMSPlugin.get_annotated_list_qs(
            CMSPlugin.objects.filter(placeholder__in=placeholder_ids)
        )
        self.print("                └── Plugins:")

        for plugin in plugins:

            instance, tree_params = plugin
            self.print("                    - ({}) {} : {}".format(
                instance.id,
                instance.plugin_type,
                "At root" if tree_params["level"] == 0 else "Children",
            ))
            collected[instance.id] = {
                "type": instance.plugin_type,
                "level": tree_params["level"],
            }

        return collected

    def serialize_titlemodel(self, page, title):
        """
        Get page title summary data
        """
        url = "/".join([self.base_url, title.language, title.path])
        if not url.endswith("/"):
            url += "/"

        self.print("   └── [{}] {}".format(title.language, title.title))
        self.print("            ├── Published: {}".format(
            yes_or_no(not title.publisher_is_draft)
        ))
        self.print("            └── URL: {}".format(url))

        self.print("                └── Placeholders:")
        placeholders = {
            item.id: item.slot
            for item in page.placeholders.all()
        }
        for pk, name in placeholders.items():
            self.print("                   - ({}) {}".format(pk, name))

        return {
            "language": title.language,
            "title_id": title.id,
            "title": title.title,
            "draft": title.publisher_is_draft,
            "url": url,
            "placeholders": placeholders,
            "plugins": self.serialize_plugins(title, [
                pk
                for pk, name in placeholders.items()
            ]),
        }

    def serialize_pagemodel(self, page):
        """
        Get page summary data
        """
        self.print()
        self.print("{pk}. ({published}) {title}".format(
            pk=str(page.id).zfill(5),
            published=yes_or_no(not page.publisher_is_draft),
            title=page,
        ))

        return {
            "page_id": page.id,
            "main_title": str(page),
            "draft": page.publisher_is_draft,
            "reverse_id": page.reverse_id,
            "soft_root": page.soft_root,
            "application_urls": page.application_urls,
            "application_namespace": page.application_namespace,
            "is_home": page.is_home,
            "creation": page.creation_date.isoformat(timespec="seconds"),
            "changed": page.changed_date.isoformat(timespec="seconds"),
            "login_required": page.login_required,
            "template": page.template,
            "in_navigation": page.in_navigation,
            "language_versions": [
                self.serialize_titlemodel(page, title)
                for title in page.title_set.all()
            ],
        }

    def get_pages_summary(self, ignore_draft=False):
        """
        Create a summary of all pages
        """
        self.print("🗃️ Page summary")

        queryset = Page.objects.all().order_by("id")
        if ignore_draft:
            queryset = queryset.filter(publisher_is_draft=False)

        if self.page_slices:
            queryset = queryset[self.page_slices]

        return [
            self.serialize_pagemodel(item)
            for item in queryset
        ]

    def get_queryset_slice(self, **options):
        """
        Parse and validate given slice pattern.

        Pattern could be:

        * START:END
        * START:
        * :END

        Where START and END are valid integers.

        Everything else would be invalid.
        """
        slices = options.get("slice")

        if not slices:
            return None

        if ":" not in slices:
            raise CommandError("Invalid 'slice' format.")

        slices = slices.split(":")
        starts = int(slices[0]) if slices[0] else None
        ends = int(slices[1]) if slices[1] else None

        return slice(starts, ends)

    def get_reused_dump(self, argname, **options):
        """
        Validate and load a dump from given filepath.

        Arguments:
            argname (string): Argument name.

        Returns:
            object: Object depending from JSON dump structure.
        """
        # Convert argument name to var name
        varname = argname.replace("-", "_")

        if not options[varname]:
            return None

        if not options[varname].exists():
            raise CommandError(
                "Given filepath to argument '--{}' does not exists: {}".format(
                    argname, options[varname]
                )
            )
        elif not options[varname].is_file():
            raise CommandError(
                "Given filepath to argument '--{}' is not a file: {}".format(
                    argname, options[varname]
                )
            )

        return json.loads(options[varname].read_text())

    def inspect(self, **options):
        """
        Proceed to CMS inspection.
        """
        self.print("🚀 Starting inspection")

        return {
            "parameters": {
                "created": datetime.datetime.now().isoformat(timespec="seconds"),
                "base_url": self.base_url,
                "slice": options["slice"],
                "no_draft": options["no_draft"],
            },
            "statistics": {
                "plugins": self.get_plugins_stats(),
                "pages": self.get_pages_stats(),
            },
            "objects": {
                "pages": self.get_pages_summary(ignore_draft=options["no_draft"]),
            },
        }

    def ping(self, destination, page_payload):
        """
        Ping every published page versions to get their response status.
        """
        if not destination:
            return None

        self.print("🚀 Starting to ping versions for {} pages".format(
            len(page_payload["objects"]["pages"])
        ))
        destination = destination.resolve()

        parent_dirs = destination.parent
        if not parent_dirs.exists():
            parent_dirs.mkdir(parents=True, exist_ok=True)

        # Compute total of page titles to perform
        published_title_total = 0
        for page in page_payload["objects"]["pages"]:
            for title in page["language_versions"]:
                if not title["draft"]:
                    published_title_total += 1

        self.print("  - Total of titles {}".format(
            published_title_total
        ))
        if self.ping_batch:
            self.print("  - By batch of {}".format(self.ping_batch))
            self.print("  - For a total of approximatively {} batches".format(
                round(published_title_total / self.ping_batch)
            ))
            self.print("  - Each batch paused on {}s".format(self.ping_pause))
        self.print()

        # Walk on every pages
        payload = {}
        batch_slot = 0
        done_titles = 0
        for page_index, page in enumerate(page_payload["objects"]["pages"], start=1):
            self.print("{i}. #{pk} ({published}) {title}".format(
                i=page_index,
                pk=str(page["page_id"]).zfill(5),
                published=yes_or_no(not page["draft"]),
                title=page["main_title"],
            ))

            # Walk on every page titles
            for title in page["language_versions"]:
                if not title["draft"]:
                    batch_slot += 1
                    done_titles += 1
                    self.print("   └── [{}] {}".format(
                        title["language"], title["title"]
                    ))

                    self.print("            ├── Published: {}".format(
                        yes_or_no(not title["draft"])
                    ))
                    self.print("            └── URL: {}".format(title["url"]))

                    # Perform ping request
                    try:
                        r = requests.get(
                            title["url"],
                            headers=self.request_headers,
                            timeout=self.request_timeout
                        )
                    except requests.exceptions.ReadTimeout:
                        r = DummyReponse(status_code=408)

                    self.print("            └── Status: {sign} {label}".format(
                        sign="💚" if r.status_code == requests.codes.ok else "🚩",
                        label=r.status_code,
                    ))
                    payload[title["title_id"]] = {
                        "status_code": r.status_code,
                        "is_ok": r.status_code == requests.codes.ok,
                    }

                    # Pause the batch ping if necessary
                    if (
                        self.ping_batch and
                        self.ping_pause and
                        done_titles >= self.ping_batch and
                        batch_slot < published_title_total
                    ):
                        msg = "💬 Ping batch pausing for {}s"
                        self.print(msg.format(self.ping_pause))
                        time.sleep(self.ping_pause)
                        done_titles = 0

        self.print("📝 Writing ping dump to: {}".format(destination))
        destination.write_text(
            json.dumps(payload, indent=4)
        )

        return destination

    def render(self, destination, page_payload, ping_payload=None):
        """
        Render generated summaries to HTML.
        """
        destination = destination.resolve()

        parent_dirs = destination.parent
        if not parent_dirs.exists():
            parent_dirs.mkdir(parents=True, exist_ok=True)

        self.print("📝 Rendering report to: {}".format(destination))

        t = get_template("djangocms_inspector/plugins_report.html").template

        destination.write_text(
            t.render(Context({
                "summaries": page_payload,
                "pings": ping_payload,
            }))
        )

        return destination

    def handle(self, *args, **options):
        self.silent = options["silent"]
        self.base_url = options["base_url"]
        self.request_timeout = 10
        self.request_headers = {"user-agent": "djangocms-inspector"}
        self.ping_batch = 10
        self.ping_pause = 2

        self.page_slices = self.get_queryset_slice(**options)
        self.reused_pages_dump = self.get_reused_dump("reuse", **options)
        self.reused_pings_dump = self.get_reused_dump("render-ping", **options)

        # Either get page payload from reused dump or proceed to payload generation
        page_payload = self.reused_pages_dump or self.inspect(**options)

        # Either get pings payload from reused dump or proceed to payload generation
        ping_payload = (
            self.reused_pings_dump or self.ping(options["ping"], page_payload)
        )

        # Proceed to dump only if not in reuse mode
        if not self.reused_pages_dump and options["dump"]:
            self.print("📝 Writing dump to: {}".format(options["dump"]))
            options["dump"].write_text(
                json.dumps(page_payload, indent=4)
            )

        if options["render"]:
            self.render(options["render"], page_payload, ping_payload)
