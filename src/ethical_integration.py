from integration import Integration


class Ethicalntegration(Integration):
    @property
    def message(self):
        return self._message.replace("88 &gt", "88 &lt").replace("61a &lt", "61a &gt").replace("61A &lt", "61A &gt")
