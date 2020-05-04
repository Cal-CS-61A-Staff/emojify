import re

from integration import Integration


class ClapIntegration(Integration):
    @property
    def message(self):
        return re.sub(r"^\\clap(.*)$", lambda mat: ":clap: ".join(mat.group(1).strip().split(" ")), self._message)
