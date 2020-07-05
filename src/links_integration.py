import itertools
import re
from collections import namedtuple

from integration import Integration
from utils import OrderedSet

LinkLink = namedtuple("LinkLink", ["path"])

VALID_PATH = r"[0-9A-Za-z\-]"
PATH_REGEX = r"(?P<path>{}+)".format(VALID_PATH)

REGEX_TEMPLATE = r"<(https?://)?links\.cs61a\.org/{}/?(\|[^\s|]+)?>"
SHORT_REGEX_TEMPLATE = r"links/{}/?"

class LinkLinkIntegration(Integration):
    def _process(self):
        self._linklinks = OrderedSet()
        for match in itertools.chain(
            re.finditer(REGEX_TEMPLATE.format(PATH_REGEX), self._message),
            re.finditer(SHORT_REGEX_TEMPLATE.format(PATH_REGEX), self._message),
        ):
            self._linklinks.add(LinkLink(match.group("path")))

    @property
    def message(self):
        out = self._message
        for link in self._linklinks:
            out = re.sub(
                REGEX_TEMPLATE.format(link.path),
                "links/{}".format(link.path),
                out,
            )
            out = re.sub(
                SHORT_REGEX_TEMPLATE.format(link.path),
                r"<https://links.cs61a.org/{}|links/{}>".format(link.path, link.path),
                out,
            )
        return out
